"""
A股回测引擎
支持历史数据回测、交易规则校验、绩效分析
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("错误：缺少pandas和numpy，请运行: pip install pandas numpy")
    sys.exit(1)


class BacktestEngine:
    """回测引擎核心类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化回测引擎
        
        Args:
            config_path: 回测配置文件路径
        """
        # 加载配置
        if config_path is None:
            config_path = project_root / "configs" / "backtest_config.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 基础配置
        self.start_date = self.config['date_range']['start_date']
        self.end_date = self.config['date_range']['end_date']
        self.initial_capital = self.config['initial_capital']
        
        # 交易成本配置
        self.slippage = self.config['trading_config']['slippage']
        self.commission_rate = self.config['trading_config']['commission_rate']
        self.min_commission = self.config['trading_config']['min_commission']
        self.stamp_tax = self.config['trading_config']['stamp_tax']
        
        # 风控配置
        self.risk_control = self.config['risk_control']
        
        # 数据存储
        self.historical_data = {}
        self.consensus_data = {}
        
        # 回测状态
        self.current_date = None
        self.cash = self.initial_capital
        self.positions = defaultdict(int)  # {symbol: shares}
        self.portfolio_value_history = []
        self.trades_history = []
        self.daily_positions = []
        
    def load_historical_data(self) -> bool:
        """加载历史行情数据
        
        Returns:
            是否成功加载
        """
        print(f"加载历史数据: {self.start_date} 至 {self.end_date}")
        
        data_file = project_root / "data" / "merged.jsonl"
        if not data_file.exists():
            print(f"错误：数据文件不存在 {data_file}")
            return False
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    doc = json.loads(line)
                    
                    meta = doc.get('Meta Data', {})
                    symbol = meta.get('2. Symbol')
                    if not symbol:
                        continue
                    
                    time_series = doc.get('Time Series (Daily)', {})
                    
                    # 筛选日期范围内的数据
                    filtered_data = {}
                    for date_str, price_data in time_series.items():
                        if self.start_date <= date_str <= self.end_date:
                            filtered_data[date_str] = price_data
                    
                    if filtered_data:
                        self.historical_data[symbol] = filtered_data
            
            print(f"成功加载 {len(self.historical_data)} 只股票的历史数据")
            return True
            
        except Exception as e:
            print(f"加载历史数据失败: {e}")
            return False
    
    def load_consensus_data(self) -> bool:
        """加载共识数据
        
        Returns:
            是否成功加载
        """
        consensus_file = project_root / "data" / "consensus_data.jsonl"
        
        if not consensus_file.exists():
            print("提示：未找到共识数据文件，跳过")
            return True
        
        try:
            with open(consensus_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    
                    date = record.get('date')
                    symbol = record.get('symbol')
                    
                    if date and symbol:
                        if date not in self.consensus_data:
                            self.consensus_data[date] = {}
                        self.consensus_data[date][symbol] = record
            
            print(f"成功加载共识数据")
            return True
            
        except Exception as e:
            print(f"加载共识数据失败: {e}")
            return False
    
    def check_trade_validity(self, symbol: str, action: str, shares: int, 
                            date: str) -> Tuple[bool, Optional[str]]:
        """检查交易合规性
        
        防止未来信息泄露、验证交易规则
        
        Args:
            symbol: 股票代码
            action: 'buy' 或 'sell'
            shares: 股数
            date: 交易日期
            
        Returns:
            (是否合规, 错误信息)
        """
        # 1. 时间旅行检查：确保不使用未来数据
        if date > self.current_date:
            return (False, f"时间旅行错误：不能在{self.current_date}交易{date}的数据")
        
        # 2. 检查股票数据是否存在
        if symbol not in self.historical_data:
            return (False, f"股票{symbol}无历史数据")
        
        if date not in self.historical_data[symbol]:
            return (False, f"股票{symbol}在{date}无交易数据（可能停牌）")
        
        # 3. 买入数量必须是100的整数倍
        if action == 'buy' and shares % 100 != 0:
            return (False, f"买入数量必须是100的整数倍，当前{shares}股")
        
        # 4. 卖出检查持仓
        if action == 'sell':
            if self.positions[symbol] < shares:
                return (False, f"持仓不足：持有{self.positions[symbol]}股，尝试卖出{shares}股")
        
        # 5. 资金检查（买入时）
        if action == 'buy':
            price_data = self.historical_data[symbol][date]
            price = float(price_data.get('1. buy price', 0))
            cost = price * shares * (1 + self.commission_rate + self.slippage)
            
            if cost > self.cash:
                return (False, f"资金不足：需要{cost:.2f}，可用{self.cash:.2f}")
        
        return (True, None)
    
    def execute_order(self, symbol: str, action: str, shares: int, 
                     date: str) -> Dict[str, Any]:
        """执行订单
        
        Args:
            symbol: 股票代码
            action: 'buy' 或 'sell'
            shares: 股数
            date: 交易日期
            
        Returns:
            交易结果字典
        """
        # 检查合规性
        valid, error = self.check_trade_validity(symbol, action, shares, date)
        if not valid:
            return {"success": False, "error": error}
        
        # 获取价格
        price_data = self.historical_data[symbol][date]
        
        if action == 'buy':
            # 使用开盘价买入，加滑点
            price = float(price_data.get('1. buy price', 0)) * (1 + self.slippage)
            commission = max(price * shares * self.commission_rate, self.min_commission)
            total_cost = price * shares + commission
            
            self.cash -= total_cost
            self.positions[symbol] += shares
            
            # 记录交易
            trade_record = {
                "date": date,
                "symbol": symbol,
                "action": "buy",
                "shares": shares,
                "price": price,
                "commission": commission,
                "total_cost": total_cost
            }
            
        else:  # sell
            # 使用收盘价卖出，减滑点
            price = float(price_data.get('4. sell price', 0)) * (1 - self.slippage)
            commission = max(price * shares * self.commission_rate, self.min_commission)
            stamp_tax_cost = price * shares * self.stamp_tax
            total_revenue = price * shares - commission - stamp_tax_cost
            
            self.cash += total_revenue
            self.positions[symbol] -= shares
            
            # 记录交易
            trade_record = {
                "date": date,
                "symbol": symbol,
                "action": "sell",
                "shares": shares,
                "price": price,
                "commission": commission,
                "stamp_tax": stamp_tax_cost,
                "total_revenue": total_revenue
            }
        
        self.trades_history.append(trade_record)
        
        return {"success": True, "trade": trade_record}
    
    def calculate_portfolio_value(self, date: str) -> float:
        """计算当前组合总价值
        
        Args:
            date: 日期
            
        Returns:
            组合总价值
        """
        total_value = self.cash
        
        for symbol, shares in self.positions.items():
            if shares > 0 and symbol in self.historical_data:
                if date in self.historical_data[symbol]:
                    price_data = self.historical_data[symbol][date]
                    close_price = float(price_data.get('4. sell price', 0))
                    total_value += close_price * shares
        
        return total_value
    
    def simulate_trading_day(self, date: str, agent_decisions: List[Dict]) -> Dict[str, Any]:
        """模拟单日交易
        
        Args:
            date: 交易日期
            agent_decisions: AI Agent的决策列表 [{"action": "buy/sell", "symbol": "...", "shares": 100}, ...]
            
        Returns:
            当日交易结果汇总
        """
        self.current_date = date
        day_trades = []
        
        # 执行所有决策
        for decision in agent_decisions:
            result = self.execute_order(
                symbol=decision['symbol'],
                action=decision['action'],
                shares=decision['shares'],
                date=date
            )
            day_trades.append(result)
        
        # 计算当日组合价值
        portfolio_value = self.calculate_portfolio_value(date)
        
        # 记录
        self.portfolio_value_history.append({
            "date": date,
            "portfolio_value": portfolio_value,
            "cash": self.cash,
            "positions": dict(self.positions)
        })
        
        return {
            "date": date,
            "trades_count": len([t for t in day_trades if t.get('success')]),
            "portfolio_value": portfolio_value,
            "cash": self.cash
        }
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """计算回测绩效指标
        
        Returns:
            绩效指标字典
        """
        if not self.portfolio_value_history:
            return {}
        
        # 转为DataFrame便于计算
        df = pd.DataFrame(self.portfolio_value_history)
        
        # 总收益率
        final_value = df.iloc[-1]['portfolio_value']
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # 年化收益率
        days = len(df)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        # 最大回撤
        df['cummax'] = df['portfolio_value'].cummax()
        df['drawdown'] = (df['portfolio_value'] - df['cummax']) / df['cummax']
        max_drawdown = df['drawdown'].min()
        
        # 夏普比率（简化计算）
        df['daily_return'] = df['portfolio_value'].pct_change()
        sharpe_ratio = df['daily_return'].mean() / df['daily_return'].std() * np.sqrt(252) if df['daily_return'].std() > 0 else 0
        
        # 交易统计
        total_trades = len(self.trades_history)
        buy_trades = len([t for t in self.trades_history if t['action'] == 'buy'])
        sell_trades = len([t for t in self.trades_history if t['action'] == 'sell'])
        
        return {
            "total_return": round(total_return * 100, 2),
            "annual_return": round(annual_return * 100, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "final_value": round(final_value, 2),
            "total_trades": total_trades,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "days": days
        }
    
    def generate_report(self, output_dir: Optional[str] = None) -> str:
        """生成回测报告
        
        Args:
            output_dir: 输出目录
            
        Returns:
            报告文件路径
        """
        if output_dir is None:
            output_dir = project_root / "data" / "backtest_results" / datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存交易明细
        trades_file = output_path / "trades.jsonl"
        with open(trades_file, 'w', encoding='utf-8') as f:
            for trade in self.trades_history:
                f.write(json.dumps(trade, ensure_ascii=False) + '\n')
        
        # 保存每日持仓
        positions_file = output_path / "daily_positions.jsonl"
        with open(positions_file, 'w', encoding='utf-8') as f:
            for record in self.portfolio_value_history:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        # 保存绩效指标
        metrics = self.calculate_metrics()
        metrics_file = output_path / "metrics.json"
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        
        print(f"\n回测报告已生成: {output_path}")
        print(f"- 交易明细: {trades_file}")
        print(f"- 每日持仓: {positions_file}")
        print(f"- 绩效指标: {metrics_file}")
        
        return str(output_path)
    
    def run(self, agent_callback=None) -> Dict[str, Any]:
        """运行完整回测
        
        Args:
            agent_callback: Agent决策回调函数 callback(date, portfolio_state) -> decisions
            
        Returns:
            回测结果
        """
        print(f"\n========== 回测开始 ==========")
        print(f"时间范围: {self.start_date} - {self.end_date}")
        print(f"初始资金: {self.initial_capital:,.2f}")
        
        # 加载数据
        if not self.load_historical_data():
            return {"error": "历史数据加载失败"}
        
        self.load_consensus_data()
        
        # 生成交易日列表
        start_dt = datetime.strptime(self.start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(self.end_date, '%Y-%m-%d')
        
        current_dt = start_dt
        trading_days = []
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y-%m-%d')
            trading_days.append(date_str)
            current_dt += timedelta(days=1)
        
        # 逐日回测
        for i, date in enumerate(trading_days):
            # 如果没有agent_callback，使用简单的持有策略
            if agent_callback is None:
                decisions = []
            else:
                portfolio_state = {
                    "date": date,
                    "cash": self.cash,
                    "positions": dict(self.positions)
                }
                decisions = agent_callback(date, portfolio_state)
            
            result = self.simulate_trading_day(date, decisions)
            
            if (i + 1) % 30 == 0:
                print(f"进度: {i+1}/{len(trading_days)} 天, 组合价值: {result['portfolio_value']:,.2f}")
        
        # 计算绩效
        metrics = self.calculate_metrics()
        
        print(f"\n========== 回测完成 ==========")
        print(f"总收益率: {metrics.get('total_return', 0)}%")
        print(f"年化收益率: {metrics.get('annual_return', 0)}%")
        print(f"最大回撤: {metrics.get('max_drawdown', 0)}%")
        print(f"夏普比率: {metrics.get('sharpe_ratio', 0)}")
        print(f"总交易次数: {metrics.get('total_trades', 0)}")
        
        return metrics


def main():
    """示例：运行回测"""
    engine = BacktestEngine()
    
    # 简单示例：买入持有策略
    def simple_buy_and_hold(date, portfolio_state):
        """简单的买入持有策略"""
        # 第一天买入
        if portfolio_state['cash'] > 50000 and not portfolio_state['positions']:
            return [
                {"symbol": "600519.SH", "action": "buy", "shares": 100}
            ]
        return []
    
    # 运行回测
    results = engine.run(agent_callback=simple_buy_and_hold)
    
    # 生成报告
    engine.generate_report()


if __name__ == "__main__":
    main()
