import os
from dotenv import load_dotenv
load_dotenv()
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import sys
import os
# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from tools.price_tools import get_yesterday_date, get_open_prices, get_yesterday_open_and_close_price, get_today_init_position, get_yesterday_profit
from tools.general_tools import get_config_value

# NASDAQ 100股票池
all_nasdaq_100_symbols = [
    "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO", "TSLA",
    "NFLX", "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN", "TMUS", "MU", "LIN",
    "PEP", "SHOP", "APP", "INTU", "AMAT", "LRCX", "PDD", "QCOM", "ARM", "INTC",
    "BKNG", "AMGN", "TXN", "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON",
    "CRWD", "CEG", "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX",
    "CDNS", "ORLY", "SNPS", "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI",
    "MAR", "MNST", "CSX", "ADSK", "PYPL", "FTNT", "AEP", "WDAY", "REGN", "ROP",
    "NXPI", "DDOG", "AXON", "ROST", "IDXX", "EA", "PCAR", "FAST", "EXC", "TTWO",
    "XEL", "ZS", "PAYX", "WBD", "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR",
    "KDP", "MCHP", "GEHC", "VRSK", "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD",
    "ON", "BIIB", "LULU", "CDW", "GFS"
]

# A股股票池（自定义示例）
all_astock_symbols = [
    "600519.SH", "000858.SZ", "601318.SH", "600036.SH", "000333.SZ",
    "600276.SH", "002594.SZ", "603288.SH", "600309.SH", "000651.SZ"
]

def load_stock_pool(market: str = "nasdaq") -> List[str]:
    """根据市场类型加载股票池
    
    Args:
        market: 市场类型 (nasdaq/a_stock)
        
    Returns:
        股票代码列表
    """
    if market == "a_stock":
        # 尝试从配置文件加载
        config_file = Path(project_root) / "configs" / "default_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                stock_pool = config.get("stock_pool", "custom")
                custom_stocks = config.get("custom_stocks", [])
                
                if stock_pool == "custom" and custom_stocks:
                    return custom_stocks
        
        # 默认返回示例A股池
        return all_astock_symbols
    else:
        return all_nasdaq_100_symbols

STOP_SIGNAL = "<FINISH_SIGNAL>"

# NASDAQ市场提示词
agent_system_prompt_nasdaq = """
You are a stock fundamental analysis trading assistant.

Your goals are:
- Think and reason by calling available tools.
- You need to think about the prices of various stocks and their returns.
- Your long-term goal is to maximize returns through this portfolio.
- Before making decisions, gather as much information as possible through search tools to aid decision-making.

Thinking standards:
- Clearly show key intermediate steps:
  - Read input of yesterday's positions and today's prices
  - Update valuation and adjust weights for each target (if strategy requires)

Notes:
- You don't need to request user permission during operations, you can execute directly
- You must execute operations by calling tools, directly output operations will not be accepted

Here is the information you need:

Current time:
{date}

Your current positions (numbers after stock codes represent how many shares you hold, numbers after CASH represent your available cash):
{positions}

The current value represented by the stocks you hold:
{yesterday_close_price}

Current buying prices:
{today_buy_price}

When you think your task is complete, output
{STOP_SIGNAL}
"""

# A股市场提示词
agent_system_prompt_astock = """
你是一个A股市场基本面分析交易助手。

你的目标：
- 通过调用可用工具进行思考和推理
- 分析各只股票的价格和收益表现
- 长期目标是通过此投资组合最大化收益
- 在做决策前，通过搜索工具收集尽可能多的信息

思考标准：
- 清晰展示关键中间步骤：
  - 读取昨日持仓和今日价格信息
  - 更新估值并调整每个目标的权重（如果策略需要）

重要规则与约束：

1. A股交易制度：
   - T+1规则：当日买入的股票，次日才能卖出
   - 交易时间：上午09:30-11:30，下午13:00-15:00（北京时间）

2. 涨跌幅限制：
   - 主板股票：±10%
   - 科创板/创业板：±20%
   - ST股票：±5%
   - 涨停时禁止买入，跌停时禁止卖出

3. 交易单位：
   - 买入：必须是100股的整数倍（1手=100股）
   - 卖出：允许零股交易

4. 停牌规则：
   - 停牌股票无法交易
   - 交易前请检查股票状态

选股策略指引（多维共识方法）：

你应该优先关注满足"多维共识"的股票，这些股票在多个维度同时表现良好：

1. 技术共识（权重20%）：
   - 股价创年内新高，突破关键压力位
   - 均线呈多头排列（短期均线在长期均线上方）
   - MACD指标金叉，技术面转强
   - 成交量放大，资金活跃
   
2. 资金共识（权重30%）：
   - 北向资金（沪深股通）大幅流入，单日流入>5000万元
   - 融资余额持续增长，增幅>5%
   - 主力资金净流入
   【可用工具】get_northbound_flow(), get_margin_info()
   
3. 逻辑共识（权重30%）：
   - 所属行业为当前市场热点（行业指数涨幅前30%）
   - 近30天有5家以上券商发布"买入"评级
   - 行业政策利好，基本面向好
   【可用工具】get_industry_heat(), get_broker_ratings()
   
4. 情绪共识（权重20%）：
   - 社交媒体讨论热度高
   - 市场关注度上升
   - 散户参与度提升

【推荐使用共识筛选工具】：
- filter_by_consensus(date, min_score=70): 筛选高共识股票（总分≥70分）
- get_consensus_summary(date): 查看市场整体共识情况
- 从筛选结果中优先选择共识分数最高的股票进行配置

风险提示：
- 避免追高涨停股，避免接盘跌停股
- 注意ST股票风险，建议规避
- 分散投资，单只股票持仓不超过总资产30%
- 关注公司基本面变化、行业政策动向
- 即使是高共识股票也要设置止损，控制单笔亏损不超过5%

注意事项：
- 操作过程中不需要请求用户权限，可以直接执行
- 必须通过调用工具执行操作，直接输出操作将不被接受
- 所有交易已自动校验A股规则，请注意工具返回的错误提示

以下是你需要的信息：

当前时间：
{date}

你当前的持仓（股票代码后的数字代表你持有的股数，CASH后的数字代表可用现金）：
{positions}

你持有股票的当前价值（昨日收盘价）：
{yesterday_close_price}

当前买入价格（今日开盘价）：
{today_buy_price}

{consensus_info}

当你认为任务完成时，输出
{STOP_SIGNAL}
"""

def get_agent_system_prompt(today_date: str, signature: str) -> str:
    print(f"signature: {signature}")
    print(f"today_date: {today_date}")
    
    # 获取市场类型
    market = get_config_value("MARKET") or "nasdaq"
    
    # 根据市场类型加载股票池
    stock_symbols = load_stock_pool(market)
    
    # Get yesterday's buy and sell prices
    yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(today_date, stock_symbols)
    today_buy_price = get_open_prices(today_date, stock_symbols)
    today_init_position = get_today_init_position(today_date, signature)
    
    # 选择提示词模板
    if market == "a_stock":
        prompt_template = agent_system_prompt_astock
        # 生成共识信息
        consensus_info = get_consensus_prompt(today_date)
    else:
        prompt_template = agent_system_prompt_nasdaq
        consensus_info = ""
    
    return prompt_template.format(
        date=today_date, 
        positions=today_init_position, 
        STOP_SIGNAL=STOP_SIGNAL,
        yesterday_close_price=yesterday_sell_prices,
        today_buy_price=today_buy_price,
        consensus_info=consensus_info
    )


def get_consensus_prompt(date: str) -> str:
    """动态生成市场共识信息
    
    Args:
        date: 日期 'YYYY-MM-DD'
        
    Returns:
        共识信息提示词
    """
    # 尝试加载共识数据
    consensus_file = Path(project_root) / "data" / "consensus_data.jsonl"
    
    if not consensus_file.exists():
        return """
【市场共识信息】
当前未加载共识数据。
建议：使用 filter_by_consensus() 工具筛选高共识股票。
"""
    
    # 统计市场共识概况
    try:
        total_stocks = 0
        high_consensus_stocks = []
        
        with open(consensus_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get('date') == date:
                    total_stocks += 1
                    # 简单判断：北向资金+融资余额都增长
                    if (record.get('northbound_flow', 0) > 10000000 and 
                        record.get('margin_balance_chg', 0) > 0.02):
                        high_consensus_stocks.append({
                            'symbol': record['symbol'],
                            'northbound': record.get('northbound_flow', 0),
                            'margin_chg': record.get('margin_balance_chg', 0)
                        })
        
        # 按北向资金流入排序
        high_consensus_stocks.sort(key=lambda x: x['northbound'], reverse=True)
        
        if high_consensus_stocks:
            top_stocks = high_consensus_stocks[:5]
            stock_list = "\n".join([
                f"   - {s['symbol']}: 北向资金{s['northbound']/100000000:.2f}亿, 融资余额增{s['margin_chg']*100:.1f}%" 
                for s in top_stocks
            ])
            
            return f"""
【市场共识信息】
今日市场概况：
- 总股票数：{total_stocks}
- 高共识股票：{len(high_consensus_stocks)}只（北向资金流入>1000万 且 融资余额增长>2%）

重点关注股票：
{stock_list}

建议：优先从上述高共识股票中选择，结合基本面分析后决策。
"""
        else:
            return """
【市场共识信息】
今日市场整体共识较弱，高共识股票数量较少。
建议：谨慎操作，等待明确机会。
"""
            
    except Exception as e:
        print(f"生成共识提示失败: {e}")
        return ""



if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(get_agent_system_prompt(today_date, signature))  