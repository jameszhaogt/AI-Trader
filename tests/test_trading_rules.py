"""
A股交易规则单元测试

测试用例编号: UT-TR-001 ~ UT-TR-009
测试目标: agent_tools/tool_trade_astock.py

作者: AI-Trader Team
日期: 2024
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_tools.tool_trade_astock import (
    AStockTradeValidator,
    TradeViolationError,
    validate_astock_trade
)


class TestT1Rule:
    """UT-TR-001: T+1规则测试"""
    
    def test_buy_not_restricted(self):
        """测试买入操作不受T+1限制"""
        validator = AStockTradeValidator()
        result = validator.check_t1_rule("600000", "buy", "2024-01-15")
        assert result["passed"] is True
        assert "不受T+1限制" in result["message"]
    
    def test_sell_same_day_violation(self):
        """测试当日买入当日卖出违规"""
        validator = AStockTradeValidator()
        
        # 记录今天买入
        validator.record_trade("600000", "buy", "2024-01-15")
        
        # 尝试今天卖出 - 应该失败
        with pytest.raises(TradeViolationError) as exc_info:
            validator.check_t1_rule("600000", "sell", "2024-01-15")
        
        assert "违反T+1规则" in str(exc_info.value)
    
    def test_sell_next_day_allowed(self):
        """测试次日卖出允许"""
        validator = AStockTradeValidator()
        
        # 昨天买入
        validator.record_trade("600000", "buy", "2024-01-14")
        
        # 今天卖出 - 应该成功
        result = validator.check_t1_rule("600000", "sell", "2024-01-15")
        assert result["passed"] is True


class TestLimitPrice:
    """UT-TR-002 & UT-TR-003: 涨跌停限制测试"""
    
    def test_buy_at_limit_up_violation(self):
        """UT-TR-002: 测试涨停价买入被拒绝"""
        validator = AStockTradeValidator()
        
        # 主板股票,前收盘价10元,涨停价11元
        with pytest.raises(TradeViolationError) as exc_info:
            validator.check_limit_price(
                symbol="600000",
                action="buy",
                price=11.00,
                current_price=11.00,  # 涨停
                prev_close=10.00,
                is_st=False
            )
        
        assert "禁止在涨停价买入" in str(exc_info.value)
    
    def test_sell_at_limit_down_violation(self):
        """UT-TR-003: 测试跌停价卖出被拒绝"""
        validator = AStockTradeValidator()
        
        # 主板股票,前收盘价10元,跌停价9元
        with pytest.raises(TradeViolationError) as exc_info:
            validator.check_limit_price(
                symbol="600000",
                action="sell",
                price=9.00,
                current_price=9.00,  # 跌停
                prev_close=10.00,
                is_st=False
            )
        
        assert "禁止在跌停价卖出" in str(exc_info.value)
    
    def test_normal_price_allowed(self):
        """测试正常价格交易允许"""
        validator = AStockTradeValidator()
        
        # 价格在涨跌停范围内
        result = validator.check_limit_price(
            symbol="600000",
            action="buy",
            price=10.50,
            current_price=10.45,
            prev_close=10.00,
            is_st=False
        )
        
        assert result["passed"] is True
        assert result["limits"]["limit_up"] == 11.00
        assert result["limits"]["limit_down"] == 9.00


class TestMinUnit:
    """UT-TR-004: 最小交易单位测试"""
    
    def test_valid_quantity_100(self):
        """测试100股合规"""
        validator = AStockTradeValidator()
        result = validator.check_trade_unit("600000", 100)
        assert result["passed"] is True
    
    def test_valid_quantity_500(self):
        """测试500股合规"""
        validator = AStockTradeValidator()
        result = validator.check_trade_unit("600000", 500)
        assert result["passed"] is True
    
    def test_invalid_quantity_50(self):
        """测试50股不合规"""
        validator = AStockTradeValidator()
        
        with pytest.raises(TradeViolationError) as exc_info:
            validator.check_trade_unit("600000", 50)
        
        assert "100股的整数倍" in str(exc_info.value)
    
    def test_invalid_quantity_150(self):
        """测试150股不合规"""
        validator = AStockTradeValidator()
        
        with pytest.raises(TradeViolationError) as exc_info:
            validator.check_trade_unit("600000", 150)
        
        assert "100股的整数倍" in str(exc_info.value)
    
    def test_zero_quantity(self):
        """测试0股不合规"""
        validator = AStockTradeValidator()
        
        with pytest.raises(TradeViolationError) as exc_info:
            validator.check_trade_unit("600000", 0)
        
        assert "必须大于0" in str(exc_info.value)


class TestSuspended:
    """UT-TR-005: 停牌股票交易限制测试"""
    
    def test_suspended_stock_violation(self):
        """测试停牌股票交易被拒绝"""
        validator = AStockTradeValidator()
        
        with pytest.raises(TradeViolationError) as exc_info:
            validator.check_suspended("600000", "2024-01-15", status="suspended")
        
        assert "禁止交易停牌股票" in str(exc_info.value)
    
    def test_normal_stock_allowed(self):
        """测试正常股票交易允许"""
        validator = AStockTradeValidator()
        
        result = validator.check_suspended("600000", "2024-01-15", status="normal")
        assert result["passed"] is True
        assert result["is_suspended"] is False


class TestSTStock:
    """UT-TR-006: ST股票5%涨跌幅测试"""
    
    def test_st_stock_identification(self):
        """测试ST股票识别"""
        validator = AStockTradeValidator()
        
        assert validator.identify_st_stock("600000", "ST浦发") is True
        assert validator.identify_st_stock("600000", "*ST浦发") is True
        assert validator.identify_st_stock("600000", "SST浦发") is True
        assert validator.identify_st_stock("600000", "浦发银行") is False
    
    def test_st_stock_5_percent_limit(self):
        """测试ST股票5%涨跌幅"""
        validator = AStockTradeValidator()
        
        limits = validator.calculate_limit_prices("600000", 10.00, is_st=True)
        
        assert limits["limit_up"] == 10.50  # 10 * 1.05
        assert limits["limit_down"] == 9.50  # 10 * 0.95
    
    def test_normal_stock_10_percent_limit(self):
        """测试普通主板股票10%涨跌幅"""
        validator = AStockTradeValidator()
        
        limits = validator.calculate_limit_prices("600000", 10.00, is_st=False)
        
        assert limits["limit_up"] == 11.00  # 10 * 1.10
        assert limits["limit_down"] == 9.00  # 10 * 0.90


class TestStarMarket:
    """UT-TR-007: 科创板20%涨跌幅测试"""
    
    def test_star_market_20_percent_limit(self):
        """测试科创板20%涨跌幅"""
        validator = AStockTradeValidator()
        
        # 科创板股票代码以688开头
        limits = validator.calculate_limit_prices("688001", 10.00, is_st=False)
        
        assert limits["limit_up"] == 12.00  # 10 * 1.20
        assert limits["limit_down"] == 8.00  # 10 * 0.80
    
    def test_gem_board_20_percent_limit(self):
        """测试创业板20%涨跌幅"""
        validator = AStockTradeValidator()
        
        # 创业板股票代码以300开头
        limits = validator.calculate_limit_prices("300001", 10.00, is_st=False)
        
        assert limits["limit_up"] == 12.00  # 10 * 1.20
        assert limits["limit_down"] == 8.00  # 10 * 0.80


class TestPricePrecision:
    """UT-TR-008: 价格精度处理测试"""
    
    def test_limit_price_precision(self):
        """测试涨跌停价格精确到分"""
        validator = AStockTradeValidator()
        
        # 前收盘价9.99元
        limits = validator.calculate_limit_prices("600000", 9.99, is_st=False)
        
        # 涨停价应该是10.99,精确到分
        assert limits["limit_up"] == 10.99
        assert limits["limit_down"] == 8.99
        
        # 验证没有浮点数误差
        assert isinstance(limits["limit_up"], float)
        assert len(str(limits["limit_up"]).split('.')[-1]) <= 2


class TestComprehensiveValidation:
    """UT-TR-009: 综合规则校验测试"""
    
    def test_valid_trade(self):
        """测试符合所有规则的交易"""
        validator = AStockTradeValidator()
        
        result = validator.validate_trade(
            symbol="600000",
            action="buy",
            quantity=100,
            price=10.50,
            current_date="2024-01-15",
            current_price=10.45,
            prev_close=10.00,
            stock_name="浦发银行",
            status="normal"
        )
        
        assert result["valid"] is True
        assert len(result["violations"]) == 0
        assert result["is_st"] is False
    
    def test_multiple_violations(self):
        """测试多个规则违规"""
        validator = AStockTradeValidator()
        
        # 记录昨天买入
        validator.record_trade("600000", "buy", "2024-01-14")
        
        with pytest.raises(TradeViolationError) as exc_info:
            validator.validate_trade(
                symbol="600000",
                action="sell",
                quantity=50,  # 违规:不是100整数倍
                price=9.00,
                current_date="2024-01-14",  # 违规:当天卖出
                current_price=9.00,  # 违规:跌停价
                prev_close=10.00,
                stock_name="浦发银行",
                status="normal"
            )
        
        error_msg = str(exc_info.value)
        assert "交易校验失败" in error_msg


class TestToolFunction:
    """测试MCP工具函数"""
    
    def test_validate_astock_trade_valid(self):
        """测试工具函数-有效交易"""
        result = validate_astock_trade(
            symbol="600000",
            action="buy",
            quantity=100,
            price=10.50,
            current_date="2024-01-15",
            current_price=10.45,
            prev_close=10.00,
            stock_name="浦发银行"
        )
        
        assert result["valid"] is True
    
    def test_validate_astock_trade_invalid(self):
        """测试工具函数-无效交易"""
        result = validate_astock_trade(
            symbol="600000",
            action="buy",
            quantity=50,  # 不是100整数倍
            price=10.50,
            current_date="2024-01-15",
            current_price=10.45,
            prev_close=10.00,
            stock_name="浦发银行"
        )
        
        assert result["valid"] is False
        assert "error" in result


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
