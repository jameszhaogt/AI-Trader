"""
回测专用Agent

继承自BaseAgent,专门用于历史数据回测场景。
与实盘Agent的主要区别:
1. 数据来源:从本地JSONL文件读取,不调用实时API
2. 时间控制:严格的时间旅行检测,禁止访问未来数据
3. 交易校验:完整的A股交易规则合规检查
4. 性能优化:批量加载数据,减少IO开销

作者: AI-Trader Team
日期: 2024
"""

import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# TODO: 导入BaseAgent(需要根据实际项目结构调整)
# from agent.base_agent import BaseAgent


class BacktestAgent:
    """回测专用Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化回测Agent
        
        Args:
            config: 配置字典,包含:
                - data_dir: 数据目录
                - market: 市场类型 "ASTOCK"
                - start_date: 回测开始日期
                - end_date: 回测结束日期
                - initial_capital: 初始资金
                - enable_time_travel_check: 是否启用时间旅行检测
                - enable_compliance_check: 是否启用合规检查
        """
        self.config = config
        self.data_dir = config.get("data_dir", "./data")
        self.market = config.get("market", "ASTOCK")
        self.start_date = config["start_date"]
        self.end_date = config["end_date"]
        
        # 时间旅行检测
        self.enable_time_travel_check = config.get("enable_time_travel_check", True)
        self.current_date: Optional[datetime] = None
        
        # 合规检查
        self.enable_compliance_check = config.get("enable_compliance_check", True)
        
        # 数据缓存
        self.price_cache: Dict[str, Dict[str, Dict]] = {}  # {symbol: {date: data}}
        self.consensus_cache: Dict[str, Dict[str, Dict]] = {}
        self.stock_list_cache: Dict[str, Dict] = {}  # {symbol: info}
        
        # 交易历史(用于T+1校验)
        self.trade_history: Dict[str, List[Dict]] = {}  # {date: [trades]}
        
        logging.info(f"回测Agent初始化:市场={self.market}, 期间={self.start_date}~{self.end_date}")
    
    def load_stock_list(self, stock_pool: str = "HS300") -> Dict[str, Dict]:
        """
        加载股票列表
        
        Args:
            stock_pool: 股票池名称,如"HS300", "KC50", "CUSTOM"
            
        Returns:
            dict: {symbol: {"name": str, "is_st": bool, "industry": str, ...}}
        """
        if stock_pool == "CUSTOM":
            # 从配置读取自定义股票列表
            symbols = self.config.get("data", {}).get("custom_stocks", [])
            filepath = os.path.join(self.data_dir, "astock_list_custom.json")
        else:
            filepath = os.path.join(self.data_dir, f"astock_list_{stock_pool.lower()}.json")
        
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.stock_list_cache = {item["symbol"]: item for item in data}
                logging.info(f"股票列表加载成功:{len(self.stock_list_cache)}只股票")
        else:
            logging.warning(f"股票列表文件不存在:{filepath}")
            self.stock_list_cache = {}
        
        return self.stock_list_cache
    
    def load_price_data(self, symbols: List[str]):
        """
        批量加载行情数据到内存
        
        Args:
            symbols: 股票代码列表
        """
        logging.info(f"开始加载{len(symbols)}只股票的行情数据...")
        
        for symbol in symbols:
            filepath = os.path.join(self.data_dir, f"merged_data_{symbol}.jsonl")
            
            if not os.path.exists(filepath):
                logging.warning(f"行情数据文件不存在:{filepath}")
                continue
            
            self.price_cache[symbol] = {}
            
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            date_str = record["date"]
                            self.price_cache[symbol][date_str] = record
                        except json.JSONDecodeError as e:
                            logging.warning(f"解析行情数据失败:{e}, line={line[:100]}")
        
        total_records = sum(len(v) for v in self.price_cache.values())
        logging.info(f"行情数据加载完成:共{total_records}条记录")
    
    def load_consensus_data(self, symbols: List[str]):
        """
        批量加载共识数据到内存
        
        Args:
            symbols: 股票代码列表
        """
        logging.info(f"开始加载{len(symbols)}只股票的共识数据...")
        
        for symbol in symbols:
            filepath = os.path.join(self.data_dir, f"consensus_data_{symbol}.jsonl")
            
            if not os.path.exists(filepath):
                logging.debug(f"共识数据文件不存在(可选):{filepath}")
                continue
            
            self.consensus_cache[symbol] = {}
            
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            date_str = record["date"]
                            self.consensus_cache[symbol][date_str] = record
                        except json.JSONDecodeError as e:
                            logging.warning(f"解析共识数据失败:{e}")
        
        total_records = sum(len(v) for v in self.consensus_cache.values())
        logging.info(f"共识数据加载完成:共{total_records}条记录")
    
    def get_price(self, symbol: str, date: str, field: str = "close") -> Optional[float]:
        """
        获取价格数据(带时间旅行检测)
        
        Args:
            symbol: 股票代码
            date: 日期 "YYYY-MM-DD"
            field: 字段名,如"close", "open", "high", "low", "volume"
            
        Returns:
            float: 价格值,不存在时返回None
            
        Raises:
            TimeViolationError: 访问未来数据时抛出
        """
        # 时间旅行检测
        if self.enable_time_travel_check and self.current_date:
            query_date = datetime.strptime(date, "%Y-%m-%d")
            if query_date > self.current_date:
                from tools.backtest_engine import TimeViolationError
                raise TimeViolationError(
                    f"禁止访问未来价格数据:当前={self.current_date.strftime('%Y-%m-%d')}, "
                    f"查询={date}, symbol={symbol}, field={field}"
                )
        
        # 从缓存读取
        if symbol not in self.price_cache:
            return None
        
        if date not in self.price_cache[symbol]:
            return None
        
        return self.price_cache[symbol][date].get(field)
    
    def get_consensus(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """
        获取共识数据(带时间旅行检测)
        
        Args:
            symbol: 股票代码
            date: 日期 "YYYY-MM-DD"
            
        Returns:
            dict: 共识数据,不存在时返回None
            
        Raises:
            TimeViolationError: 访问未来数据时抛出
        """
        # 时间旅行检测
        if self.enable_time_travel_check and self.current_date:
            query_date = datetime.strptime(date, "%Y-%m-%d")
            if query_date > self.current_date:
                from tools.backtest_engine import TimeViolationError
                raise TimeViolationError(
                    f"禁止访问未来共识数据:当前={self.current_date.strftime('%Y-%m-%d')}, "
                    f"查询={date}, symbol={symbol}"
                )
        
        # 从缓存读取
        if symbol not in self.consensus_cache:
            return None
        
        return self.consensus_cache[symbol].get(date)
    
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 股票信息,包含name, is_st, industry等字段
        """
        return self.stock_list_cache.get(symbol)
    
    def validate_trade(self, symbol: str, action: str, quantity: int, 
                      price: float, date: str) -> tuple[bool, str]:
        """
        校验交易合规性(A股规则)
        
        Args:
            symbol: 股票代码
            action: "buy" 或 "sell"
            quantity: 数量
            price: 价格
            date: 日期
            
        Returns:
            tuple: (是否合规, 错误信息)
        """
        if not self.enable_compliance_check:
            return True, ""
        
        # TODO: 调用agent_tools/tool_trade_astock.py的校验函数
        # from agent_tools.tool_trade_astock import AStockTradeValidator
        
        # 示例实现
        # 1. 最小交易单位
        if quantity % 100 != 0:
            return False, f"交易数量必须是100股整数倍:当前{quantity}股"
        
        # 2. 停牌检查
        price_data = self.price_cache.get(symbol, {}).get(date, {})
        if price_data.get("status") == "suspended":
            return False, f"禁止交易停牌股票:{symbol}在{date}停牌"
        
        # 3. T+1检查
        if action == "sell":
            yesterday = (datetime.strptime(date, "%Y-%m-%d") - 
                        __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
            if yesterday in self.trade_history:
                for trade in self.trade_history[yesterday]:
                    if trade["symbol"] == symbol and trade["action"] == "buy":
                        return False, f"违反T+1规则:{symbol}于{yesterday}买入,{date}不能卖出"
        
        # 4. 涨跌停检查
        if price_data:
            prev_close = price_data.get("prev_close")
            current_price = price_data.get("close")
            
            if prev_close and current_price:
                stock_info = self.get_stock_info(symbol)
                is_st = stock_info.get("is_st", False) if stock_info else False
                
                # 计算涨跌停价
                if symbol.startswith("688") or symbol.startswith("300"):
                    limit_ratio = 1.20
                elif is_st:
                    limit_ratio = 1.05
                else:
                    limit_ratio = 1.10
                
                limit_up = round(prev_close * limit_ratio, 2)
                limit_down = round(prev_close * (2 - limit_ratio), 2)
                
                if action == "buy" and abs(current_price - limit_up) < 0.01:
                    return False, f"禁止涨停价买入:{symbol}当前价{current_price}已涨停"
                
                if action == "sell" and abs(current_price - limit_down) < 0.01:
                    return False, f"禁止跌停价卖出:{symbol}当前价{current_price}已跌停"
        
        return True, ""
    
    def record_trade(self, symbol: str, action: str, quantity: int, 
                    price: float, date: str):
        """
        记录交易历史
        
        Args:
            symbol: 股票代码
            action: 交易动作
            quantity: 数量
            price: 价格
            date: 日期
        """
        if date not in self.trade_history:
            self.trade_history[date] = []
        
        self.trade_history[date].append({
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price
        })
    
    def run_strategy(self, strategy_func):
        """
        执行回测策略
        
        Args:
            strategy_func: 策略函数,签名为 func(agent, date) -> List[dict]
                          返回交易信号列表
        """
        from datetime import timedelta
        
        current = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        
        logging.info("开始执行策略回测...")
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            self.current_date = current
            
            # 调用策略函数
            try:
                signals = strategy_func(self, date_str)
                
                # 处理交易信号
                for signal in signals:
                    is_valid, error = self.validate_trade(
                        signal["symbol"],
                        signal["action"],
                        signal["quantity"],
                        signal["price"],
                        date_str
                    )
                    
                    if is_valid:
                        self.record_trade(
                            signal["symbol"],
                            signal["action"],
                            signal["quantity"],
                            signal["price"],
                            date_str
                        )
                        logging.info(f"交易信号:{date_str} {signal}")
                    else:
                        logging.warning(f"交易被拒绝:{error}")
            
            except Exception as e:
                logging.error(f"策略执行出错:{e}", exc_info=True)
            
            current += timedelta(days=1)
        
        logging.info("策略回测完成")
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """
        获取交易汇总
        
        Returns:
            dict: 交易统计信息
        """
        total_trades = sum(len(trades) for trades in self.trade_history.values())
        buy_trades = sum(1 for trades in self.trade_history.values() 
                        for t in trades if t["action"] == "buy")
        sell_trades = total_trades - buy_trades
        
        return {
            "total_trades": total_trades,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "trading_days": len(self.trade_history)
        }


# 示例用法
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 配置
    config = {
        "data_dir": "./data",
        "market": "ASTOCK",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 1000000,
        "enable_time_travel_check": True,
        "enable_compliance_check": True
    }
    
    # 创建Agent
    agent = BacktestAgent(config)
    
    # 加载数据
    # agent.load_stock_list("HS300")
    # symbols = list(agent.stock_list_cache.keys())[:10]
    # agent.load_price_data(symbols)
    # agent.load_consensus_data(symbols)
    
    # 定义策略
    def simple_strategy(agent, date):
        """示例策略"""
        return []
    
    # 运行回测
    # agent.run_strategy(simple_strategy)
    
    # 输出汇总
    # summary = agent.get_trade_summary()
    # print(json.dumps(summary, indent=2))
    
    print("回测Agent框架已就绪")
