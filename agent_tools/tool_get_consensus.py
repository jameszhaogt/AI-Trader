"""
A股共识数据查询MCP工具
提供北向资金、融资融券、券商评级、行业热度、技术指标等查询功能
"""

from fastmcp import FastMCP
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tools.general_tools import get_config_value

mcp = FastMCP("ConsensusTools")

def _load_consensus_data(symbol: str, date: str) -> Optional[Dict[str, Any]]:
    """从consensus_data.jsonl加载指定股票和日期的共识数据
    
    Args:
        symbol: 股票代码
        date: 日期 'YYYY-MM-DD'
        
    Returns:
        共识数据字典或None
    """
    data_file = Path(project_root) / "data" / "consensus_data.jsonl"
    
    if not data_file.exists():
        return None
    
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get('symbol') == symbol and record.get('date') == date:
                return record
    
    return None


@mcp.tool()
def get_northbound_flow(symbol: str, date: str) -> Dict[str, Any]:
    """获取北向资金流向
    
    查询指定股票在指定日期的北向资金（沪股通+深股通）流入流出情况。
    北向资金是外资通过沪深港通买卖A股的资金，被视为"聪明钱"的重要指标。
    
    Args:
        symbol: 股票代码，如 '600519.SH'
        date: 查询日期，格式 'YYYY-MM-DD'
        
    Returns:
        Dict包含:
        - symbol: 股票代码
        - date: 日期
        - net_buy: 净买入额（元），正数表示流入，负数表示流出
        - rank: 当日北向资金净买入排名（如果有）
        - status: 数据状态 ('success' 或 'no_data')
        
    Example:
        >>> result = get_northbound_flow("600519.SH", "2024-01-15")
        >>> print(result)
        {
            "symbol": "600519.SH",
            "date": "2024-01-15",
            "net_buy": 120000000,
            "rank": 5,
            "status": "success"
        }
    """
    data = _load_consensus_data(symbol, date)
    
    if data is None:
        return {
            "symbol": symbol,
            "date": date,
            "net_buy": 0,
            "rank": None,
            "status": "no_data",
            "message": "未找到共识数据，请先运行 data/get_consensus_data.py 获取数据"
        }
    
    net_buy = data.get('northbound_flow', 0)
    
    return {
        "symbol": symbol,
        "date": date,
        "net_buy": net_buy,
        "rank": data.get('northbound_rank'),
        "status": "success",
        "interpretation": "北向资金流入" if net_buy > 0 else "北向资金流出" if net_buy < 0 else "北向资金无变化"
    }


@mcp.tool()
def get_margin_info(symbol: str, date: str) -> Dict[str, Any]:
    """获取融资融券信息
    
    查询指定股票的融资融券数据，包括融资余额及其变化。
    融资余额增加表示看多情绪上升，减少表示看多情绪下降。
    
    Args:
        symbol: 股票代码，如 '600519.SH'
        date: 查询日期，格式 'YYYY-MM-DD'
        
    Returns:
        Dict包含:
        - symbol: 股票代码
        - date: 日期
        - margin_balance: 融资余额（元）
        - chg_rate: 融资余额变化率（相比前一日）
        - margin_buy: 融资买入额（元）
        - status: 数据状态
        
    Example:
        >>> result = get_margin_info("600519.SH", "2024-01-15")
        >>> print(result)
        {
            "symbol": "600519.SH",
            "date": "2024-01-15",
            "margin_balance": 5000000000,
            "chg_rate": 0.05,
            "status": "success"
        }
    """
    data = _load_consensus_data(symbol, date)
    
    if data is None:
        return {
            "symbol": symbol,
            "date": date,
            "margin_balance": 0,
            "chg_rate": 0,
            "status": "no_data",
            "message": "未找到共识数据"
        }
    
    margin_balance = data.get('margin_balance', 0)
    chg_rate = data.get('margin_balance_chg', 0)
    
    return {
        "symbol": symbol,
        "date": date,
        "margin_balance": margin_balance,
        "chg_rate": chg_rate,
        "status": "success",
        "interpretation": "融资做多意愿增强" if chg_rate > 0.03 else "融资做多意愿减弱" if chg_rate < -0.03 else "融资情绪稳定"
    }


@mcp.tool()
def get_broker_ratings(symbol: str, days: int = 30) -> Dict[str, Any]:
    """获取券商评级汇总
    
    统计最近N天内各券商对该股票的评级情况。
    券商评级是专业机构的研究结论，多家券商一致看好具有参考价值。
    
    Args:
        symbol: 股票代码，如 '600519.SH'
        days: 统计最近多少天的评级，默认30天
        
    Returns:
        Dict包含:
        - symbol: 股票代码
        - period: 统计周期（天）
        - buy_count: "买入"评级次数
        - hold_count: "持有"评级次数
        - sell_count: "卖出"评级次数
        - total_count: 总评级次数
        - avg_target_price: 平均目标价（如果有）
        - status: 数据状态
        
    Example:
        >>> result = get_broker_ratings("600519.SH", 30)
        >>> print(result)
        {
            "symbol": "600519.SH",
            "period": 30,
            "buy_count": 12,
            "hold_count": 3,
            "sell_count": 0,
            "total_count": 15,
            "status": "success"
        }
    """
    # 由于券商评级数据需要单独查询，这里返回模拟数据结构
    # 实际使用时需要从 consensus_data.jsonl 或 Tushare 获取
    
    today_date = get_config_value("TODAY_DATE")
    data = _load_consensus_data(symbol, today_date)
    
    if data is None:
        return {
            "symbol": symbol,
            "period": days,
            "buy_count": 0,
            "hold_count": 0,
            "sell_count": 0,
            "total_count": 0,
            "status": "no_data",
            "message": "未找到券商评级数据"
        }
    
    recommend_count = data.get('broker_recommend_count', 0)
    
    return {
        "symbol": symbol,
        "period": days,
        "buy_count": recommend_count,
        "hold_count": 0,
        "sell_count": 0,
        "total_count": recommend_count,
        "status": "success",
        "interpretation": "券商强烈看好" if recommend_count >= 10 else "券商较为看好" if recommend_count >= 5 else "券商关注度一般"
    }


@mcp.tool()
def get_industry_heat(symbol: str, date: str) -> Dict[str, Any]:
    """获取所属行业热度
    
    查询该股票所属行业在当日的市场热度。
    行业热度高时，板块内个股更容易获得资金关注和上涨机会。
    
    Args:
        symbol: 股票代码，如 '600519.SH'
        date: 查询日期，格式 'YYYY-MM-DD'
        
    Returns:
        Dict包含:
        - symbol: 股票代码
        - date: 日期
        - industry: 所属行业名称
        - heat_score: 行业热度分数 (0-1)
        - rank: 行业热度排名
        - status: 数据状态
        
    Example:
        >>> result = get_industry_heat("600519.SH", "2024-01-15")
        >>> print(result)
        {
            "symbol": "600519.SH",
            "date": "2024-01-15",
            "industry": "白酒",
            "heat_score": 0.85,
            "rank": 3,
            "status": "success"
        }
    """
    # 加载行业映射
    mapping_file = Path(project_root) / "data" / "industry_mapping.json"
    industry_name = "未知"
    
    if mapping_file.exists():
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
            # 简化：从行业映射中查找股票所属行业
            for ind_name, ind_data in mapping.get('industries', {}).items():
                for sub_ind, stocks in ind_data.get('representative_stocks', {}).items():
                    if symbol in stocks:
                        industry_name = sub_ind
                        break
    
    data = _load_consensus_data(symbol, date)
    
    if data is None:
        return {
            "symbol": symbol,
            "date": date,
            "industry": industry_name,
            "heat_score": 0,
            "rank": None,
            "status": "no_data"
        }
    
    heat_score = data.get('industry_heat', 0)
    
    return {
        "symbol": symbol,
        "date": date,
        "industry": industry_name,
        "heat_score": heat_score,
        "rank": data.get('industry_rank'),
        "status": "success",
        "interpretation": "行业处于热点" if heat_score > 0.7 else "行业热度一般" if heat_score > 0.3 else "行业较为冷门"
    }


@mcp.tool()
def get_technical_consensus(symbol: str, date: str) -> Dict[str, Any]:
    """获取技术指标共识状态
    
    分析股票的技术指标状态，包括是否创新高、均线排列等。
    多个技术指标同时向好表示技术面共识强。
    
    Args:
        symbol: 股票代码，如 '600519.SH'
        date: 查询日期，格式 'YYYY-MM-DD'
        
    Returns:
        Dict包含:
        - symbol: 股票代码
        - date: 日期
        - year_high: 是否创年内新高
        - ma_golden_cross: 是否均线金叉
        - macd_positive: MACD是否多头
        - volume_surge: 是否放量
        - technical_score: 技术面综合得分 (0-100)
        - status: 数据状态
        
    Example:
        >>> result = get_technical_consensus("600519.SH", "2024-01-15")
        >>> print(result)
        {
            "symbol": "600519.SH",
            "date": "2024-01-15",
            "year_high": True,
            "ma_golden_cross": True,
            "technical_score": 85,
            "status": "success"
        }
    """
    # 技术指标需要基于历史价格计算
    # 这里返回基本结构，实际需要从price数据计算
    
    return {
        "symbol": symbol,
        "date": date,
        "year_high": False,
        "ma_golden_cross": False,
        "macd_positive": False,
        "volume_surge": False,
        "technical_score": 50,
        "status": "pending",
        "message": "技术指标计算功能待实现，需要基于历史价格数据计算MA、MACD等指标"
    }


if __name__ == "__main__":
    port = int(os.getenv("CONSENSUS_HTTP_PORT", "8004"))
    mcp.run(transport="streamable-http", port=port)
