"""
共识数据查询MCP工具

提供5个MCP工具函数供Agent调用,封装共识数据获取功能:
1. get_northbound_flow - 北向资金流向
2. get_margin_trading - 融资融券数据
3. get_analyst_ratings - 券商评级
4. get_industry_heat - 行业热度
5. get_all_consensus - 获取全部共识数据

作者: AI-Trader Team
日期: 2024
"""

from typing import Dict, Any, Optional
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入共识数据获取模块
try:
    from data.get_consensus_data import ConsensusDataFetcher
except ImportError:
    ConsensusDataFetcher = None
    print("Warning: ConsensusDataFetcher not available")


# TODO: 根据实际MCP框架调整装饰器
# from mcp import tool
# 当前使用模拟装饰器
def mcp_tool():
    """MCP工具装饰器(模拟)"""
    def decorator(func):
        func._is_mcp_tool = True
        return func
    return decorator


@mcp_tool()
def get_northbound_flow(symbol: str, date: str, tushare_token: Optional[str] = None) -> Dict[str, Any]:
    """
    获取北向资金流向数据(沪深股通外资数据)
    
    Args:
        symbol: 股票代码,如"600000"(不含后缀)
        date: 查询日期,格式"YYYY-MM-DD",如"2024-01-15"
        tushare_token: 废弃参数(保持兼容性)
        
    Returns:
        dict: {
            "date": str,              // 日期
            "symbol": str,            // 股票代码
            "buy_amount": float,      // 北向资金买入金额(万元),null表示数据缺失
            "sell_amount": float,     // 北向资金卖出金额(万元),null表示数据缺失
            "net_amount": float,      // 北向资金净流入(万元),正值为流入,负值为流出,null表示数据缺失
            "data_source": str,       // 数据源("akshare"或"error")
            "error": str              // 错误信息(如果有)
        }
        
    Example:
        >>> data = get_northbound_flow("600000", "2024-01-15")
        >>> if data["net_amount"] and data["net_amount"] > 0:
        ...     print(f"北向资金净流入{data['net_amount']}万元")
        
    Notes:
        - 北向资金指通过沪深股通流入A股的外资
        - 净流入>1000万通常被视为显著流入信号
        - 数据可能存在1-2天延迟
        - 数据缺失时返回null,不影响其他维度使用
    """
    if not ConsensusDataFetcher:
        return {
            "date": date,
            "symbol": symbol,
            "buy_amount": None,
            "sell_amount": None,
            "net_amount": None,
            "data_source": "error",
            "error": "ConsensusDataFetcher not available"
        }
    
    fetcher = ConsensusDataFetcher()
    return fetcher.fetch_northbound_flow(symbol, date)


@mcp_tool()
def get_margin_trading(symbol: str, date: str, tushare_token: Optional[str] = None) -> Dict[str, Any]:
    """
    获取融资融券数据
    
    Args:
        symbol: 股票代码,如"600000"
        date: 查询日期,格式"YYYY-MM-DD"
        tushare_token: Tushare Pro API Token(可选)
        
    Returns:
        dict: {
            "date": str,
            "symbol": str,
            "margin_balance": float,      // 融资余额(万元),null表示数据缺失
            "short_balance": float,       // 融券余额(万元),null表示数据缺失
            "margin_buy_amount": float,   // 融资买入额(万元),null表示数据缺失
            "data_source": str
        }
        
    Example:
        >>> data = get_margin_trading("600000", "2024-01-15")
        >>> # 计算融资余额环比(需要历史数据)
        >>> if data["margin_balance"]:
        ...     print(f"融资余额:{data['margin_balance']}万元")
        
    Notes:
        - 融资:借钱买股票,看多信号
        - 融券:借股票卖出,看空信号
        - 融资余额增长>5%通常被视为积极信号
        - 需要有融资融券资格的股票才有数据
    """
    if not ConsensusDataFetcher:
        return {
            "date": date,
            "symbol": symbol,
            "margin_balance": None,
            "short_balance": None,
            "margin_buy_amount": None,
            "data_source": "error",
            "error": "ConsensusDataFetcher not available"
        }
    
    fetcher = ConsensusDataFetcher()
    return fetcher.fetch_margin_trading(symbol, date)


@mcp_tool()
def get_analyst_ratings(symbol: str, date: str, tushare_token: Optional[str] = None) -> Dict[str, Any]:
    """
    获取券商分析师评级数据
    
    Args:
        symbol: 股票代码,如"600000"
        date: 查询日期,格式"YYYY-MM-DD"
        tushare_token: Tushare Pro API Token(可选)
        
    Returns:
        dict: {
            "date": str,
            "symbol": str,
            "rating": str,                // 最新评级("买入"/"增持"/"中性"/"减持"/"卖出"),null表示无评级
            "target_price": float,        // 目标价(元),null表示数据缺失
            "rating_change": str,         // 评级变化("上调"/"维持"/"下调"),null表示数据缺失
            "institution_count": int,     // 评级机构数量,null表示数据缺失
            "data_source": str
        }
        
    Example:
        >>> data = get_analyst_ratings("600000", "2024-01-15")
        >>> if data["rating"] == "买入" and data["rating_change"] == "上调":
        ...     print("券商上调评级至买入,积极信号")
        
    Notes:
        - 评级权重:买入(10分)>增持(5分)>中性(0分)>减持(-5分)>卖出(-10分)
        - 评级上调通常是积极信号
        - 机构数量>5家评级更有参考价值
        - 注意评级时效性,超过1个月的评级参考价值降低
    """
    if not ConsensusDataFetcher:
        return {
            "date": date,
            "symbol": symbol,
            "rating": None,
            "target_price": None,
            "rating_change": None,
            "institution_count": None,
            "data_source": "error",
            "error": "ConsensusDataFetcher not available"
        }
    
    fetcher = ConsensusDataFetcher()
    return fetcher.fetch_analyst_ratings(symbol, date)


@mcp_tool()
def get_industry_heat(industry: str, date: str, tushare_token: Optional[str] = None) -> Dict[str, Any]:
    """
    获取行业热度数据
    
    Args:
        industry: 行业名称,如"银行"、"医药"、"半导体"等
        date: 查询日期,格式"YYYY-MM-DD"
        tushare_token: Tushare Pro API Token(可选)
        
    Returns:
        dict: {
            "date": str,
            "industry": str,
            "pct_change": float,          // 行业当日涨跌幅(%),null表示数据缺失
            "net_flow": float,            // 行业资金净流入(万元),null表示数据缺失
            "heat_rank": int,             // 热度排名(1=最热),null表示数据缺失
            "data_source": str
        }
        
    Example:
        >>> data = get_industry_heat("银行", "2024-01-15")
        >>> if data["pct_change"] and data["pct_change"] > 2:
        ...     print(f"银行行业上涨{data['pct_change']}%,表现强势")
        
    Notes:
        - 行业涨幅>大盘2%通常被视为热门行业
        - 行业热度排名前10%的行业配置价值较高
        - 行业轮动是A股重要特征,关注行业趋势
        - 常见行业分类:银行、地产、医药、消费、科技、周期等
    """
    if not ConsensusDataFetcher:
        return {
            "date": date,
            "industry": industry,
            "pct_change": None,
            "net_flow": None,
            "heat_rank": None,
            "data_source": "error",
            "error": "ConsensusDataFetcher not available"
        }
    
    fetcher = ConsensusDataFetcher()
    return fetcher.fetch_industry_heat(industry, date)


@mcp_tool()
def get_all_consensus(symbol: str, date: str, industry: Optional[str] = None, 
                      tushare_token: Optional[str] = None) -> Dict[str, Any]:
    """
    获取股票的全部共识数据(一次性获取4个维度)
    
    Args:
        symbol: 股票代码,如"600000"
        date: 查询日期,格式"YYYY-MM-DD"
        industry: 行业名称(可选),如"银行"
        tushare_token: Tushare Pro API Token(可选)
        
    Returns:
        dict: {
            "symbol": str,
            "date": str,
            "northbound": dict,           // 北向资金数据(可能为null)
            "margin": dict,               // 融资融券数据(可能为null)
            "ratings": dict,              // 券商评级数据(可能为null)
            "industry": dict              // 行业热度数据(可能为null)
        }
        
    Example:
        >>> consensus = get_all_consensus("600000", "2024-01-15", industry="银行")
        >>> 
        >>> # 检查北向资金
        >>> if consensus["northbound"] and consensus["northbound"]["net_amount"]:
        ...     net = consensus["northbound"]["net_amount"]
        ...     print(f"北向资金{'流入' if net > 0 else '流出'}{abs(net)}万元")
        >>> 
        >>> # 检查券商评级
        >>> if consensus["ratings"] and consensus["ratings"]["rating"]:
        ...     print(f"券商评级:{consensus['ratings']['rating']}")
        
    Notes:
        - 这是推荐的获取共识数据方式,一次性获取所有维度
        - 各维度数据可能独立缺失,使用前需检查是否为null
        - 缺失的数据在共识分数计算时会记0分
        - 建议配合calculate_consensus_score()使用
    """
    if not ConsensusDataFetcher:
        return {
            "symbol": symbol,
            "date": date,
            "northbound": None,
            "margin": None,
            "ratings": None,
            "industry": None,
            "error": "ConsensusDataFetcher not available"
        }
    
    fetcher = ConsensusDataFetcher()
    return fetcher.fetch_all_consensus_data(symbol, date, industry)


# 工具函数列表(供MCP框架注册)
MCP_TOOLS = [
    get_northbound_flow,
    get_margin_trading,
    get_analyst_ratings,
    get_industry_heat,
    get_all_consensus
]


# 使用示例
if __name__ == "__main__":
    import json
    
    print("=" * 80)
    print("共识数据查询工具示例")
    print("=" * 80)
    
    # 示例1: 获取北向资金数据
    print("\n1. 获取北向资金数据:")
    northbound = get_northbound_flow("600000", "2024-01-15")
    print(json.dumps(northbound, indent=2, ensure_ascii=False))
    
    # 示例2: 获取融资融券数据
    print("\n2. 获取融资融券数据:")
    margin = get_margin_trading("600000", "2024-01-15")
    print(json.dumps(margin, indent=2, ensure_ascii=False))
    
    # 示例3: 获取券商评级
    print("\n3. 获取券商评级:")
    ratings = get_analyst_ratings("600000", "2024-01-15")
    print(json.dumps(ratings, indent=2, ensure_ascii=False))
    
    # 示例4: 获取行业热度
    print("\n4. 获取行业热度:")
    industry = get_industry_heat("银行", "2024-01-15")
    print(json.dumps(industry, indent=2, ensure_ascii=False))
    
    # 示例5: 获取全部共识数据(推荐)
    print("\n5. 获取全部共识数据:")
    all_consensus = get_all_consensus("600000", "2024-01-15", industry="银行")
    print(json.dumps(all_consensus, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("提示:实际使用时需要配置TUSHARE_TOKEN环境变量")
    print("=" * 80)
