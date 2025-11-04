"""
BacktestAgent - 回测专用Agent
继承BaseAgent，使用本地历史数据进行回测，替代实时MCP服务调用
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import parent class
from .base_agent import BaseAgent

# Import tools
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from tools.general_tools import extract_conversation, extract_tool_messages, get_config_value, write_config_value
from tools.price_tools import add_no_trade_record
from prompts.agent_prompt import get_agent_system_prompt, STOP_SIGNAL


class BacktestAgent(BaseAgent):
    """
    回测专用Agent类
    
    主要特点：
    1. 使用本地历史数据，无需实时API调用
    2. 严格防止时间旅行（未来数据泄露）
    3. 模拟交易成本（滑点、佣金、印花税）
    4. 支持与BacktestEngine集成
    """
    
    def __init__(
        self,
        signature: str,
        basemodel: str,
        historical_data: Dict[str, Dict[str, Dict]],
        consensus_data: Optional[Dict[str, Dict]] = None,
        stock_symbols: Optional[List[str]] = None,
        log_path: Optional[str] = None,
        max_steps: int = 10,
        max_retries: int = 3,
        base_delay: float = 0.5,
        openai_base_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        initial_cash: float = 100000.0,
        init_date: str = "2024-01-01"
    ):
        """
        初始化回测Agent
        
        Args:
            signature: Agent签名/名称
            basemodel: 基础模型名
            historical_data: 历史行情数据 {symbol: {date: price_data}}
            consensus_data: 共识数据 {date: {symbol: consensus_info}}
            stock_symbols: 股票代码列表
            log_path: 日志路径
            max_steps: 最大推理步数
            max_retries: 最大重试次数
            base_delay: 重试延迟
            openai_base_url: OpenAI API base URL
            openai_api_key: OpenAI API key
            initial_cash: 初始资金
            init_date: 初始化日期
        """
        # 调用父类初始化
        super().__init__(
            signature=signature,
            basemodel=basemodel,
            stock_symbols=stock_symbols,
            mcp_config=None,  # 回测模式不使用MCP
            log_path=log_path,
            max_steps=max_steps,
            max_retries=max_retries,
            base_delay=base_delay,
            openai_base_url=openai_base_url,
            openai_api_key=openai_api_key,
            initial_cash=initial_cash,
            init_date=init_date
        )
        
        # 回测专用数据
        self.historical_data = historical_data
        self.consensus_data = consensus_data or {}
        self.current_backtest_date = None
        
        # 本地工具模拟（替代MCP服务）
        self.local_tools = self._create_local_tools()
    
    async def initialize(self) -> None:
        """初始化回测Agent（简化版，无需MCP）"""
        print(f"🚀 初始化回测Agent: {self.signature}")
        
        # 验证OpenAI配置
        if not self.openai_api_key:
            raise ValueError("❌ 未设置OpenAI API key")
        
        try:
            from langchain_openai import ChatOpenAI
            
            # 创建AI模型
            self.model = ChatOpenAI(
                model=self.basemodel,
                base_url=self.openai_base_url,
                api_key=self.openai_api_key,
                max_retries=3,
                timeout=30
            )
            print(f"✅ AI模型初始化成功: {self.basemodel}")
        except Exception as e:
            raise RuntimeError(f"❌ AI模型初始化失败: {e}")
        
        # 注意：由于回测使用本地数据，不需要创建MCP客户端
        # Agent将在run_trading_session中创建
        
        print(f"✅ 回测Agent {self.signature} 初始化完成")
    
    def _create_local_tools(self) -> List[Any]:
        """创建本地工具（模拟MCP工具）"""
        from langchain.tools import Tool
        
        tools = []
        
        # 1. get_price 工具
        def get_price_wrapper(input_str: str) -> str:
            """获取股票价格数据"""
            try:
                import json
                # 解析输入参数
                params = json.loads(input_str) if isinstance(input_str, str) else input_str
                symbol = params.get('symbol')
                date = params.get('date', self.current_backtest_date)
                
                price_data = self.get_price_local(symbol, date)
                if price_data:
                    return json.dumps(price_data, ensure_ascii=False)
                else:
                    return json.dumps({"error": "无法获取价格数据"})
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        tools.append(Tool(
            name="get_price",
            func=get_price_wrapper,
            description="获取股票价格数据。输入: {\"symbol\": \"股票代码\", \"date\": \"日期\"}"
        ))
        
        # 2. get_consensus 工具
        def get_consensus_wrapper(input_str: str) -> str:
            """获取共识数据"""
            try:
                import json
                params = json.loads(input_str) if isinstance(input_str, str) else input_str
                symbol = params.get('symbol')
                date = params.get('date', self.current_backtest_date)
                
                consensus_data = self.get_consensus_local(symbol, date)
                if consensus_data:
                    return json.dumps(consensus_data, ensure_ascii=False)
                else:
                    return json.dumps({"info": "暂无共识数据"})
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        tools.append(Tool(
            name="get_consensus",
            func=get_consensus_wrapper,
            description="获取股票共识数据。输入: {\"symbol\": \"股票代码\", \"date\": \"日期\"}"
        ))
        
        # 3. trade 工具 (回测版本)
        def trade_wrapper(input_str: str) -> str:
            """执行交易操作"""
            try:
                import json
                params = json.loads(input_str) if isinstance(input_str, str) else input_str
                
                # 提取交易参数
                symbol = params.get('symbol')
                action = params.get('action')  # 'buy' or 'sell'
                quantity = params.get('quantity', 100)
                price = params.get('price')
                
                # 这里只是记录交易意图，实际执行由BacktestEngine处理
                trade_record = {
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "price": price,
                    "date": self.current_backtest_date,
                    "status": "pending"
                }
                
                return json.dumps({
                    "success": True,
                    "message": f"{action} {quantity}股 {symbol} @ {price}",
                    "trade": trade_record
                }, ensure_ascii=False)
                
            except Exception as e:
                return json.dumps({"error": str(e)}, ensure_ascii=False)
        
        tools.append(Tool(
            name="trade",
            func=trade_wrapper,
            description="执行交易。输入: {\"symbol\": \"股票代码\", \"action\": \"buy/sell\", \"quantity\": 数量, \"price\": 价格}"
        ))
        
        # 4. search 工具 (模拟版本)
        def search_wrapper(input_str: str) -> str:
            """搜索相关信息"""
            try:
                import json
                params = json.loads(input_str) if isinstance(input_str, str) else input_str
                query = params.get('query', '')
                
                # 回测环境下返回模拟结果
                return json.dumps({
                    "results": [],
                    "message": f"回测模式下搜索功能不可用: {query}"
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": str(e)}, ensure_ascii=False)
        
        tools.append(Tool(
            name="search",
            func=search_wrapper,
            description="搜索相关信息。输入: {\"query\": \"搜索关键词\"}"
        ))
        
        return tools
    
    def get_price_local(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """本地获取价格数据（替代MCP get_price）
        
        Args:
            symbol: 股票代码
            date: 日期
            
        Returns:
            价格数据或None
        """
        # 时间旅行检查
        if date > self.current_backtest_date:
            print(f"⚠️ 时间旅行警告：请求{date}的数据，但当前回测日期为{self.current_backtest_date}")
            return None
        
        if symbol not in self.historical_data:
            return None
        
        if date not in self.historical_data[symbol]:
            return None
        
        return self.historical_data[symbol][date]
    
    def get_consensus_local(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """本地获取共识数据
        
        Args:
            symbol: 股票代码
            date: 日期
            
        Returns:
            共识数据或None
        """
        # 时间旅行检查
        if date > self.current_backtest_date:
            return None
        
        if date not in self.consensus_data:
            return None
        
        if symbol not in self.consensus_data[date]:
            return None
        
        return self.consensus_data[date][symbol]
    
    async def run_trading_session(self, today_date: str) -> Dict[str, Any]:
        """
        运行单日回测交易（重写父类方法）
        
        Args:
            today_date: 回测日期
            
        Returns:
            交易决策信息
        """
        print(f"📈 开始回测交易: {today_date}")
        
        # 更新当前回测日期（用于时间旅行检查）
        self.current_backtest_date = today_date
        
        # 设置日志
        log_file = self._setup_logging(today_date)
        write_config_value("LOG_FILE", log_file)
        
        # 创建agent（使用本地工具）
        from langchain.agents import create_agent
        
        self.agent = create_agent(
            self.model,
            tools=self.local_tools,  # 使用本地工具而非MCP工具
            system_prompt=get_agent_system_prompt(today_date, self.signature),
        )
        
        # 构建市场信息上下文
        market_context = self._build_market_context(today_date)
        
        # 初始用户查询
        user_query = [{"role": "user", "content": f"请分析并更新今日（{today_date}）持仓。\n\n{market_context}"}]
        message = user_query.copy()
        
        # 记录初始消息
        self._log_message(log_file, user_query)
        
        # 交易决策（简化版，直接返回分析结果）
        trading_decision = {
            "date": today_date,
            "actions": [],
            "reasoning": ""
        }
        
        # 交易循环
        current_step = 0
        while current_step < self.max_steps:
            current_step += 1
            print(f"🔄 步骤 {current_step}/{self.max_steps}")
            
            try:
                # 调用agent
                response = await self._ainvoke_with_retry(message)
                
                # 提取agent响应
                agent_response = extract_conversation(response, "final")
                
                # 检查停止信号
                if STOP_SIGNAL in agent_response:
                    print("✅ 收到停止信号，交易决策完成")
                    trading_decision["reasoning"] = agent_response
                    self._log_message(log_file, [{"role": "assistant", "content": agent_response}])
                    break
                
                # 提取工具消息
                tool_msgs = extract_tool_messages(response)
                tool_response = '\n'.join([msg.content for msg in tool_msgs])
                
                # 准备新消息
                new_messages = [
                    {"role": "assistant", "content": agent_response},
                    {"role": "user", "content": f'工具返回结果: {tool_response}'}
                ]
                
                # 添加新消息
                message.extend(new_messages)
                
                # 记录消息
                self._log_message(log_file, new_messages[0])
                self._log_message(log_file, new_messages[1])
                
            except Exception as e:
                print(f"❌ 回测交易决策错误: {str(e)}")
                trading_decision["error"] = str(e)
                break
        
        return trading_decision
    
    def _build_market_context(self, date: str) -> str:
        """构建市场上下文信息
        
        Args:
            date: 日期
            
        Returns:
            市场上下文文本
        """
        context_parts = []
        
        # 1. 可交易股票列表（有数据的股票）
        available_stocks = []
        for symbol in self.stock_symbols:
            if symbol in self.historical_data and date in self.historical_data[symbol]:
                available_stocks.append(symbol)
        
        context_parts.append(f"今日可交易股票（共{len(available_stocks)}只）：{', '.join(available_stocks[:20])}")
        if len(available_stocks) > 20:
            context_parts.append(f"...（还有{len(available_stocks) - 20}只）")
        
        # 2. 共识数据概览
        if date in self.consensus_data:
            high_consensus_stocks = []
            for symbol, cons_data in self.consensus_data[date].items():
                score = cons_data.get('consensus_score', {}).get('total', 0)
                if score >= 70:
                    high_consensus_stocks.append(f"{symbol}({score}分)")
            
            if high_consensus_stocks:
                context_parts.append(f"\n高共识股票（≥70分）：{', '.join(high_consensus_stocks[:10])}")
        
        # 3. 交易规则提醒
        context_parts.append("\n【A股交易规则】")
        context_parts.append("- T+1制度：今日买入的股票明日才能卖出")
        context_parts.append("- 涨跌停限制：主板±10%，科创板/创业板±20%")
        context_parts.append("- 最小交易单位：100股（1手）")
        
        return '\n'.join(context_parts)
    
    async def run_backtest_date_range(self, start_date: str, end_date: str,
                                     callback=None) -> List[Dict[str, Any]]:
        """
        运行日期范围内的回测
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            callback: 回调函数，用于与BacktestEngine交互
            
        Returns:
            所有交易日的决策列表
        """
        print(f"📅 运行回测: {start_date} 至 {end_date}")
        
        # 获取交易日期列表
        trading_dates = self._get_trading_dates_in_range(start_date, end_date)
        
        if not trading_dates:
            print("ℹ️ 无交易日需要处理")
            return []
        
        print(f"📊 需要处理的交易日: {len(trading_dates)}天")
        
        all_decisions = []
        
        # 处理每个交易日
        for date in trading_dates:
            print(f"\n{'='*60}")
            print(f"🔄 回测日期: {date}")
            
            # 设置配置
            write_config_value("TODAY_DATE", date)
            write_config_value("SIGNATURE", self.signature)
            
            try:
                # 运行交易决策
                decision = await self.run_trading_session(date)
                all_decisions.append(decision)
                
                # 如果有回调函数（与BacktestEngine交互），调用它
                if callback:
                    callback_result = callback(date, decision)
                    print(f"回调返回: {callback_result}")
                
            except Exception as e:
                print(f"❌ 回测日期 {date} 发生错误: {e}")
                all_decisions.append({
                    "date": date,
                    "error": str(e)
                })
        
        print(f"\n✅ 回测完成，共处理 {len(all_decisions)} 个交易日")
        return all_decisions
    
    def _get_trading_dates_in_range(self, start_date: str, end_date: str) -> List[str]:
        """获取日期范围内的所有交易日
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            交易日期列表
        """
        # 从历史数据中提取所有日期
        all_dates = set()
        for symbol_data in self.historical_data.values():
            all_dates.update(symbol_data.keys())
        
        # 筛选日期范围
        trading_dates = sorted([
            d for d in all_dates 
            if start_date <= d <= end_date
        ])
        
        return trading_dates
    
    def get_backtest_summary(self) -> Dict[str, Any]:
        """获取回测总结"""
        return {
            "signature": self.signature,
            "stocks_count": len(self.historical_data),
            "dates_count": len(set(
                date for symbol_data in self.historical_data.values()
                for date in symbol_data.keys()
            )),
            "initial_cash": self.initial_cash,
            "position_file": self.position_file
        }
    
    def __str__(self) -> str:
        return f"BacktestAgent(signature='{self.signature}', stocks={len(self.historical_data)}, backtest_mode=True)"
    
    def __repr__(self) -> str:
        return self.__str__()
