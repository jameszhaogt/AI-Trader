"""
共识分数计算单元测试

测试用例编号: UT-CS-001 ~ UT-CS-005
测试目标: agent_tools/tool_consensus_filter.py

作者: AI-Trader Team
日期: 2024
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_tools.tool_consensus_filter import (
    ConsensusScorer,
    filter_stocks_by_consensus
)


class TestTechnicalScore:
    """UT-CS-001: 技术面分数计算测试"""
    
    def test_bullish_pattern(self):
        """测试多头形态得高分"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        price_data = {
            "close": 10.50,
            "prev_close": 10.00,
            "ma5": 10.30,
            "ma10": 10.00,
            "ma20": 9.80,  # 多头排列
            "macd": 0.15,
            "macd_signal": 0.10,  # 金叉
            "volume": 15000000,
            "avg_volume": 10000000,  # 放量上涨
            "high_60d": 10.40,
            "low_60d": 9.00
        }
        
        result = scorer.calculate_technical_score(price_data)
        
        assert result["score"] >= 15  # 应该得高分
        assert result["details"]["ma_score"] == 5.0
        assert result["details"]["macd_score"] == 5.0
        assert len(result["missing_fields"]) == 0
    
    def test_bearish_pattern(self):
        """测试空头形态得低分"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        price_data = {
            "close": 9.50,
            "prev_close": 10.00,
            "ma5": 9.70,
            "ma10": 10.00,
            "ma20": 10.20,  # 空头排列
            "macd": -0.15,
            "macd_signal": -0.10,  # 死叉
            "volume": 8000000,
            "avg_volume": 10000000,  # 缩量下跌
            "high_60d": 11.00,
            "low_60d": 9.50
        }
        
        result = scorer.calculate_technical_score(price_data)
        
        assert result["score"] <= 10  # 应该得低分
        assert result["details"]["ma_score"] == -5.0
        assert result["details"]["macd_score"] == -5.0
    
    def test_missing_data_handling(self):
        """测试数据缺失处理"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        # 只提供部分数据
        price_data = {
            "close": 10.50,
            "prev_close": 10.00,
            "ma5": 10.30,
            # ma10, ma20缺失
        }
        
        result = scorer.calculate_technical_score(price_data)
        
        assert "ma10" in result["missing_fields"]
        assert "ma20" in result["missing_fields"]
        assert result["details"]["ma_score"] == 0.0  # 缺失记0分


class TestCapitalScore:
    """UT-CS-002: 资金面分数计算测试"""
    
    def test_strong_inflow(self):
        """测试资金大幅流入得高分"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        consensus_data = {
            "northbound": {"net_amount": 2000},  # 净流入2000万
            "margin": {
                "margin_balance": 50000,
                "margin_balance_change_pct": 8  # 融资余额增长8%
            },
            "net_flow": 8000  # 主力净流入8000万
        }
        
        result = scorer.calculate_capital_score(consensus_data)
        
        assert result["score"] >= 20  # 应该得高分
        assert result["details"]["northbound_score"] == 10.0
        assert result["details"]["margin_score"] == 10.0
    
    def test_strong_outflow(self):
        """测试资金大幅流出得低分"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        consensus_data = {
            "northbound": {"net_amount": -2000},  # 净流出
            "margin": {
                "margin_balance": 50000,
                "margin_balance_change_pct": -8  # 融资余额减少
            },
            "net_flow": -8000  # 主力净流出
        }
        
        result = scorer.calculate_capital_score(consensus_data)
        
        assert result["score"] <= 10
        assert result["details"]["northbound_score"] == -10.0
    
    def test_missing_northbound_data(self):
        """测试北向资金数据缺失"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        consensus_data = {
            "northbound": {"net_amount": None},  # 数据缺失
            "margin": {"margin_balance": 50000},
        }
        
        result = scorer.calculate_capital_score(consensus_data)
        
        assert "northbound.net_amount" in result["missing_fields"]
        assert result["details"]["northbound_score"] == 0.0


class TestLogicScore:
    """UT-CS-003: 逻辑面分数计算测试"""
    
    def test_strong_buy_rating(self):
        """测试买入评级得高分"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        consensus_data = {
            "ratings": {
                "rating": "买入",
                "rating_change": "上调"
            },
            "industry": {
                "pct_change": 3.5  # 行业涨幅3.5%
            }
        }
        
        result = scorer.calculate_logic_score(consensus_data)
        
        assert result["score"] >= 20
        assert result["details"]["rating_score"] == 10.0
        assert result["details"]["rating_change_score"] == 10.0
    
    def test_sell_rating(self):
        """测试卖出评级得低分"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        consensus_data = {
            "ratings": {
                "rating": "卖出",
                "rating_change": "下调"
            },
            "industry": {
                "pct_change": -3.5
            }
        }
        
        result = scorer.calculate_logic_score(consensus_data)
        
        assert result["score"] <= 10
        assert result["details"]["rating_score"] == -10.0
        assert result["details"]["rating_change_score"] == -10.0


class TestSentimentScore:
    """UT-CS-004: 情绪面分数计算测试"""
    
    def test_high_heat(self):
        """测试高热度得高分"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        consensus_data = {
            "social_heat_rank": 50,
            "total_stocks": 5000,  # 排名前1%
            "search_index_change": 80  # 搜索量暴涨80%
        }
        
        result = scorer.calculate_sentiment_score(consensus_data)
        
        assert result["score"] >= 15
        assert result["details"]["social_score"] == 10.0
        assert result["details"]["search_score"] == 10.0
    
    def test_low_heat(self):
        """测试低热度得低分"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        consensus_data = {
            "social_heat_rank": 4500,
            "total_stocks": 5000,  # 排名后10%
            "search_index_change": -60  # 搜索量下跌60%
        }
        
        result = scorer.calculate_sentiment_score(consensus_data)
        
        assert result["score"] <= 5
        assert result["details"]["social_score"] == -10.0
        assert result["details"]["search_score"] == -10.0


class TestDataMissing:
    """UT-CS-005: 数据缺失处理测试(D3缺陷修复验证)"""
    
    def test_all_data_complete(self):
        """测试完整数据"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        price_data = {
            "close": 10.50,
            "prev_close": 10.00,
            "ma5": 10.30,
            "ma10": 10.00,
            "ma20": 9.80,
            "macd": 0.15,
            "macd_signal": 0.10,
            "volume": 15000000,
            "avg_volume": 10000000,
            "high_60d": 10.40,
            "low_60d": 9.00
        }
        
        consensus_data = {
            "northbound": {"net_amount": 1500},
            "margin": {"margin_balance": 50000, "margin_balance_change_pct": 6},
            "ratings": {"rating": "买入", "rating_change": "上调"},
            "industry": {"pct_change": 3.5},
            "net_flow": 6000
        }
        
        result = scorer.calculate_total_score("600000", "2024-01-15", 
                                             price_data, consensus_data)
        
        assert result["data_completeness"] == 100.0
        assert len(result["all_missing_fields"]) == 0
    
    def test_partial_data_missing(self):
        """测试部分数据缺失"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        price_data = {
            "close": 10.50,
            "prev_close": 10.00,
            # ma数据缺失
        }
        
        consensus_data = {
            "northbound": {"net_amount": None},  # 缺失
            "margin": {},  # 缺失
            "ratings": {"rating": "买入", "rating_change": None},  # 部分缺失
        }
        
        result = scorer.calculate_total_score("600000", "2024-01-15",
                                             price_data, consensus_data)
        
        # 验证缺失维度记0分
        assert result["technical"]["score"] >= 0
        assert result["capital"]["score"] >= 0
        assert result["logic"]["score"] >= 0
        assert result["sentiment"]["score"] >= 0
        
        # 验证数据完整度降低
        assert result["data_completeness"] < 100.0
        assert len(result["all_missing_fields"]) > 0
    
    def test_all_data_missing(self):
        """测试所有数据缺失"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        price_data = {}
        consensus_data = {}
        
        result = scorer.calculate_total_score("600000", "2024-01-15",
                                             price_data, consensus_data)
        
        # 缺失数据记0分,总分应该很低但不会抛出异常
        assert result["total_score"] >= 0
        assert result["data_completeness"] < 50.0
    
    def test_missing_score_not_affect_other_dimensions(self):
        """测试缺失维度不影响其他维度"""
        scorer = ConsensusScorer(missing_score=0.0)
        
        price_data = {
            "close": 10.50,
            "prev_close": 10.00,
            "ma5": 10.30,
            "ma10": 10.00,
            "ma20": 9.80,
            "macd": 0.15,
            "macd_signal": 0.10,
            "volume": 15000000,
            "avg_volume": 10000000,
            "high_60d": 10.40,
            "low_60d": 9.00
        }
        
        consensus_data = {
            "northbound": {"net_amount": None},  # 资金面缺失
            "margin": {},
            "ratings": {"rating": "买入", "rating_change": "上调"},  # 逻辑面完整
            "industry": {"pct_change": 3.5}
        }
        
        result = scorer.calculate_total_score("600000", "2024-01-15",
                                             price_data, consensus_data)
        
        # 技术面应该有正常分数
        assert result["technical"]["score"] > 10
        
        # 资金面缺失,记0分
        assert result["capital"]["score"] < 15  # 因为有部分缺失
        
        # 逻辑面应该有正常分数
        assert result["logic"]["score"] > 10


class TestStockFiltering:
    """测试股票筛选功能"""
    
    def test_filter_by_min_score(self):
        """测试按最低分数筛选"""
        stocks_data = [
            {"symbol": "600000", "total_score": 75, "data_completeness": 80},
            {"symbol": "600036", "total_score": 65, "data_completeness": 90},
            {"symbol": "600519", "total_score": 80, "data_completeness": 85},
        ]
        
        filtered = filter_stocks_by_consensus(stocks_data, min_score=70)
        
        assert len(filtered) == 2
        assert filtered[0]["symbol"] == "600519"  # 最高分排第一
        assert filtered[1]["symbol"] == "600000"
    
    def test_filter_by_completeness(self):
        """测试按数据完整度筛选"""
        stocks_data = [
            {"symbol": "600000", "total_score": 75, "data_completeness": 45},
            {"symbol": "600036", "total_score": 75, "data_completeness": 90},
        ]
        
        filtered = filter_stocks_by_consensus(stocks_data, 
                                             min_score=70, 
                                             min_completeness=50)
        
        assert len(filtered) == 1
        assert filtered[0]["symbol"] == "600036"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
