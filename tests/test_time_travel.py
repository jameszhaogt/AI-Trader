"""
时间旅行检测单元测试

测试用例编号: UT-TT-001 ~ UT-TT-004
测试目标: tools/backtest_engine.py, agent/backtest_agent.py

作者: AI-Trader Team
日期: 2024
"""

import pytest
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.backtest_engine import BacktestEngine, TimeViolationError


class TestTimeTravelDetection:
    """时间旅行检测测试"""
    
    def setup_method(self):
        """每个测试前的设置"""
        config = {
            "initial_capital": 100000,
            "data_dir": "./tests/test_data",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
        self.engine = BacktestEngine(config)
        
        # 模拟加载一些价格数据
        self.engine.price_data = {
            "600000": {
                "2024-01-15": {"close": 10.50, "open": 10.30, "high": 10.60, "low": 10.20},
                "2024-01-16": {"close": 10.65, "open": 10.55, "high": 10.75, "low": 10.50},
                "2024-01-17": {"close": 10.80, "open": 10.70, "high": 10.90, "low": 10.65},
            }
        }
    
    def test_access_future_price_violation(self):
        """UT-TT-001: 测试访问未来价格数据触发异常"""
        # 设置当前日期为1月15日
        self.engine.current_date = datetime.strptime("2024-01-15", "%Y-%m-%d")
        
        # 尝试访问1月16日的数据(未来数据)
        with pytest.raises(TimeViolationError) as exc_info:
            self.engine.get_price("600000", "2024-01-16", "close")
        
        assert "禁止访问未来数据" in str(exc_info.value)
        assert "2024-01-16" in str(exc_info.value)
    
    def test_access_current_price_allowed(self):
        """UT-TT-002: 测试访问当前日期数据允许"""
        # 设置当前日期为1月15日
        self.engine.current_date = datetime.strptime("2024-01-15", "%Y-%m-%d")
        
        # 访问当天的数据应该成功
        price = self.engine.get_price("600000", "2024-01-15", "close")
        
        assert price == 10.50
    
    def test_access_historical_price_allowed(self):
        """UT-TT-003: 测试访问历史数据允许"""
        # 设置当前日期为1月17日
        self.engine.current_date = datetime.strptime("2024-01-17", "%Y-%m-%d")
        
        # 访问过去的数据应该成功
        price_15 = self.engine.get_price("600000", "2024-01-15", "close")
        price_16 = self.engine.get_price("600000", "2024-01-16", "close")
        
        assert price_15 == 10.50
        assert price_16 == 10.65
    
    def test_no_current_date_set(self):
        """UT-TT-004: 测试未设置当前日期时允许访问(初始化阶段)"""
        # 不设置current_date
        self.engine.current_date = None
        
        # 应该可以访问任意日期的数据
        price = self.engine.get_price("600000", "2024-01-17", "close")
        
        assert price == 10.80


class TestConsensusTimeTravelDetection:
    """共识数据时间旅行检测"""
    
    def setup_method(self):
        """每个测试前的设置"""
        config = {
            "initial_capital": 100000,
            "data_dir": "./tests/test_data",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
        self.engine = BacktestEngine(config)
        
        # 模拟加载共识数据
        self.engine.consensus_data = {
            "600000": {
                "2024-01-15": {"northbound": {"net_amount": 1000}},
                "2024-01-16": {"northbound": {"net_amount": 1500}},
            }
        }
    
    def test_access_future_consensus_violation(self):
        """测试访问未来共识数据触发异常"""
        self.engine.current_date = datetime.strptime("2024-01-15", "%Y-%m-%d")
        
        with pytest.raises(TimeViolationError) as exc_info:
            self.engine.get_consensus("600000", "2024-01-16")
        
        assert "禁止访问未来共识数据" in str(exc_info.value)
    
    def test_access_current_consensus_allowed(self):
        """测试访问当前共识数据允许"""
        self.engine.current_date = datetime.strptime("2024-01-15", "%Y-%m-%d")
        
        consensus = self.engine.get_consensus("600000", "2024-01-15")
        
        assert consensus is not None
        assert consensus["northbound"]["net_amount"] == 1000


class TestBacktestAgentTimeTravel:
    """BacktestAgent时间旅行检测"""
    
    def test_agent_time_travel_check_enabled(self):
        """测试Agent启用时间旅行检测"""
        from agent.backtest_agent import BacktestAgent
        
        config = {
            "data_dir": "./tests/test_data",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital": 100000,
            "enable_time_travel_check": True
        }
        
        agent = BacktestAgent(config)
        
        assert agent.enable_time_travel_check is True
    
    def test_agent_time_travel_check_disabled(self):
        """测试Agent禁用时间旅行检测"""
        from agent.backtest_agent import BacktestAgent
        
        config = {
            "data_dir": "./tests/test_data",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital": 100000,
            "enable_time_travel_check": False
        }
        
        agent = BacktestAgent(config)
        
        assert agent.enable_time_travel_check is False


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
