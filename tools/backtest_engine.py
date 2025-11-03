"""
A股回测引擎

功能:
1. 历史数据加载 - 从本地JSONL文件加载行情/共识数据
2. 交易模拟 - 模拟买卖交易,记录持仓与盈亏
3. 时间旅行验证 - 禁止访问未来数据,抛出TimeViolationError
4. 合规检查 - T+1、涨跌停、最小交易单位等规则校验
5. 绩效计算 - 总收益率、夏普比率、最大回撤等指标
6. 滑点与手续费 - 模拟真实交易成本

修复缺陷:
- D1: 涨跌停价格精度处理
- D2: ST股票识别与限制
- D4: 停牌日处理

作者: AI-Trader Team
日期: 2024
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import os
import logging
import math


class TimeViolationError(Exception):
    """时间旅行违规异常 - 访问了未来数据"""
    pass


class TradeComplianceError(Exception):
    """交易合规异常 - 违反交易规则"""
    pass


@dataclass
class Position:
    """持仓数据类"""
    symbol: str
    quantity: int
    avg_cost: float
    buy_date: str
    current_value: float = 0.0
    unrealized_pnl: float = 0.0


@dataclass
class Trade:
    """交易记录类"""
    date: str
    symbol: str
    action: str  # "buy" or "sell"
    quantity: int
    price: float
    amount: float
    fee: float
    slippage: float


class BacktestEngine:
    """A股回测引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置字典,包含:
                - initial_capital: 初始资金(元)
                - data_dir: 数据目录
                - start_date: 回测开始日期 "YYYY-MM-DD"
                - end_date: 回测结束日期 "YYYY-MM-DD"
                - commission_rate: 手续费率(默认0.0003)
                - slippage_rate: 滑点率(默认0.001)
                - max_positions: 最大持仓数量(默认5)
        """
        self.config = config
        self.initial_capital = config["initial_capital"]
        self.data_dir = config.get("data_dir", "./data")
        self.start_date = datetime.strptime(config["start_date"], "%Y-%m-%d")
        self.end_date = datetime.strptime(config["end_date"], "%Y-%m-%d")
        
        # 交易成本参数
        self.commission_rate = config.get("commission_rate", 0.0003)  # 0.03%
        self.slippage_rate = config.get("slippage_rate", 0.001)  # 0.1%
        
        # 持仓管理
        self.max_positions = config.get("max_positions", 5)
        self.positions: Dict[str, Position] = {}  # {symbol: Position}
        self.cash = self.initial_capital
        
        # 交易记录
        self.trades: List[Trade] = []
        self.daily_values: List[Dict[str, Any]] = []
        
        # 数据加载
        self.price_data: Dict[str, Dict[str, Dict]] = {}  # {symbol: {date: data}}
        self.consensus_data: Dict[str, Dict[str, Dict]] = {}
        
        # 当前模拟日期(用于时间旅行检测)
        self.current_date: Optional[datetime] = None
        
        logging.info(f"回测引擎初始化完成:初始资金{self.initial_capital}元,回测期间{config['start_date']}至{config['end_date']}")
    
    def load_price_data(self, symbols: List[str]):
        """
        加载行情数据
        
        Args:
            symbols: 股票代码列表
        """
        logging.info(f"加载{len(symbols)}只股票的行情数据...")
        
        for symbol in symbols:
            self.price_data[symbol] = {}
            
            # TODO: 从merged_data.jsonl读取数据
            # 当前为示例实现
            filepath = os.path.join(self.data_dir, f"merged_data_{symbol}.jsonl")
            
            if not os.path.exists(filepath):
                logging.warning(f"数据文件不存在: {filepath}")
                continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        date_str = record["date"]
                        self.price_data[symbol][date_str] = record
        
        logging.info(f"行情数据加载完成,共{sum(len(v) for v in self.price_data.values())}条记录")
    
    def load_consensus_data(self, symbols: List[str]):
        """
        加载共识数据
        
        Args:
            symbols: 股票代码列表
        """
        logging.info(f"加载{len(symbols)}只股票的共识数据...")
        
        for symbol in symbols:
            self.consensus_data[symbol] = {}
            
            # TODO: 从consensus_data.jsonl读取
            filepath = os.path.join(self.data_dir, f"consensus_data_{symbol}.jsonl")
            
            if not os.path.exists(filepath):
                logging.warning(f"共识数据文件不存在: {filepath}")
                continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        date_str = record["date"]
                        self.consensus_data[symbol][date_str] = record
        
        logging.info(f"共识数据加载完成")
    
    def get_price(self, symbol: str, date: str, field: str = "close") -> Optional[float]:
        """
        获取指定日期的价格数据(带时间旅行检测)
        
        Args:
            symbol: 股票代码
            date: 日期 "YYYY-MM-DD"
            field: 字段名,如"close", "open", "high", "low"
            
        Returns:
            float: 价格,如果数据不存在返回None
            
        Raises:
            TimeViolationError: 访问未来数据时抛出
        """
        # 时间旅行检测
        query_date = datetime.strptime(date, "%Y-%m-%d")
        if self.current_date and query_date > self.current_date:
            raise TimeViolationError(
                f"禁止访问未来数据:当前日期{self.current_date.strftime('%Y-%m-%d')}, "
                f"尝试访问{date}的数据"
            )
        
        if symbol not in self.price_data:
            return None
        
        if date not in self.price_data[symbol]:
            return None
        
        return self.price_data[symbol][date].get(field)
    
    def get_consensus(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """
        获取共识数据(带时间旅行检测)
        
        Args:
            symbol: 股票代码
            date: 日期 "YYYY-MM-DD"
            
        Returns:
            dict: 共识数据,如果不存在返回None
            
        Raises:
            TimeViolationError: 访问未来数据时抛出
        """
        query_date = datetime.strptime(date, "%Y-%m-%d")
        if self.current_date and query_date > self.current_date:
            raise TimeViolationError(
                f"禁止访问未来共识数据:当前日期{self.current_date.strftime('%Y-%m-%d')}, "
                f"尝试访问{date}的数据"
            )
        
        if symbol not in self.consensus_data:
            return None
        
        return self.consensus_data[symbol].get(date)
    
    def calculate_slippage(self, price: float, action: str) -> float:
        """
        计算滑点
        
        Args:
            price: 原价格
            action: "buy" 或 "sell"
            
        Returns:
            float: 实际成交价格
        """
        if action == "buy":
            # 买入时价格上滑
            return round(price * (1 + self.slippage_rate), 2)
        else:
            # 卖出时价格下滑
            return round(price * (1 - self.slippage_rate), 2)
    
    def calculate_commission(self, amount: float) -> float:
        """
        计算手续费
        
        Args:
            amount: 交易金额
            
        Returns:
            float: 手续费(元),最低5元
        """
        commission = amount * self.commission_rate
        return max(5.0, round(commission, 2))  # 最低5元
    
    def validate_trade_compliance(self, symbol: str, action: str, 
                                  quantity: int, price: float, 
                                  date_str: str) -> Tuple[bool, str]:
        """
        校验交易合规性
        
        Args:
            symbol: 股票代码
            action: 交易动作
            quantity: 数量
            price: 价格
            date_str: 日期
            
        Returns:
            Tuple[bool, str]: (是否合规, 错误信息)
        """
        # 1. 最小交易单位检查(100股)
        if quantity % 100 != 0:
            return False, f"交易数量必须是100股的整数倍:当前{quantity}股"
        
        # 2. 停牌检查
        price_data = self.price_data.get(symbol, {}).get(date_str)
        if price_data and price_data.get("status") == "suspended":
            return False, f"禁止交易停牌股票:{symbol}在{date_str}停牌"
        
        # 3. T+1检查
        if action == "sell":
            if symbol in self.positions:
                buy_date = datetime.strptime(self.positions[symbol].buy_date, "%Y-%m-%d")
                sell_date = datetime.strptime(date_str, "%Y-%m-%d")
                if (sell_date - buy_date).days < 1:
                    return False, f"违反T+1规则:{symbol}当日买入,次日才能卖出"
        
        # 4. 涨跌停检查
        if price_data:
            prev_close = price_data.get("prev_close")
            current_price = price_data.get("close")
            
            if prev_close and current_price:
                # 判断是否ST股票
                is_st = price_data.get("is_st", False)
                
                # 计算涨跌停价格
                if symbol.startswith("688") or symbol.startswith("300"):
                    limit_ratio = 1.20
                elif is_st:
                    limit_ratio = 1.05
                else:
                    limit_ratio = 1.10
                
                limit_up = round(prev_close * limit_ratio, 2)
                limit_down = round(prev_close * (2 - limit_ratio), 2)
                
                # 涨停禁止买入
                if action == "buy" and abs(current_price - limit_up) < 0.01:
                    return False, f"禁止在涨停价买入:{symbol}当前价{current_price}元已涨停"
                
                # 跌停禁止卖出
                if action == "sell" and abs(current_price - limit_down) < 0.01:
                    return False, f"禁止在跌停价卖出:{symbol}当前价{current_price}元已跌停"
        
        return True, ""
    
    def execute_trade(self, symbol: str, action: str, quantity: int, 
                     price: float, date_str: str) -> bool:
        """
        执行交易
        
        Args:
            symbol: 股票代码
            action: "buy" 或 "sell"
            quantity: 数量
            price: 委托价格
            date_str: 交易日期
            
        Returns:
            bool: 是否交易成功
            
        Raises:
            TradeComplianceError: 违反交易规则时抛出
        """
        # 合规检查
        is_compliant, error_msg = self.validate_trade_compliance(
            symbol, action, quantity, price, date_str
        )
        
        if not is_compliant:
            raise TradeComplianceError(error_msg)
        
        # 计算实际成交价格(含滑点)
        actual_price = self.calculate_slippage(price, action)
        amount = actual_price * quantity
        fee = self.calculate_commission(amount)
        slippage = abs(actual_price - price) * quantity
        
        if action == "buy":
            # 买入
            total_cost = amount + fee
            
            if total_cost > self.cash:
                logging.warning(f"资金不足:需要{total_cost}元,可用{self.cash}元")
                return False
            
            # 检查持仓数量限制
            if symbol not in self.positions and len(self.positions) >= self.max_positions:
                logging.warning(f"持仓数量已达上限{self.max_positions}")
                return False
            
            # 更新持仓
            if symbol in self.positions:
                # 加仓
                pos = self.positions[symbol]
                total_quantity = pos.quantity + quantity
                total_cost_value = pos.avg_cost * pos.quantity + amount
                pos.avg_cost = round(total_cost_value / total_quantity, 2)
                pos.quantity = total_quantity
            else:
                # 新建仓位
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=actual_price,
                    buy_date=date_str
                )
            
            # 扣除现金
            self.cash -= total_cost
            
            logging.info(f"买入成功:{date_str} {symbol} {quantity}股 @{actual_price}元,手续费{fee}元")
        
        else:  # sell
            # 卖出
            if symbol not in self.positions:
                logging.warning(f"无持仓:{symbol}")
                return False
            
            pos = self.positions[symbol]
            if pos.quantity < quantity:
                logging.warning(f"持仓不足:需要{quantity}股,持有{pos.quantity}股")
                return False
            
            # 更新持仓
            pos.quantity -= quantity
            total_income = amount - fee
            
            # 如果清仓则删除持仓
            if pos.quantity == 0:
                del self.positions[symbol]
            
            # 增加现金
            self.cash += total_income
            
            logging.info(f"卖出成功:{date_str} {symbol} {quantity}股 @{actual_price}元,手续费{fee}元")
        
        # 记录交易
        trade = Trade(
            date=date_str,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=actual_price,
            amount=amount,
            fee=fee,
            slippage=slippage
        )
        self.trades.append(trade)
        
        return True
    
    def update_positions_value(self, date_str: str):
        """
        更新持仓市值和未实现盈亏
        
        Args:
            date_str: 当前日期
        """
        for symbol, pos in self.positions.items():
            current_price = self.get_price(symbol, date_str, "close")
            
            if current_price:
                pos.current_value = current_price * pos.quantity
                pos.unrealized_pnl = (current_price - pos.avg_cost) * pos.quantity
    
    def calculate_total_value(self, date_str: str) -> float:
        """
        计算账户总资产
        
        Args:
            date_str: 当前日期
            
        Returns:
            float: 总资产(现金+持仓市值)
        """
        self.update_positions_value(date_str)
        positions_value = sum(pos.current_value for pos in self.positions.values())
        return self.cash + positions_value
    
    def run_backtest(self, strategy_func):
        """
        运行回测
        
        Args:
            strategy_func: 策略函数,签名为 func(engine, date_str) -> List[dict]
                          返回交易信号列表: [{"symbol": str, "action": str, "quantity": int, "price": float}]
        """
        logging.info("开始回测...")
        
        current = self.start_date
        
        while current <= self.end_date:
            date_str = current.strftime("%Y-%m-%d")
            self.current_date = current
            
            # 更新持仓市值
            self.update_positions_value(date_str)
            
            # 调用策略函数获取交易信号
            try:
                signals = strategy_func(self, date_str)
                
                # 执行交易信号
                for signal in signals:
                    try:
                        self.execute_trade(
                            symbol=signal["symbol"],
                            action=signal["action"],
                            quantity=signal["quantity"],
                            price=signal["price"],
                            date_str=date_str
                        )
                    except (TradeComplianceError, TimeViolationError) as e:
                        logging.warning(f"交易失败:{e}")
            
            except TimeViolationError as e:
                logging.error(f"时间旅行检测:{e}")
                raise
            
            # 记录每日资产
            total_value = self.calculate_total_value(date_str)
            self.daily_values.append({
                "date": date_str,
                "cash": self.cash,
                "positions_value": total_value - self.cash,
                "total_value": total_value
            })
            
            # 下一交易日
            current += timedelta(days=1)
        
        logging.info("回测完成")
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """
        计算回测绩效指标
        
        Returns:
            dict: 绩效指标,包含:
                - total_return: 总收益率(%)
                - annual_return: 年化收益率(%)
                - max_drawdown: 最大回撤(%)
                - sharpe_ratio: 夏普比率
                - win_rate: 胜率(%)
                - total_trades: 总交易次数
        """
        if not self.daily_values:
            return {}
        
        # 总收益率
        final_value = self.daily_values[-1]["total_value"]
        total_return = (final_value / self.initial_capital - 1) * 100
        
        # 年化收益率
        days = len(self.daily_values)
        years = days / 365.0
        annual_return = ((final_value / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # 最大回撤
        peak = self.initial_capital
        max_dd = 0.0
        for record in self.daily_values:
            value = record["total_value"]
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # 夏普比率(简化计算,假设无风险利率3%)
        returns = []
        for i in range(1, len(self.daily_values)):
            daily_return = (self.daily_values[i]["total_value"] / 
                           self.daily_values[i-1]["total_value"] - 1)
            returns.append(daily_return)
        
        if returns:
            avg_return = sum(returns) / len(returns)
            std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
            risk_free_rate = 0.03 / 365  # 日化无风险利率
            sharpe_ratio = (avg_return - risk_free_rate) / std_return * math.sqrt(365) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 胜率
        winning_trades = sum(1 for t in self.trades if t.action == "sell" and 
                            (t.price - self.positions.get(t.symbol, Position("", 0, t.price, "")).avg_cost) > 0)
        total_trades = len([t for t in self.trades if t.action == "sell"])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": len(self.trades)
        }


# 示例用法
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 配置回测参数
    config = {
        "initial_capital": 100000,
        "data_dir": "./data",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "commission_rate": 0.0003,
        "slippage_rate": 0.001,
        "max_positions": 5
    }
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # TODO: 加载数据
    # engine.load_price_data(["600000", "600036"])
    
    # TODO: 定义策略函数
    def simple_strategy(engine, date_str):
        """示例策略:随机买入"""
        return []
    
    # TODO: 运行回测
    # engine.run_backtest(simple_strategy)
    
    # TODO: 计算绩效
    # metrics = engine.calculate_metrics()
    # print(json.dumps(metrics, indent=2))
    
    print("回测引擎框架已就绪,待实现数据加载和策略逻辑")
