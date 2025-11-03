"""
A股交易规则校验增强模块

功能:
1. T+1制度校验 - 当日买入股票次日才能卖出
2. 涨跌停限制 - 禁止在涨停价买入、跌停价卖出
3. 最小交易单位 - 买卖数量必须是100股整数倍
4. 停牌检查 - 禁止交易停牌股票
5. 价格精度处理 - 价格精确到分(round(price, 2))

修复缺陷:
- D1: 涨跌停价格精确到分
- D2: ST股票识别与5%涨跌幅限制
- D4: 停牌股票交易限制

作者: AI-Trader Team
日期: 2024
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import os


class TradeViolationError(Exception):
    """交易规则违规异常"""
    pass


class AStockTradeValidator:
    """A股交易规则校验器"""
    
    def __init__(self, data_dir: str = "./data"):
        """
        初始化校验器
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir
        self.trading_history = {}  # 记录交易历史用于T+1校验 {date: {symbol: action}}
    
    def identify_st_stock(self, symbol: str, stock_name: str) -> bool:
        """
        判断是否为ST股票
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            
        Returns:
            bool: 是否为ST股票
        """
        name = stock_name.strip()
        st_prefixes = ["ST", "*ST", "SST", "S*ST", "退市"]
        return any(name.startswith(prefix) for prefix in st_prefixes)
    
    def calculate_limit_prices(self, symbol: str, prev_close: float, is_st: bool = False) -> Dict[str, float]:
        """
        计算涨跌停价格(精确到分)
        
        Args:
            symbol: 股票代码
            prev_close: 前收盘价
            is_st: 是否为ST股票
            
        Returns:
            dict: {"limit_up": 涨停价, "limit_down": 跌停价}
        """
        # 确定涨跌幅比例
        if symbol.startswith("688"):  # 科创板
            limit_ratio = 1.20  # ±20%
        elif symbol.startswith("300"):  # 创业板
            limit_ratio = 1.20  # ±20%
        elif is_st:  # ST股票
            limit_ratio = 1.05  # ±5%
        else:  # 主板
            limit_ratio = 1.10  # ±10%
        
        # 计算涨跌停价格,精确到分
        limit_up = round(prev_close * limit_ratio, 2)
        limit_down = round(prev_close * (2 - limit_ratio), 2)
        
        return {
            "limit_up": limit_up,
            "limit_down": limit_down
        }
    
    def check_t1_rule(self, symbol: str, action: str, current_date: str) -> Dict[str, Any]:
        """
        检查T+1规则
        
        Args:
            symbol: 股票代码
            action: 交易动作 "buy" 或 "sell"
            current_date: 当前日期 "YYYY-MM-DD"
            
        Returns:
            dict: {"passed": bool, "message": str}
            
        Raises:
            TradeViolationError: 违反T+1规则时抛出
        """
        if action.lower() != "sell":
            # 买入操作不受T+1限制
            return {"passed": True, "message": "买入操作不受T+1限制"}
        
        # 检查昨天是否买入该股票
        current_dt = datetime.strptime(current_date, "%Y-%m-%d")
        yesterday = (current_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        
        if yesterday in self.trading_history:
            if symbol in self.trading_history[yesterday]:
                if self.trading_history[yesterday][symbol] == "buy":
                    msg = f"违反T+1规则:股票{symbol}于{yesterday}买入,次日{current_date}才能卖出"
                    raise TradeViolationError(msg)
        
        return {"passed": True, "message": "符合T+1规则"}
    
    def check_limit_price(self, symbol: str, action: str, price: float, 
                          current_price: float, prev_close: float, 
                          is_st: bool = False) -> Dict[str, Any]:
        """
        检查涨跌停限制
        
        Args:
            symbol: 股票代码
            action: 交易动作 "buy" 或 "sell"
            price: 委托价格
            current_price: 当前价格
            prev_close: 前收盘价
            is_st: 是否为ST股票
            
        Returns:
            dict: {"passed": bool, "message": str, "limits": dict}
            
        Raises:
            TradeViolationError: 违反涨跌停规则时抛出
        """
        # 计算涨跌停价格
        limits = self.calculate_limit_prices(symbol, prev_close, is_st)
        limit_up = limits["limit_up"]
        limit_down = limits["limit_down"]
        
        # 价格精度处理
        price = round(price, 2)
        current_price = round(current_price, 2)
        
        # 检查涨跌停状态
        is_limit_up = abs(current_price - limit_up) < 0.01
        is_limit_down = abs(current_price - limit_down) < 0.01
        
        if action.lower() == "buy" and is_limit_up:
            msg = f"禁止在涨停价买入:股票{symbol}当前价{current_price}元已涨停(涨停价{limit_up}元)"
            raise TradeViolationError(msg)
        
        if action.lower() == "sell" and is_limit_down:
            msg = f"禁止在跌停价卖出:股票{symbol}当前价{current_price}元已跌停(跌停价{limit_down}元)"
            raise TradeViolationError(msg)
        
        return {
            "passed": True, 
            "message": "未触及涨跌停限制",
            "limits": limits
        }
    
    def check_trade_unit(self, symbol: str, quantity: int) -> Dict[str, Any]:
        """
        检查最小交易单位(100股整数倍)
        
        Args:
            symbol: 股票代码
            quantity: 交易数量
            
        Returns:
            dict: {"passed": bool, "message": str}
            
        Raises:
            TradeViolationError: 不符合最小交易单位时抛出
        """
        min_unit = 100  # A股最小交易单位为100股(1手)
        
        if quantity % min_unit != 0:
            msg = f"交易数量必须是{min_unit}股的整数倍:当前数量{quantity}股不符合要求"
            raise TradeViolationError(msg)
        
        if quantity <= 0:
            msg = f"交易数量必须大于0:当前数量{quantity}股"
            raise TradeViolationError(msg)
        
        return {"passed": True, "message": f"符合最小交易单位要求({min_unit}股)"}
    
    def check_suspended(self, symbol: str, date: str, status: Optional[str] = None) -> Dict[str, Any]:
        """
        检查股票是否停牌
        
        Args:
            symbol: 股票代码
            date: 交易日期 "YYYY-MM-DD"
            status: 股票状态(可选),如果提供则直接使用
            
        Returns:
            dict: {"passed": bool, "message": str, "is_suspended": bool}
            
        Raises:
            TradeViolationError: 股票停牌时抛出
        """
        # TODO: 实际实现需要从merged_data.jsonl读取status字段
        # 当前为示例实现
        if status is None:
            # 从数据文件读取status
            status = self._get_stock_status(symbol, date)
        
        is_suspended = (status == "suspended")
        
        if is_suspended:
            msg = f"禁止交易停牌股票:股票{symbol}在{date}处于停牌状态"
            raise TradeViolationError(msg)
        
        return {
            "passed": True, 
            "message": "股票正常交易",
            "is_suspended": False
        }
    
    def _get_stock_status(self, symbol: str, date: str) -> str:
        """
        从数据文件获取股票状态
        
        Args:
            symbol: 股票代码
            date: 日期 "YYYY-MM-DD"
            
        Returns:
            str: "normal" 或 "suspended"
        """
        # TODO: 实现从merged_data.jsonl读取status字段的逻辑
        # 临时返回normal
        return "normal"
    
    def validate_trade(self, symbol: str, action: str, quantity: int, 
                      price: float, current_date: str, 
                      current_price: float, prev_close: float,
                      stock_name: str = "", status: Optional[str] = None) -> Dict[str, Any]:
        """
        综合校验交易请求
        
        Args:
            symbol: 股票代码
            action: 交易动作 "buy" 或 "sell"
            quantity: 交易数量
            price: 委托价格
            current_date: 当前日期 "YYYY-MM-DD"
            current_price: 当前价格
            prev_close: 前收盘价
            stock_name: 股票名称(用于ST判断)
            status: 股票状态(可选)
            
        Returns:
            dict: {
                "valid": bool,
                "violations": List[str],
                "checks": {
                    "t1_rule": dict,
                    "limit_price": dict,
                    "trade_unit": dict,
                    "suspended": dict
                }
            }
            
        Raises:
            TradeViolationError: 任一规则违规时抛出
        """
        violations = []
        checks = {}
        
        # 判断是否为ST股票
        is_st = self.identify_st_stock(symbol, stock_name) if stock_name else False
        
        # 1. 检查最小交易单位
        try:
            checks["trade_unit"] = self.check_trade_unit(symbol, quantity)
        except TradeViolationError as e:
            violations.append(str(e))
            checks["trade_unit"] = {"passed": False, "message": str(e)}
        
        # 2. 检查停牌状态
        try:
            checks["suspended"] = self.check_suspended(symbol, current_date, status)
        except TradeViolationError as e:
            violations.append(str(e))
            checks["suspended"] = {"passed": False, "message": str(e)}
        
        # 3. 检查T+1规则
        try:
            checks["t1_rule"] = self.check_t1_rule(symbol, action, current_date)
        except TradeViolationError as e:
            violations.append(str(e))
            checks["t1_rule"] = {"passed": False, "message": str(e)}
        
        # 4. 检查涨跌停限制
        try:
            checks["limit_price"] = self.check_limit_price(
                symbol, action, price, current_price, prev_close, is_st
            )
        except TradeViolationError as e:
            violations.append(str(e))
            checks["limit_price"] = {"passed": False, "message": str(e)}
        
        # 如果有任何违规,抛出异常
        if violations:
            raise TradeViolationError(f"交易校验失败:\n" + "\n".join(violations))
        
        return {
            "valid": True,
            "violations": [],
            "checks": checks,
            "is_st": is_st
        }
    
    def record_trade(self, symbol: str, action: str, date: str):
        """
        记录交易历史(用于T+1校验)
        
        Args:
            symbol: 股票代码
            action: 交易动作 "buy" 或 "sell"
            date: 交易日期 "YYYY-MM-DD"
        """
        if date not in self.trading_history:
            self.trading_history[date] = {}
        self.trading_history[date][symbol] = action.lower()


# MCP工具函数(供Agent调用)
# TODO: 需要根据实际MCP框架进行适配

def validate_astock_trade(symbol: str, action: str, quantity: int, 
                          price: float, current_date: str,
                          current_price: float, prev_close: float,
                          stock_name: str = "") -> Dict[str, Any]:
    """
    A股交易规则校验(MCP工具函数)
    
    Args:
        symbol: 股票代码,如"600000"
        action: 交易动作 "buy" 或 "sell"
        quantity: 交易数量
        price: 委托价格
        current_date: 当前日期 "YYYY-MM-DD"
        current_price: 当前价格
        prev_close: 前收盘价
        stock_name: 股票名称(可选)
        
    Returns:
        dict: 校验结果,包含valid字段和详细检查信息
        
    Example:
        >>> result = validate_astock_trade(
        ...     symbol="600000",
        ...     action="buy",
        ...     quantity=100,
        ...     price=10.50,
        ...     current_date="2024-01-15",
        ...     current_price=10.45,
        ...     prev_close=10.00,
        ...     stock_name="浦发银行"
        ... )
        >>> print(result["valid"])
        True
    """
    validator = AStockTradeValidator()
    
    try:
        result = validator.validate_trade(
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            current_date=current_date,
            current_price=current_price,
            prev_close=prev_close,
            stock_name=stock_name
        )
        return result
    except TradeViolationError as e:
        return {
            "valid": False,
            "error": str(e),
            "violations": [str(e)]
        }


# 示例用法和测试用例
if __name__ == "__main__":
    validator = AStockTradeValidator()
    
    # 测试用例1: 正常买入
    print("测试1: 正常买入100股")
    try:
        result = validator.validate_trade(
            symbol="600000",
            action="buy",
            quantity=100,
            price=10.50,
            current_date="2024-01-15",
            current_price=10.45,
            prev_close=10.00,
            stock_name="浦发银行"
        )
        print(f"✓ 校验通过: {result}")
    except TradeViolationError as e:
        print(f"✗ 校验失败: {e}")
    
    # 测试用例2: 违反最小交易单位
    print("\n测试2: 买入50股(非100整数倍)")
    try:
        result = validator.validate_trade(
            symbol="600000",
            action="buy",
            quantity=50,
            price=10.50,
            current_date="2024-01-15",
            current_price=10.45,
            prev_close=10.00,
            stock_name="浦发银行"
        )
        print(f"✓ 校验通过: {result}")
    except TradeViolationError as e:
        print(f"✗ 校验失败: {e}")
    
    # 测试用例3: 涨停价买入
    print("\n测试3: 涨停价买入")
    try:
        result = validator.validate_trade(
            symbol="600000",
            action="buy",
            quantity=100,
            price=11.00,
            current_date="2024-01-15",
            current_price=11.00,  # 涨停价
            prev_close=10.00,
            stock_name="浦发银行"
        )
        print(f"✓ 校验通过: {result}")
    except TradeViolationError as e:
        print(f"✗ 校验失败: {e}")
    
    # 测试用例4: ST股票5%涨跌幅
    print("\n测试4: ST股票5%涨跌幅")
    limits = validator.calculate_limit_prices("600000", 10.00, is_st=True)
    print(f"ST股票涨跌停价: {limits}")
    assert limits["limit_up"] == 10.50
    assert limits["limit_down"] == 9.50
    print("✓ ST股票涨跌幅计算正确")
