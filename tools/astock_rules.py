"""
A股交易规则校验工具
包含T+1、涨跌停、停牌检查等A股特有规则
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from tools.general_tools import get_config_value


class AStockRuleValidator:
    """A股交易规则校验器"""
    
    def __init__(self):
        """初始化规则校验器"""
        self.data_dir = project_root / "data"
        self.config_file = project_root / "configs" / "default_config.json"
        
        # 加载配置
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.trading_rules = self.config.get("trading_rules", {})
        self.price_limits = self.trading_rules.get("price_limit", {})
        
    def get_board_type(self, symbol: str) -> str:
        """识别股票所属板块
        
        Args:
            symbol: 股票代码，如 '600519.SH'
            
        Returns:
            板块类型: 'main_board', 'star_market', 'gem_board', 'st_stock'
        """
        # 提取代码前缀
        code = symbol.split('.')[0]
        prefix = code[:3]
        
        # ST股票判断（需要通过股票名称，这里简化处理）
        # 实际应用中应该查询股票基本信息
        
        if prefix == '688':
            return 'star_market'  # 科创板
        elif prefix == '300':
            return 'gem_board'  # 创业板
        else:
            return 'main_board'  # 主板
    
    def get_price_limit(self, symbol: str) -> float:
        """获取股票涨跌幅限制
        
        Args:
            symbol: 股票代码
            
        Returns:
            涨跌幅限制（小数形式，如0.1表示10%）
        """
        board_type = self.get_board_type(symbol)
        return self.price_limits.get(board_type, 0.1)
    
    def check_limit_up(self, symbol: str, current_price: float, prev_close: float) -> bool:
        """检查是否涨停
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            prev_close: 前收盘价
            
        Returns:
            True表示涨停
        """
        limit = self.get_price_limit(symbol)
        limit_up_price = prev_close * (1 + limit)
        
        # 允许0.01的误差
        return current_price >= (limit_up_price - 0.01)
    
    def check_limit_down(self, symbol: str, current_price: float, prev_close: float) -> bool:
        """检查是否跌停
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            prev_close: 前收盘价
            
        Returns:
            True表示跌停
        """
        limit = self.get_price_limit(symbol)
        limit_down_price = prev_close * (1 - limit)
        
        # 允许0.01的误差
        return current_price <= (limit_down_price + 0.01)
    
    def check_suspended(self, symbol: str, date: str) -> bool:
        """检查股票是否停牌
        
        Args:
            symbol: 股票代码
            date: 交易日期 'YYYY-MM-DD'
            
        Returns:
            True表示停牌
        """
        # 从merged.jsonl读取数据检查
        merged_file = self.data_dir / "merged.jsonl"
        
        if not merged_file.exists():
            return False
        
        with open(merged_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                doc = json.loads(line)
                meta = doc.get("Meta Data", {})
                if meta.get("2. Symbol") != symbol:
                    continue
                
                series = doc.get("Time Series (Daily)", {})
                # 如果当日无数据，可能是停牌
                if date not in series:
                    return True
                    
                return False
        
        # 未找到股票数据
        return True
    
    def check_t_plus_1(self, symbol: str, current_date: str, signature: str) -> Tuple[bool, Optional[str]]:
        """检查T+1限制（当日买入不可当日卖出）
        
        Args:
            symbol: 股票代码
            current_date: 当前日期 'YYYY-MM-DD'
            signature: 模型签名
            
        Returns:
            (是否可以卖出, 错误信息)
        """
        t_plus = self.trading_rules.get("t_plus", 1)
        if t_plus == 0:
            return (True, None)
        
        # 读取持仓记录，检查最近买入日期
        position_file = project_root / "data" / "agent_data" / signature / "position" / "position.jsonl"
        
        if not position_file.exists():
            return (True, None)
        
        # 查找最近一次买入该股票的日期
        last_buy_date = None
        with open(position_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                action = record.get('this_action', {})
                
                if action.get('action') == 'buy' and action.get('symbol') == symbol:
                    last_buy_date = record.get('date')
        
        if last_buy_date is None:
            return (True, None)
        
        # 检查是否同一天
        if last_buy_date == current_date:
            return (False, f"T+{t_plus}规则：{current_date}买入的股票需要{t_plus}个交易日后才能卖出")
        
        return (True, None)
    
    def check_min_trade_unit(self, amount: int, action: str) -> Tuple[bool, Optional[str]]:
        """检查最小交易单位（买入必须100股整数倍）
        
        Args:
            amount: 交易数量
            action: 'buy' 或 'sell'
            
        Returns:
            (是否合规, 错误信息)
        """
        min_unit = self.trading_rules.get("min_unit", 100)
        
        if action == 'buy':
            if amount % min_unit != 0:
                return (False, f"买入数量必须是{min_unit}股的整数倍（1手={min_unit}股）")
        
        # 卖出可以有零股
        return (True, None)
    
    def validate_trade_rules(self, symbol: str, amount: int, action: str, 
                           current_date: str, signature: str) -> Dict[str, Any]:
        """综合校验交易规则
        
        Args:
            symbol: 股票代码
            amount: 交易数量
            action: 'buy' 或 'sell'
            current_date: 交易日期
            signature: 模型签名
            
        Returns:
            {"valid": bool, "error": str or None}
        """
        # 1. 检查最小交易单位
        valid, error = self.check_min_trade_unit(amount, action)
        if not valid:
            return {"valid": False, "error": error}
        
        # 2. 检查停牌
        if self.check_suspended(symbol, current_date):
            return {"valid": False, "error": f"股票{symbol}在{current_date}停牌，无法交易"}
        
        # 3. T+1检查（仅卖出时）
        if action == 'sell':
            valid, error = self.check_t_plus_1(symbol, current_date, signature)
            if not valid:
                return {"valid": False, "error": error}
        
        # 4. 涨跌停检查需要获取价格数据
        # 这部分在实际交易时进行
        
        return {"valid": True, "error": None}


# 全局实例
_validator = None

def get_validator() -> AStockRuleValidator:
    """获取全局规则校验器实例"""
    global _validator
    if _validator is None:
        _validator = AStockRuleValidator()
    return _validator


def validate_trade_rules(symbol: str, amount: int, action: str, 
                        current_date: str, signature: str) -> Dict[str, Any]:
    """便捷函数：校验交易规则
    
    Args:
        symbol: 股票代码
        amount: 交易数量
        action: 'buy' 或 'sell'
        current_date: 交易日期
        signature: 模型签名
        
    Returns:
        {"valid": bool, "error": str or None}
    """
    validator = get_validator()
    return validator.validate_trade_rules(symbol, amount, action, current_date, signature)
