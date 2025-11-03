"""
A股市场适配 - Agent Prompt增强

在原有prompt基础上增加A股市场特定的规则说明和注意事项。

作者: AI-Trader Team
日期: 2024
"""

# A股市场规则说明(追加到原有agent_prompt.py)

ASTOCK_MARKET_RULES = """
## A股市场特殊规则

### 1. T+1交易制度
- 当日买入的股票,需等到下一交易日才能卖出
- 当日卖出股票获得的资金当日可用于买入,但需次日才可提现
- 违反T+1规则的交易将被系统拒绝

### 2. 涨跌停限制
- **主板股票(60XXXX, 00XXXX)**:涨跌幅限制±10%
- **科创板(688XXX)**:涨跌幅限制±20%,上市前5日不设涨跌幅限制
- **创业板(300XXX)**:涨跌幅限制±20%
- **ST股票(ST/\*ST/SST开头)**:涨跌幅限制±5%
- **涨跌停价格精确到分**:使用round(前收盘价 × 涨跌幅比例, 2)

**重要注意事项**:
- 禁止在涨停价买入股票(封单难以成交,浪费资金)
- 禁止在跌停价卖出股票(无法成交,可能扩大损失)

### 3. 交易单位
- 最小交易单位:100股(1手)
- 买卖数量必须是100股的整数倍
- 卖出时允许不足100股的零股一次性卖出

### 4. ST股票识别
- ST(Special Treatment):财务异常或其他异常情况
- \*ST:有退市风险
- SST:未完成股改的ST股票
- 判断方法:通过股票名称前缀识别,或查询is_st字段
- ST股票风险较高,建议谨慎投资

### 5. 停牌处理
- 停牌股票无法交易,status字段标记为"suspended"
- 停牌日行情数据使用前收盘价填充
- 交易前需检查股票是否停牌

### 6. 交易时间
- 开盘集合竞价:9:15-9:25
- 上午交易:9:30-11:30
- 下午交易:13:00-15:00
- 收盘集合竞价:14:57-15:00(仅深交所)
- 回测系统以收盘价为成交价

### 7. 交易成本
- 佣金:约0.03%(双向收取,最低5元)
- 印花税:0.1%(仅卖出时收取)
- 过户费:0.001%(双向收取,仅沪市)
- 滑点:约0.1%(市价单冲击成本)

### 8. 共识数据说明
- **北向资金**:沪深股通外资流向,正值为净流入
- **融资融券**:杠杆资金,余额增长表明看好
- **券商评级**:买入>增持>中性>减持>卖出
- **行业热度**:相对大盘的超额收益
- **数据缺失处理**:缺失维度记0分,不影响其他维度

### 9. 风险控制建议
- 单只股票持仓比例不超过30%
- 保留10%现金应对突发情况
- 止损线:-8%~-10%
- 止盈线:+20%~+25%
- 最大回撤控制在15%以内

### 10. 回测注意事项
- 严禁使用未来数据(时间旅行检测)
- 所有交易必须通过合规检查
- 停牌日无法交易,跳过该日
- 考虑滑点和手续费,避免高频交易
"""

ASTOCK_TOOL_USAGE_GUIDE = """
## A股市场专用工具

### 1. get_price_astock(symbol, date)
获取A股价格数据,返回完整的行情信息,包含:
- 基础行情:open, high, low, close, volume
- 涨跌停信息:is_limit_up, is_limit_down, limit_up_price, limit_down_price
- ST标记:is_st
- 停牌状态:status("normal"/"suspended")
- 前收盘价:prev_close

**使用示例**:
```python
price_data = get_price_astock("600000", "2024-01-15")
if price_data["status"] == "suspended":
    print("股票停牌,无法交易")
elif price_data["is_limit_up"]:
    print("涨停,不建议买入")
```

### 2. validate_astock_trade(symbol, action, quantity, price, date, ...)
校验A股交易规则,返回校验结果:
- T+1规则检查
- 涨跌停限制检查
- 最小交易单位检查
- 停牌状态检查

**使用示例**:
```python
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
if not result["valid"]:
    print(f"交易不合规:{result['error']}")
```

### 3. get_consensus_data(symbol, date)
获取股票共识数据,包含:
- northbound:北向资金数据
- margin:融资融券数据
- ratings:券商评级数据
- industry:行业热度数据

**注意**:数据可能缺失,缺失字段为null

### 4. calculate_consensus_score(symbol, date, price_data, consensus_data)
计算4维度共识分数:
- technical:技术面(20分)
- capital:资金面(30分)
- logic:逻辑面(30分)
- sentiment:情绪面(20分)
- total_score:总分(100分)

**筛选建议**:
- 稳健策略:总分≥70分
- 进取策略:总分≥65分
- 数据完整度≥50%

### 5. filter_stocks_by_consensus(stocks_data, min_score, min_completeness)
根据共识分数筛选股票,返回按总分降序排序的列表

### 6. BacktestEngine.run_backtest(strategy_func)
运行回测,自动进行:
- 时间旅行检测
- 交易合规检查
- 持仓管理
- 绩效计算

**策略函数签名**:
```python
def my_strategy(engine, date_str) -> List[dict]:
    # 返回交易信号列表
    return [
        {"symbol": "600000", "action": "buy", "quantity": 100, "price": 10.50}
    ]
```
"""

ASTOCK_STRATEGY_EXAMPLES = """
## A股策略示例

### 示例1:共识驱动策略
```python
def consensus_driven_strategy(engine, date_str):
    signals = []
    
    # 获取候选股票池
    candidates = engine.get_stock_pool()
    
    for symbol in candidates:
        # 获取价格数据
        price_data = engine.get_price(symbol, date_str)
        if not price_data or price_data["status"] == "suspended":
            continue
        
        # 获取共识数据
        consensus_data = engine.get_consensus(symbol, date_str)
        if not consensus_data:
            continue
        
        # 计算共识分数
        score = calculate_consensus_score(symbol, date_str, price_data, consensus_data)
        
        # 买入信号:总分≥75,且技术面+资金面均良好
        if (score["total_score"] >= 75 and 
            score["technical"]["score"] >= 12 and
            score["capital"]["score"] >= 18 and
            not price_data["is_limit_up"]):
            
            signals.append({
                "symbol": symbol,
                "action": "buy",
                "quantity": 100,
                "price": price_data["close"]
            })
        
        # 卖出信号:总分<50,或止损
        if (score["total_score"] < 50 or 
            (price_data["close"] / engine.positions[symbol].avg_cost - 1) < -0.08):
            
            signals.append({
                "symbol": symbol,
                "action": "sell",
                "quantity": engine.positions[symbol].quantity,
                "price": price_data["close"]
            })
    
    return signals
```

### 示例2:ST股票规避策略
```python
def avoid_st_strategy(engine, date_str):
    signals = []
    
    for symbol in engine.get_stock_pool():
        stock_info = engine.get_stock_info(symbol)
        
        # 规避ST股票
        if stock_info and stock_info.get("is_st", False):
            # 如果持有ST股票,立即卖出
            if symbol in engine.positions:
                signals.append({
                    "symbol": symbol,
                    "action": "sell",
                    "quantity": engine.positions[symbol].quantity,
                    "price": engine.get_price(symbol, date_str)["close"]
                })
            continue  # 不买入ST股票
        
        # ... 其他策略逻辑
    
    return signals
```

### 示例3:涨跌停应对策略
```python
def limit_price_aware_strategy(engine, date_str):
    signals = []
    
    for symbol in engine.get_stock_pool():
        price_data = engine.get_price(symbol, date_str)
        
        if not price_data:
            continue
        
        # 涨停:不买入
        if price_data["is_limit_up"]:
            continue
        
        # 跌停:不卖出(等待反弹)
        if price_data["is_limit_down"] and symbol in engine.positions:
            continue  # 保留持仓
        
        # 接近涨停(涨幅>8%):考虑止盈
        pct_change = (price_data["close"] / price_data["prev_close"] - 1) * 100
        if pct_change > 8 and symbol in engine.positions:
            signals.append({
                "symbol": symbol,
                "action": "sell",
                "quantity": engine.positions[symbol].quantity,
                "price": price_data["close"]
            })
        
        # ... 其他策略逻辑
    
    return signals
```
"""

# 完整的A股市场Prompt(追加到原agent_prompt.py)
ASTOCK_ENHANCED_PROMPT = f"""
{ASTOCK_MARKET_RULES}

{ASTOCK_TOOL_USAGE_GUIDE}

{ASTOCK_STRATEGY_EXAMPLES}

---
**重要提醒**:
1. 所有交易必须遵守A股市场规则,系统会自动校验
2. 时间旅行检测已启用,禁止访问未来数据
3. 数据缺失时记0分,不要因数据不完整而放弃策略
4. 涨跌停价格精确到分,避免浮点数误差
5. ST股票风险高,建议规避或设置更严格止损
6. 回测时考虑交易成本,避免过度交易
7. 保持足够的现金储备,应对突发情况
"""


def get_astock_agent_prompt(base_prompt: str = "") -> str:
    """
    获取A股市场增强版Agent Prompt
    
    Args:
        base_prompt: 原始基础prompt
        
    Returns:
        str: 增强后的prompt
    """
    return base_prompt + "\n\n" + ASTOCK_ENHANCED_PROMPT


# 示例用法
if __name__ == "__main__":
    # 假设有原始prompt
    base_prompt = """
    You are an AI trading agent. Your goal is to maximize returns while managing risk.
    You have access to various tools to analyze markets and execute trades.
    """
    
    # 获取A股增强prompt
    enhanced_prompt = get_astock_agent_prompt(base_prompt)
    
    print("=" * 80)
    print("A股市场增强版Agent Prompt")
    print("=" * 80)
    print(enhanced_prompt)
    print("\n提示:将此prompt与原agent_prompt.py合并使用")
