"""
多维共识筛选算法
基于技术、资金、逻辑、情绪四个维度计算股票共识分数并筛选
"""

from fastmcp import FastMCP
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(project_root))

from tools.general_tools import get_config_value

mcp = FastMCP("ConsensusFilter")


class ConsensusScoreCalculator:
    """共识分数计算器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化
        
        Args:
            config: 配置字典，包含各维度权重
        """
        if config is None:
            # 默认权重
            self.weights = {
                "technical": 0.2,
                "capital": 0.3,
                "logic": 0.3,
                "sentiment": 0.2
            }
        else:
            self.weights = config.get('weights', {
                "technical": 0.2,
                "capital": 0.3,
                "logic": 0.3,
                "sentiment": 0.2
            })
    
    def calculate_technical_score(self, data: Dict[str, Any]) -> float:
        """计算技术共识分数 (0-20分)
        
        评分标准:
        - 创年内新高: +5分
        - 均线多头排列: +5分
        - MACD金叉: +5分
        - 放量突破: +5分
        
        Args:
            data: 包含技术指标的数据字典
            
        Returns:
            技术共识分数 (0-20)
        """
        score = 0.0
        max_score = 20.0
        
        # 这里使用简化逻辑，实际应基于技术指标计算
        # 由于技术指标计算较复杂，这里给予默认分数
        
        # 假设从数据中获取技术指标
        year_high = data.get('year_high', False)
        ma_golden_cross = data.get('ma_golden_cross', False)
        macd_positive = data.get('macd_positive', False)
        volume_surge = data.get('volume_surge', False)
        
        if year_high:
            score += 5
        if ma_golden_cross:
            score += 5
        if macd_positive:
            score += 5
        if volume_surge:
            score += 5
        
        return min(score, max_score)
    
    def calculate_capital_score(self, data: Dict[str, Any]) -> float:
        """计算资金共识分数 (0-30分)
        
        评分标准:
        - 北向资金大幅流入(>5000万): +15分
        - 融资余额增长(>5%): +15分
        
        Args:
            data: 包含资金数据的字典
            
        Returns:
            资金共识分数 (0-30)
        """
        score = 0.0
        max_score = 30.0
        
        # 北向资金评分
        northbound_flow = data.get('northbound_flow', 0)
        if northbound_flow > 50000000:  # 5000万
            score += 15
        elif northbound_flow > 10000000:  # 1000万
            score += 10
        elif northbound_flow > 0:
            score += 5
        
        # 融资余额评分
        margin_chg = data.get('margin_balance_chg', 0)
        if margin_chg > 0.05:  # 增长5%
            score += 15
        elif margin_chg > 0.02:  # 增长2%
            score += 10
        elif margin_chg > 0:
            score += 5
        
        return min(score, max_score)
    
    def calculate_logic_score(self, data: Dict[str, Any]) -> float:
        """计算逻辑共识分数 (0-30分)
        
        评分标准:
        - 行业热度排名前30%: +15分
        - 券商推荐>5次: +15分
        
        Args:
            data: 包含行业和券商数据的字典
            
        Returns:
            逻辑共识分数 (0-30)
        """
        score = 0.0
        max_score = 30.0
        
        # 行业热度评分
        industry_heat = data.get('industry_heat', 0)
        if industry_heat > 0.7:  # 热度>0.7
            score += 15
        elif industry_heat > 0.5:
            score += 10
        elif industry_heat > 0.3:
            score += 5
        
        # 券商评级评分
        broker_count = data.get('broker_recommend_count', 0)
        if broker_count >= 10:
            score += 15
        elif broker_count >= 5:
            score += 10
        elif broker_count > 0:
            score += 5
        
        return min(score, max_score)
    
    def calculate_sentiment_score(self, data: Dict[str, Any]) -> float:
        """计算情绪共识分数 (0-20分)
        
        评分标准:
        - 社交媒体讨论热度高: +10分
        - 市场关注度上升: +10分
        
        Args:
            data: 包含情绪数据的字典
            
        Returns:
            情绪共识分数 (0-20)
        """
        score = 0.0
        max_score = 20.0
        
        # 简化处理，实际需要爬取社交媒体数据
        # 这里基于其他指标综合判断
        
        # 如果北向资金和融资余额都在增长，认为市场关注度上升
        if data.get('northbound_flow', 0) > 0 and data.get('margin_balance_chg', 0) > 0:
            score += 10
        
        # 如果行业热度高，认为讨论热度高
        if data.get('industry_heat', 0) > 0.6:
            score += 10
        
        return min(score, max_score)
    
    def calculate_total_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """计算总共识分数
        
        Args:
            data: 包含所有维度数据的字典
            
        Returns:
            包含各维度分数和总分的字典
        """
        technical = self.calculate_technical_score(data)
        capital = self.calculate_capital_score(data)
        logic = self.calculate_logic_score(data)
        sentiment = self.calculate_sentiment_score(data)
        
        total = technical + capital + logic + sentiment
        
        return {
            "technical": technical,
            "capital": capital,
            "logic": logic,
            "sentiment": sentiment,
            "total": total,
            "max_score": 100
        }


def _load_all_consensus_data(date: str) -> List[Dict[str, Any]]:
    """加载指定日期所有股票的共识数据
    
    Args:
        date: 日期 'YYYY-MM-DD'
        
    Returns:
        共识数据列表
    """
    data_file = Path(project_root) / "data" / "consensus_data.jsonl"
    
    if not data_file.exists():
        return []
    
    records = []
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get('date') == date:
                records.append(record)
    
    return records


@mcp.tool()
def filter_by_consensus(date: str, min_consensus_score: int = 70) -> List[Dict[str, Any]]:
    """按共识分数筛选股票
    
    基于技术、资金、逻辑、情绪四个维度的综合评分筛选高共识股票。
    这些股票在多个维度同时表现良好，值得重点关注。
    
    筛选逻辑:
    1. 技术共识 (0-20分): 创新高、均线多头、MACD金叉、放量
    2. 资金共识 (0-30分): 北向资金流入、融资余额增长
    3. 逻辑共识 (0-30分): 行业热度、券商推荐
    4. 情绪共识 (0-20分): 社交媒体热度、市场关注度
    
    总分 = 技术 + 资金 + 逻辑 + 情绪 (0-100分)
    
    Args:
        date: 筛选日期，格式 'YYYY-MM-DD'
        min_consensus_score: 最小共识分数阈值 (0-100)，默认70分
        
    Returns:
        符合条件的股票列表，按分数降序排列，每个元素包含:
        - symbol: 股票代码
        - name: 股票名称（如果有）
        - consensus_score: 总共识分数
        - details: 各维度详细分数
            - technical: 技术共识分
            - capital: 资金共识分
            - logic: 逻辑共识分
            - sentiment: 情绪共识分
        
    Example:
        >>> result = filter_by_consensus("2024-01-15", 70)
        >>> print(result)
        [
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "consensus_score": 85,
                "details": {
                    "technical": 18,
                    "capital": 28,
                    "logic": 30,
                    "sentiment": 19
                }
            }
        ]
    """
    # 加载配置
    config_file = Path(project_root) / "configs" / "default_config.json"
    config = {}
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    consensus_config = config.get('consensus_filter', {})
    calculator = ConsensusScoreCalculator(consensus_config)
    
    # 加载所有共识数据
    all_data = _load_all_consensus_data(date)
    
    if not all_data:
        return {
            "date": date,
            "min_score": min_consensus_score,
            "result_count": 0,
            "stocks": [],
            "message": "未找到共识数据，请先运行 data/get_consensus_data.py 获取数据"
        }
    
    # 计算每只股票的共识分数
    scored_stocks = []
    for data in all_data:
        scores = calculator.calculate_total_score(data)
        
        if scores['total'] >= min_consensus_score:
            scored_stocks.append({
                "symbol": data['symbol'],
                "name": data.get('name', ''),
                "consensus_score": round(scores['total'], 2),
                "details": {
                    "technical": round(scores['technical'], 2),
                    "capital": round(scores['capital'], 2),
                    "logic": round(scores['logic'], 2),
                    "sentiment": round(scores['sentiment'], 2)
                }
            })
    
    # 按分数降序排列
    scored_stocks.sort(key=lambda x: x['consensus_score'], reverse=True)
    
    return {
        "date": date,
        "min_score": min_consensus_score,
        "result_count": len(scored_stocks),
        "stocks": scored_stocks[:20],  # 返回前20只
        "message": f"找到{len(scored_stocks)}只高共识股票（显示前20只）"
    }


@mcp.tool()
def get_consensus_summary(date: str) -> Dict[str, Any]:
    """获取市场共识概况
    
    统计当日市场的整体共识情况，包括高共识股票数量、平均分数等。
    
    Args:
        date: 查询日期，格式 'YYYY-MM-DD'
        
    Returns:
        市场共识概况字典:
        - date: 日期
        - total_stocks: 总股票数
        - high_consensus_count: 高共识股票数（>=70分）
        - avg_consensus_score: 平均共识分数
        - top_industries: 共识最高的前3个行业
        - market_sentiment: 市场整体情绪 (强/中/弱)
    """
    all_data = _load_all_consensus_data(date)
    
    if not all_data:
        return {
            "date": date,
            "total_stocks": 0,
            "message": "未找到共识数据"
        }
    
    calculator = ConsensusScoreCalculator()
    
    # 计算所有股票分数
    scores = []
    high_consensus = 0
    
    for data in all_data:
        score_result = calculator.calculate_total_score(data)
        scores.append(score_result['total'])
        if score_result['total'] >= 70:
            high_consensus += 1
    
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # 判断市场情绪
    if avg_score >= 60:
        sentiment = "强"
    elif avg_score >= 40:
        sentiment = "中"
    else:
        sentiment = "弱"
    
    return {
        "date": date,
        "total_stocks": len(all_data),
        "high_consensus_count": high_consensus,
        "avg_consensus_score": round(avg_score, 2),
        "market_sentiment": sentiment,
        "interpretation": f"市场共识{sentiment}，{high_consensus}只高共识股票"
    }


if __name__ == "__main__":
    port = int(os.getenv("CONSENSUS_FILTER_HTTP_PORT", "8005"))
    mcp.run(transport="streamable-http", port=port)
