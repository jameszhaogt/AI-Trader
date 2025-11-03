# A股市场适配实施路线图

## 文档概述

本文档提供A股市场适配的完整实施路线图,包括详细的任务清单、依赖关系、验收标准和时间估算。

---

## 总体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    A股市场适配系统                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  数据层      │  │  工具层      │  │  回测层      │     │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤     │
│  │ Tushare API │  │ MCP Tools    │  │ Backtest     │     │
│  │ AkShare备用 │  │ 交易规则校验  │  │ Engine       │     │
│  │ 数据清洗    │  │ 共识筛选     │  │ 时间旅行     │     │
│  │ 停牌处理    │  │ 价格查询     │  │ 绩效分析     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │             │
│         └────────┬────────┴────────┬────────┘             │
│                  │                 │                      │
│         ┌────────▼─────────────────▼────────┐             │
│         │      Agent决策引擎                │             │
│         │  (基于LLM的智能交易决策)           │             │
│         └─────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

---

## 实施阶段划分

### 阶段概览

| 阶段 | 名称 | 核心任务 | 预计耗时 | 依赖 |
|------|------|---------|---------|------|
| 阶段0 | 前置准备 | 修复设计缺陷,环境配置 | 0.5天 | 无 |
| 阶段1 | 基础适配 | 数据源接入,交易规则实现 | 3天 | 阶段0 |
| 阶段2 | 共识系统 | 多维共识数据获取与筛选 | 2天 | 阶段1 |
| 阶段3 | 回测系统 | 历史回测与绩效分析 | 2天 | 阶段1+2 |
| 阶段4 | 测试优化 | 全面测试与性能优化 | 2天 | 阶段1+2+3 |

**总计**: 9.5个工作日

---

## 阶段0: 前置准备 (0.5天)

### 任务清单

- [x] **任务0.1**: 审核设计缺陷修复文档
  - 文件: `docs/DESIGN_DEFECTS_FIX.md`
  - 验收: 开发团队确认所有修复点已理解
  
- [x] **任务0.2**: 确认.gitignore配置
  - 文件: `.gitignore`
  - 验收: 确认包含`.env`规则
  
- [ ] **任务0.3**: 创建.env.example文件
  - 文件: `.env.example`
  - 内容: Tushare Token, OpenAI Key等示例配置
  - 验收: 文件存在且格式正确

### 环境准备

```bash
# 1. 安装新增依赖
pip install tushare akshare pandas numpy

# 2. 配置环境变量
cp .env.example .env
# 编辑.env文件,填入真实Token

# 3. 验证API连接
python -c "import tushare as ts; pro = ts.pro_api()"
```

### 验收标准

- [ ] 设计缺陷修复文档已审核完成
- [ ] .env.example文件已创建
- [ ] Tushare API连接测试通过
- [ ] Git配置正确(.env不被追踪)

---

## 阶段1: 基础适配 - 数据源与交易规则 (3天)

### 依赖关系图

```
任务1.1 (get_astock_data.py)
   │
   ├──► 任务1.2 (tool_get_price_local.py)
   │       │
   │       └──► 任务1.3 (tool_trade.py)
   │               │
   │               └──► 任务1.4 (agent_prompt.py)
   │                       │
   └───────────────────────┴──► 任务1.5 (default_config.json)
                                   │
                                   └──► 任务1.6 (阶段测试)
```

### 第1天: 数据层开发

#### 任务1.1: 创建 data/get_astock_data.py

**功能需求**:
1. 获取A股股票列表(沪深300 + 科创50)
2. 下载历史日线数据(支持日期范围)
3. 复权处理(前复权)
4. 停牌日处理(使用前收盘价填充)
5. 数据质量校验(价格异常检测)
6. ST股票识别(通过股票名称)

**核心函数设计**:

```python
# 1. 股票列表获取
def fetch_stock_list(
    market: str = "HS300",  # HS300, KC50, ALL
    update: bool = True
) -> dict:
    """
    获取股票列表
    
    Returns:
        {
            "update_time": "2024-01-15 15:00:00",
            "total_count": 300,
            "stocks": [
                {
                    "symbol": "600519.SH",
                    "name": "贵州茅台",
                    "industry": "白酒",
                    "market": "主板",
                    "list_date": "2001-08-27",
                    "is_st": False,
                    "status": "normal"
                }
            ]
        }
    """
    pass


# 2. 历史数据下载
def fetch_daily_data(
    symbol: str,
    start_date: str,
    end_date: str,
    adj: str = "qfq"  # 前复权
) -> list:
    """
    下载历史日线数据并处理停牌日
    
    Returns:
        [
            {
                "symbol": "600519.SH",
                "date": "2024-01-15",
                "open": 1860.00,
                "close": 1880.00,
                "high": 1890.00,
                "low": 1855.00,
                "volume": 12345678,
                "amount": 231234567.89,
                "prev_close": 1850.00,
                "change_pct": 1.62,
                "status": "normal",  # normal, suspended, limit_up, limit_down
                "suspend_reason": None
            }
        ]
    """
    pass


# 3. ST股票识别
def identify_st_stock(stock_name: str) -> bool:
    """
    判断是否为ST股票
    
    识别规则:
    - ST开头 -> True
    - *ST开头 -> True
    - SST开头 -> True
    - 其他 -> False
    """
    name = stock_name.strip()
    st_prefixes = ["ST", "*ST", "SST", "S*ST"]
    return any(name.startswith(prefix) for prefix in st_prefixes)


# 4. 数据质量校验
def validate_data_quality(data: list) -> dict:
    """
    校验数据质量
    
    校验项:
    - 价格连续性(涨跌幅<50%)
    - 成交量合理性(volume>0)
    - 数据完整性(OHLCV字段非空)
    - 时间序列连续性(无未来日期)
    
    Returns:
        {
            "valid": True/False,
            "warnings": ["2024-01-15: 涨跌幅异常50.5%"],
            "errors": []
        }
    """
    pass


# 5. 批量下载
def download_all_stocks(
    stock_pool: str = "HS300",
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31"
) -> None:
    """
    批量下载所有股票数据
    
    存储格式:
    - data/astock_list.json - 股票列表
    - data/merged.jsonl - 行情数据(追加模式)
    """
    pass
```

**实现要点**:
- 使用Tushare Pro API作为主数据源
- 增加重试机制(最多3次)
- API调用频率控制(120次/分钟)
- 停牌日通过`pro.suspend_d()`查询
- 数据写入使用追加模式(避免覆盖)

**测试验证**:
```bash
# 测试股票列表获取
python data/get_astock_data.py --action list --market HS300

# 测试单股下载
python data/get_astock_data.py --action download --symbol 600519.SH --start 2024-01-01 --end 2024-01-31

# 测试批量下载(10只股票)
python data/get_astock_data.py --action batch --limit 10
```

**预计耗时**: 4小时

---

### 第2天: MCP工具层开发 (上午)

#### 任务1.2: 修改 agent_tools/tool_get_price_local.py

**新增功能**:
1. 股票代码验证(检查是否在astock_list.json中)
2. 停牌状态检测(读取status字段)
3. 涨跌停判断(根据板块和ST标记)
4. ST股票识别(读取is_st字段)

**修改内容**:

```python
# 新增: 股票代码验证
def validate_stock_symbol(symbol: str) -> dict:
    """
    验证股票代码是否有效
    
    Returns:
        {
            "valid": True/False,
            "stock_info": {...} or None,
            "reason": "股票代码无效"
        }
    """
    with open("data/astock_list.json", "r") as f:
        stock_list = json.load(f)
    
    for stock in stock_list["stocks"]:
        if stock["symbol"] == symbol:
            return {
                "valid": True,
                "stock_info": stock,
                "reason": ""
            }
    
    return {
        "valid": False,
        "stock_info": None,
        "reason": f"股票代码 {symbol} 不存在"
    }


# 修改: 增加状态返回
def get_price_with_status(symbol: str, date: str) -> dict:
    """
    获取价格并返回涨跌停状态
    
    Returns:
        {
            "symbol": "600519.SH",
            "date": "2024-01-15",
            "open": 1860.00,
            "close": 1880.00,
            "high": 1890.00,
            "low": 1855.00,
            "volume": 12345678,
            "prev_close": 1850.00,
            "status": "normal",  # normal, limit_up, limit_down, suspended
            "limit_prices": {
                "limit_up": 2035.00,
                "limit_down": 1665.00
            },
            "is_st": False
        }
    """
    # 1. 验证股票代码
    validation = validate_stock_symbol(symbol)
    if not validation["valid"]:
        raise ValueError(validation["reason"])
    
    stock_info = validation["stock_info"]
    is_st = stock_info["is_st"]
    
    # 2. 读取价格数据
    data = read_price_from_jsonl(symbol, date)
    
    if not data:
        raise ValueError(f"无法获取 {symbol} 在 {date} 的价格数据")
    
    # 3. 计算涨跌停价格
    from agent_tools.tool_trade import calculate_limit_prices
    limits = calculate_limit_prices(symbol, data["prev_close"], is_st)
    
    # 4. 返回完整信息
    return {
        **data,
        "limit_prices": limits,
        "is_st": is_st
    }
```

**测试验证**:
```python
# 测试正常股票
result = get_price_with_status("600519.SH", "2024-01-15")
assert result["status"] in ["normal", "limit_up", "limit_down", "suspended"]

# 测试ST股票
result = get_price_with_status("ST600005.SH", "2024-01-15")
assert result["is_st"] is True
assert result["limit_prices"]["limit_up"] == round(result["prev_close"] * 1.05, 2)

# 测试无效代码
with pytest.raises(ValueError):
    get_price_with_status("999999.SH", "2024-01-15")
```

**预计耗时**: 2小时

---

### 第2天: MCP工具层开发 (下午)

#### 任务1.3: 修改 agent_tools/tool_trade.py

**新增功能**:
1. T+1校验(检查买入日期与卖出日期)
2. 涨跌停限制(买入/卖出禁止)
3. 最小交易单位(100股整数倍)
4. 停牌检查(禁止交易停牌股票)
5. 价格精度处理(round to 2位小数)

**核心函数实现**:

```python
# 1. 涨跌停价格计算(参考DESIGN_DEFECTS_FIX.md中的实现)
def calculate_limit_prices(symbol: str, prev_close: float, is_st: bool = False) -> dict:
    """详见设计缺陷修复文档 D1"""
    if symbol.startswith("688") or symbol.startswith("300"):
        limit_ratio = 1.20  # 科创板/创业板
    elif is_st:
        limit_ratio = 1.05  # ST股票
    else:
        limit_ratio = 1.10  # 主板
    
    return {
        "limit_up": round(prev_close * limit_ratio, 2),
        "limit_down": round(prev_close * (2 - limit_ratio), 2)
    }


# 2. 涨跌停判断
def is_limit_up(symbol: str, current_price: float, prev_close: float, is_st: bool = False) -> bool:
    limits = calculate_limit_prices(symbol, prev_close, is_st)
    return current_price >= limits["limit_up"]

def is_limit_down(symbol: str, current_price: float, prev_close: float, is_st: bool = False) -> bool:
    limits = calculate_limit_prices(symbol, prev_close, is_st)
    return current_price <= limits["limit_down"]


# 3. 交易规则校验
def validate_trade_rules(
    symbol: str,
    action: str,  # buy, sell
    amount: int = None,
    price: float = None,
    current_date: str = None,
    position: dict = None,
    **kwargs
) -> dict:
    """
    交易规则校验
    
    Returns:
        {
            "valid": True/False,
            "reason": "错误原因"
        }
    """
    # 获取价格数据
    from agent_tools.tool_get_price_local import get_price_with_status
    price_data = get_price_with_status(symbol, current_date)
    
    # 1. 停牌检查
    if price_data["status"] == "suspended":
        return {"valid": False, "reason": "股票停牌,无法交易"}
    
    # 2. 涨跌停检查
    if action == "buy" and price_data["status"] == "limit_up":
        return {"valid": False, "reason": f"涨停无法买入(涨停价:{price_data['limit_prices']['limit_up']}元)"}
    
    if action == "sell" and price_data["status"] == "limit_down":
        return {"valid": False, "reason": f"跌停无法卖出(跌停价:{price_data['limit_prices']['limit_down']}元)"}
    
    # 3. 最小交易单位检查
    if amount and amount % 100 != 0:
        return {"valid": False, "reason": "买入数量必须是100股的整数倍"}
    
    # 4. T+1检查(仅卖出时)
    if action == "sell" and position:
        buy_date = datetime.strptime(position["buy_date"], "%Y-%m-%d")
        sell_date = datetime.strptime(current_date, "%Y-%m-%d")
        
        if buy_date >= sell_date:
            return {"valid": False, "reason": "T+1规则限制:当日买入的股票无法当日卖出"}
    
    return {"valid": True, "reason": ""}


# 4. 交易执行(修改现有函数,增加校验)
def execute_trade(
    symbol: str,
    action: str,
    amount: int,
    price: float,
    date: str,
    portfolio: dict
) -> dict:
    """
    执行交易(增加A股规则校验)
    """
    # 获取持仓信息(如果是卖出)
    position = portfolio["positions"].get(symbol) if action == "sell" else None
    
    # 交易规则校验
    validation = validate_trade_rules(
        symbol=symbol,
        action=action,
        amount=amount,
        price=price,
        current_date=date,
        position=position
    )
    
    if not validation["valid"]:
        return {
            "success": False,
            "reason": validation["reason"]
        }
    
    # 执行原有交易逻辑...
    # (保持与NASDAQ兼容)
```

**测试验证**:
```bash
pytest tests/unit/test_trade_rules.py -v
```

**预计耗时**: 3小时

---

### 第3天: 配置与提示词修改

#### 任务1.4: 修改 prompts/agent_prompt.py

**增加A股市场规则说明**:

```python
ASTOCK_TRADING_RULES = """
## A股市场交易规则

### 1. T+1制度
- **规则**: 当日买入的股票,次日才能卖出
- **示例**: 1月15日买入的股票,最早1月16日卖出
- **注意**: 卖出后的资金当日可用于买入,但次日才能提现

### 2. 涨跌停限制
- **主板/中小板**: ±10%
  - 涨停价 = 前收盘价 × 1.10
  - 跌停价 = 前收盘价 × 0.90
  - **禁止涨停价买入,跌停价卖出**
  
- **科创板(688xxx)/创业板(300xxx)**: ±20%
  - 涨停价 = 前收盘价 × 1.20
  - 跌停价 = 前收盘价 × 0.80
  
- **ST股票**: ±5%
  - 涨停价 = 前收盘价 × 1.05
  - 跌停价 = 前收盘价 × 0.95

### 3. 最小交易单位
- **买入**: 必须是100股的整数倍(1手=100股)
- **卖出**: 可以不足100股(清仓时)

### 4. 停牌处理
- 停牌股票无法交易
- 持有的停牌股票使用前收盘价估值

### 5. 交易时间
- 开盘集合竞价: 09:15-09:25
- 连续竞价: 09:30-11:30, 13:00-15:00
- 尾盘集合竞价(深市): 14:57-15:00

### 6. 共识筛选建议
使用 `filter_stocks_by_consensus` 工具筛选高共识股票:
- 技术共识: 价格接近年高,金叉形态
- 资金共识: 北向资金流入,融资买入
- 逻辑共识: 券商评级高,热门行业
- 情绪共识: 网络讨论热度高

**建议阈值**: 共识分数 >= 70分
"""

# 修改主提示词
AGENT_PROMPT = f"""
You are an AI trading agent...

{ASTOCK_TRADING_RULES}

...
"""
```

**预计耗时**: 1小时

---

#### 任务1.5: 修改 configs/default_config.json

**增加A股相关配置**:

```json
{
  "market": "a_stock",
  "stock_pool": "HS300",
  "data_source": {
    "primary": "tushare",
    "backup": "akshare",
    "update_frequency": "daily"
  },
  "trading_rules": {
    "t1_enabled": true,
    "limit_check_enabled": true,
    "min_trade_unit": 100,
    "suspend_check_enabled": true
  },
  "consensus_filter": {
    "enabled": true,
    "min_score": 70,
    "min_data_completeness": 0.5
  },
  "backtest": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_cash": 1000000,
    "commission_rate": 0.00025,
    "stamp_tax_rate": 0.001,
    "slippage_rate": 0.005
  }
}
```

**预计耗时**: 0.5小时

---

#### 任务1.6: 阶段一测试

**执行测试**:

```bash
# 1. 单元测试
pytest tests/unit/test_trade_rules.py -v --cov=agent_tools

# 2. 集成测试
pytest tests/integration/test_trade_flow.py::test_it_tf_001 -v

# 3. 数据下载测试
python data/get_astock_data.py --action batch --limit 10

# 4. 手动验收
python
>>> from agent_tools.tool_get_price_local import get_price_with_status
>>> result = get_price_with_status("600519.SH", "2024-01-15")
>>> assert "status" in result
>>> assert "limit_prices" in result
```

**验收标准**:
- [ ] 所有UT-TR系列测试通过(9个用例)
- [ ] IT-TF-001测试通过(正常买入流程)
- [ ] 可成功下载10只股票的历史数据
- [ ] astock_list.json文件包含is_st字段
- [ ] merged.jsonl文件包含status字段

**预计耗时**: 1.5小时

---

## 阶段2: 共识系统 - 多维共识数据获取与筛选 (2天)

### 第4天: 共识数据获取

#### 任务2.1: 创建 data/get_consensus_data.py

**功能需求**:
1. 北向资金数据获取(沪深股通)
2. 融资融券数据获取
3. 券商评级数据获取
4. 行业热度数据获取
5. 数据缺失处理(记录为null)

**核心函数设计**:

```python
# 1. 北向资金
def fetch_northbound_flow(trade_date: str) -> list:
    """
    获取北向资金流向
    
    API: pro.moneyflow_hsgt(trade_date='20240115')
    
    Returns:
        [
            {
                "symbol": "600519.SH",
                "date": "2024-01-15",
                "north_money": 50000000.0,  # 北向资金净流入(元)
                "north_volume": 27000  # 北向资金净买入股数
            }
        ]
    """
    pass


# 2. 融资融券
def fetch_margin_data(trade_date: str) -> list:
    """
    获取融资融券数据
    
    API: pro.margin_detail(trade_date='20240115')
    
    Returns:
        [
            {
                "symbol": "600519.SH",
                "date": "2024-01-15",
                "rzye": 1500000000.0,  # 融资余额
                "rzmre": 80000000.0,   # 融资买入额
                "rqye": 50000000.0,    # 融券余额
                "rqyl": 27000          # 融券余量
            }
        ]
    """
    pass


# 3. 券商评级
def fetch_analyst_rating(symbol: str = None) -> list:
    """
    获取券商评级
    
    API: pro.stk_surv(symbol='600519.SH')
    
    Returns:
        [
            {
                "symbol": "600519.SH",
                "date": "2024-01-15",
                "rating": "买入",
                "rating_count": 15,  # 近30天推荐次数
                "target_price": 2100.0
            }
        ]
    """
    pass


# 4. 行业热度
def fetch_industry_heat(trade_date: str) -> list:
    """
    获取行业热度排名
    
    基于行业资金流入、涨跌幅、成交量综合计算
    
    Returns:
        [
            {
                "industry": "白酒",
                "date": "2024-01-15",
                "rank": 3,  # 行业热度排名
                "money_flow": 500000000.0,  # 行业资金流入
                "avg_change": 2.5  # 行业平均涨幅
            }
        ]
    """
    pass


# 5. 批量获取并合并
def download_consensus_data(
    start_date: str,
    end_date: str,
    stock_pool: list
) -> None:
    """
    批量下载共识数据并保存到consensus_data.jsonl
    
    存储格式:
    {
        "symbol": "600519.SH",
        "date": "2024-01-15",
        "northbound": {"net_flow": 50000000.0} or null,
        "margin": {"net_buy": 80000000.0} or null,
        "rating": {"recommend_count": 15} or null,
        "industry": {"rank": 3} or null
    }
    """
    pass
```

**数据缺失处理**:
```python
# 如果某个数据源无数据,存储为null
{
    "symbol": "300999.SZ",
    "date": "2024-01-15",
    "northbound": null,  # 数据缺失
    "margin": {"net_buy": 1000000.0},
    "rating": null,  # 数据缺失
    "industry": {"rank": 10}
}
```

**测试验证**:
```bash
# 测试单日数据获取
python data/get_consensus_data.py --date 2024-01-15

# 测试批量下载
python data/get_consensus_data.py --start 2024-01-01 --end 2024-01-31 --pool HS300
```

**预计耗时**: 4小时

---

### 第5天: 共识工具开发

#### 任务2.2: 创建 agent_tools/tool_get_consensus.py

**实现5个查询函数**:

```python
# 1. 北向资金查询
def get_northbound_flow(symbol: str, date: str) -> dict:
    """从consensus_data.jsonl读取北向资金数据"""
    data = read_consensus_from_jsonl(symbol, date)
    return data.get("northbound") if data else None


# 2. 融资融券查询
def get_margin_data(symbol: str, date: str) -> dict:
    """从consensus_data.jsonl读取融资融券数据"""
    data = read_consensus_from_jsonl(symbol, date)
    return data.get("margin") if data else None


# 3. 券商评级查询
def get_analyst_rating(symbol: str, date: str) -> dict:
    """从consensus_data.jsonl读取券商评级数据"""
    data = read_consensus_from_jsonl(symbol, date)
    return data.get("rating") if data else None


# 4. 行业热度查询
def get_industry_heat(symbol: str, date: str) -> dict:
    """
    查询股票所属行业的热度
    
    需要:
    1. 从astock_list.json获取股票所属行业
    2. 从consensus_data.jsonl获取行业热度数据
    """
    # 获取行业
    stock_info = get_stock_info(symbol)
    industry = stock_info["industry"]
    
    # 查询行业热度
    data = read_consensus_from_jsonl(symbol, date)
    industry_data = data.get("industry") if data else None
    
    return industry_data


# 5. 综合共识查询
def get_all_consensus(symbol: str, date: str) -> dict:
    """一次性获取所有共识数据"""
    return {
        "northbound": get_northbound_flow(symbol, date),
        "margin": get_margin_data(symbol, date),
        "rating": get_analyst_rating(symbol, date),
        "industry": get_industry_heat(symbol, date)
    }
```

**预计耗时**: 2小时

---

#### 任务2.3: 创建 agent_tools/tool_consensus_filter.py

**实现共识分数计算**(参考DESIGN_DEFECTS_FIX.md D3部分):

```python
# 详细实现见设计缺陷修复文档 3.2节
def calculate_consensus_score(symbol: str, date: str) -> dict:
    """
    计算共识分数(含缺失数据处理)
    
    Returns:
        {
            "symbol": "600519.SH",
            "date": "2024-01-15",
            "scores": {
                "technical": 20,
                "fund": 30,
                "logic": 15,  # 券商评级缺失,只有行业热度
                "sentiment": 20
            },
            "total_score": 85,
            "missing_data": ["analyst_rating"],
            "data_completeness": 0.75
        }
    """
    pass


def filter_stocks_by_consensus(
    stock_pool: list,
    date: str,
    min_score: int = 70,
    min_data_completeness: float = 0.5
) -> list:
    """
    根据共识分数筛选股票
    
    Returns:
        [
            {
                "symbol": "600519.SH",
                "total_score": 95,
                "data_completeness": 1.0,
                "scores": {...}
            }
        ]
    """
    pass
```

**预计耗时**: 3小时

---

#### 任务2.4: 修改 agent_tools/tool_jina_search.py

**适配中文搜索**:

```python
# 修改搜索模板
SEARCH_TEMPLATE_ASTOCK = """
搜索关键词: {stock_name} {keyword}
信息源优先级:
1. 东方财富网
2. 雪球
3. 同花顺
4. 证券之星
5. 新浪财经

时间范围: 近7天
"""

def search_stock_discussion(symbol: str, date: str) -> dict:
    """
    搜索股票讨论热度
    
    Returns:
        {
            "discussion_count": 5000,
            "sentiment": "positive",  # positive, neutral, negative
            "keywords": ["白酒", "业绩", "涨价"]
        }
    """
    # 获取股票名称
    stock_info = get_stock_info(symbol)
    stock_name = stock_info["name"]
    
    # 构造搜索查询
    query = f"{stock_name} 股票 讨论"
    
    # 执行搜索
    results = jina_search(query, template=SEARCH_TEMPLATE_ASTOCK)
    
    # 统计讨论数
    discussion_count = len(results)
    
    return {
        "discussion_count": discussion_count,
        "sentiment": analyze_sentiment(results),
        "keywords": extract_keywords(results)
    }
```

**预计耗时**: 1小时

---

#### 任务2.5: 阶段二测试

```bash
# 单元测试
pytest tests/unit/test_consensus_score.py -v

# 集成测试
pytest tests/integration/test_consensus_filter.py -v

# 手动验收
python
>>> from agent_tools.tool_consensus_filter import filter_stocks_by_consensus
>>> results = filter_stocks_by_consensus(["600519.SH", "000001.SZ"], "2024-01-15", min_score=70)
>>> assert len(results) > 0
>>> assert all(r["total_score"] >= 70 for r in results)
```

**验收标准**:
- [ ] UT-CS系列测试通过(5个用例)
- [ ] IT-CF系列测试通过
- [ ] consensus_data.jsonl文件已生成
- [ ] 数据缺失情况下不抛出异常

**预计耗时**: 2小时

---

## 阶段3: 回测系统 - 历史数据回测与绩效分析 (2天)

### 第6天: 回测引擎开发

#### 任务3.1: 创建 tools/backtest_engine.py

**核心类设计**:

```python
class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: dict):
        self.config = config
        self.current_date = None
        self.portfolio = {
            "cash": config["initial_cash"],
            "positions": {},
            "trades": [],
            "daily_values": []
        }
        self.data_cache = {}
    
    def load_data(self, start_date: str, end_date: str):
        """加载回测数据到缓存"""
        pass
    
    def get_price_data(self, symbol: str, date: datetime) -> dict:
        """
        获取价格数据(带时间旅行验证)
        
        Raises:
            TimeViolationError: 如果访问未来数据
        """
        if date > self.current_date:
            raise TimeViolationError(f"禁止访问未来数据: {date} > {self.current_date}")
        
        # 从缓存读取
        key = f"{symbol}_{date.strftime('%Y-%m-%d')}"
        return self.data_cache.get(key)
    
    def simulate_trade_day(self, date: datetime):
        """模拟单日交易"""
        self.current_date = date
        
        # 1. 获取当日所有股票数据
        daily_data = self.load_daily_data(date)
        
        # 2. 识别停牌股票
        suspended = [d for d in daily_data if d["status"] == "suspended"]
        
        # 3. Agent决策
        decision = self.agent.make_decision(date)
        
        # 4. 执行交易(过滤停牌股票)
        for trade in decision["trades"]:
            if trade["symbol"] not in suspended:
                self.execute_trade(trade, date)
        
        # 5. 计算当日市值
        self.calculate_portfolio_value(date, daily_data)
    
    def calculate_metrics(self) -> dict:
        """
        计算绩效指标
        
        Returns:
            {
                "total_return": 0.25,  # 25%
                "annual_return": 0.30,  # 年化30%
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.15,  # 最大回撤15%
                "win_rate": 0.60,  # 胜率60%
                "total_trades": 50
            }
        """
        pass
    
    def generate_report(self, output_path: str):
        """生成HTML回测报告"""
        pass
    
    def run(self) -> dict:
        """执行完整回测"""
        # 1. 加载数据
        self.load_data(self.config["start_date"], self.config["end_date"])
        
        # 2. 获取交易日历
        trade_dates = self.get_trade_calendar(
            self.config["start_date"],
            self.config["end_date"]
        )
        
        # 3. 逐日模拟
        for date in trade_dates:
            self.simulate_trade_day(date)
        
        # 4. 计算绩效
        metrics = self.calculate_metrics()
        
        # 5. 生成报告
        self.generate_report("backtest_results/report.html")
        
        return metrics


class TimeViolationError(Exception):
    """时间旅行违规异常"""
    pass
```

**滑点与手续费模拟**(参考设计文档3.2.3节):

```python
def calculate_transaction_cost(
    symbol: str,
    action: str,
    amount: int,
    price: float
) -> dict:
    """
    计算交易成本
    
    Returns:
        {
            "commission": 100.0,  # 佣金
            "stamp_tax": 200.0,   # 印花税(仅卖出)
            "transfer_fee": 5.0,  # 过户费(仅沪市)
            "slippage": 50.0,     # 滑点
            "total_cost": 355.0
        }
    """
    value = amount * price
    
    # 佣金(万分之2.5,最低5元)
    commission = max(value * 0.00025, 5.0)
    
    # 印花税(千分之1,仅卖出)
    stamp_tax = value * 0.001 if action == "sell" else 0
    
    # 过户费(万分之0.2,仅沪市)
    transfer_fee = value * 0.00002 if symbol.endswith(".SH") else 0
    
    # 滑点(±0.5%)
    slippage = value * 0.005
    
    return {
        "commission": round(commission, 2),
        "stamp_tax": round(stamp_tax, 2),
        "transfer_fee": round(transfer_fee, 2),
        "slippage": round(slippage, 2),
        "total_cost": round(commission + stamp_tax + transfer_fee + slippage, 2)
    }
```

**预计耗时**: 5小时

---

### 第7天: 回测Agent与配置

#### 任务3.2: 创建 agent/backtest_agent.py

```python
from agent.base_agent import BaseAgent

class BacktestAgent(BaseAgent):
    """回测专用Agent"""
    
    def __init__(self, backtest_engine):
        super().__init__()
        self.engine = backtest_engine
        self.use_local_data = True  # 强制使用本地数据
    
    def get_price(self, symbol: str, date: str) -> dict:
        """覆盖父类方法,使用回测引擎的数据"""
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        return self.engine.get_price_data(symbol, date_obj)
    
    def make_decision(self, current_date: datetime) -> dict:
        """
        基于当前日期做出交易决策
        
        Returns:
            {
                "trades": [
                    {"symbol": "600519.SH", "action": "buy", "amount": 100}
                ]
            }
        """
        # 调用LLM决策
        # 使用共识筛选工具
        # 返回交易指令
        pass
```

**预计耗时**: 2小时

---

#### 任务3.3: 创建示例配置文件

**configs/backtest/example_hs300_conservative.json**:

```json
{
  "name": "沪深300稳健策略",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_cash": 1000000,
  "stock_pool": "HS300",
  "max_position_per_stock": 0.20,
  "max_total_position": 0.80,
  "consensus_filter": {
    "min_score": 80,
    "min_data_completeness": 0.75
  },
  "risk_control": {
    "stop_loss": 0.10,
    "take_profit": 0.20,
    "max_drawdown": 0.15
  }
}
```

**configs/backtest/example_kc50_aggressive.json**:

```json
{
  "name": "科创50激进策略",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_cash": 1000000,
  "stock_pool": "KC50",
  "max_position_per_stock": 0.30,
  "max_total_position": 0.95,
  "consensus_filter": {
    "min_score": 70,
    "min_data_completeness": 0.50
  },
  "risk_control": {
    "stop_loss": 0.15,
    "take_profit": 0.30,
    "max_drawdown": 0.25
  }
}
```

**预计耗时**: 0.5小时

---

#### 任务3.4: 阶段三测试

```bash
# 单元测试
pytest tests/unit/test_time_travel.py -v
pytest tests/backtest/test_backtest_accuracy.py -v
pytest tests/backtest/test_backtest_data.py -v
pytest tests/backtest/test_backtest_metrics.py -v

# 执行示例回测
python tools/backtest_engine.py --config configs/backtest/example_hs300_conservative.json

# 验证报告生成
ls -lh backtest_results/report.html
```

**验收标准**:
- [ ] UT-TT系列测试通过(4个用例)
- [ ] BT-ACC系列测试通过(2个用例)
- [ ] BT-DATA系列测试通过
- [ ] BT-METRIC系列测试通过
- [ ] 成功生成HTML回测报告
- [ ] 全年回测耗时<10分钟

**预计耗时**: 2.5小时

---

## 阶段4: 全面测试与优化 (2天)

### 第8天: 边界测试与集成测试

#### 任务4.1: 边界场景测试

```bash
# 执行所有EDGE系列测试
pytest tests/edge_cases/ -v
```

**重点测试场景**:
1. 异常数据处理(EDGE-001~004)
2. 极端市场环境(EDGE-005~007)
3. 数据缺失容错
4. API限流处理

**预计耗时**: 3小时

---

#### 任务4.2: 完整集成测试

```bash
# 执行完整流程测试
pytest tests/integration/test_full_flow.py -v
```

**测试流程**:
1. 数据下载(10只股票,1个月)
2. 共识筛选(筛出5只高分股票)
3. 模拟交易(执行买入卖出)
4. 回测验证(全流程回测)

**预计耗时**: 2小时

---

#### 任务4.3: 性能测试

```bash
# 测试全年回测耗时
time python tools/backtest_engine.py --config configs/backtest/example_hs300_conservative.json

# 测试API调用频率
python tests/performance/test_api_rate_limit.py
```

**性能目标**:
- 全年回测(240交易日) < 10分钟
- 单日交易模拟 < 3秒
- API调用不超限(120次/分钟)

**预计耗时**: 2小时

---

### 第9天: 兼容性测试与文档完善

#### 任务4.4: 兼容性测试

**验证NASDAQ市场功能未受影响**:

```bash
# 切换回NASDAQ配置
cp configs/nasdaq_config.json configs/default_config.json

# 执行原有测试
pytest tests/nasdaq/ -v

# 验证原有功能
python main.py --mode nasdaq --days 1
```

**预计耗时**: 1小时

---

#### 任务4.5: 安全性测试

```bash
# 检查.env是否被git追踪
git status .env  # 应该提示未追踪

# 检查提交历史
git log -p | grep -i "tushare_token"  # 应该无输出

# 验证.env.example存在
cat .env.example
```

**预计耗时**: 0.5小时

---

#### 任务4.6: 文档完善

**需要创建/更新的文档**:

1. **API文档** (`docs/API_REFERENCE.md`)
   - 所有新增函数的详细说明
   - 参数说明
   - 返回值格式
   - 示例代码

2. **使用说明** (`docs/ASTOCK_USER_GUIDE.md`)
   - 环境配置步骤
   - 数据下载教程
   - 回测执行指南
   - 常见问题FAQ

3. **测试报告** (`docs/TEST_REPORT.md`)
   - 测试用例执行结果
   - 覆盖率报告
   - 性能测试数据
   - 问题汇总

**预计耗时**: 3.5小时

---

## 风险控制与应急预案

### 风险清单

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| Tushare API限流 | 高 | 中 | 1. 降低下载频率<br>2. 切换到AkShare备用 |
| 数据质量问题 | 中 | 高 | 1. 增强数据校验<br>2. 人工复核异常数据 |
| 回测性能不达标 | 中 | 中 | 1. 优化数据加载<br>2. 使用缓存机制 |
| LLM决策不稳定 | 高 | 中 | 1. 增加规则校验<br>2. 设置决策边界 |
| 时间超期 | 中 | 高 | 1. 优先完成核心功能<br>2. 延后优化任务 |

### 应急决策树

```
发现进度延迟
    │
    ├─延迟<1天 ─► 加班完成当前阶段
    │
    └─延迟≥1天
        │
        ├─核心功能完成 ─► 跳过优化任务,直接进入测试
        │
        └─核心功能未完成
            │
            ├─阶段1未完成 ─► 暂停后续阶段,集中完成阶段1
            │
            ├─阶段2未完成 ─► 简化共识筛选,只保留资金共识
            │
            └─阶段3未完成 ─► 使用简化版回测(不含滑点手续费)
```

---

## 验收检查清单

### 阶段一验收

- [ ] get_astock_data.py可成功下载沪深300股票列表
- [ ] astock_list.json包含is_st字段
- [ ] merged.jsonl包含status字段(normal, suspended, limit_up, limit_down)
- [ ] tool_get_price_local.py返回涨跌停状态
- [ ] tool_trade.py通过所有UT-TR测试(9个用例)
- [ ] 可执行单日模拟交易

### 阶段二验收

- [ ] consensus_data.jsonl包含所有共识数据
- [ ] 数据缺失情况下不抛出异常
- [ ] tool_consensus_filter.py通过所有UT-CS测试(5个用例)
- [ ] 共识筛选功能正常工作
- [ ] 可筛选出高共识股票(分数≥70)

### 阶段三验收

- [ ] backtest_engine.py可执行完整回测
- [ ] 时间旅行验证通过所有UT-TT测试(4个用例)
- [ ] 回测绩效指标计算正确(BT-METRIC测试通过)
- [ ] 生成HTML回测报告
- [ ] 全年回测耗时<10分钟

### 最终验收

- [ ] 所有单元测试通过(UT-TR, UT-CS, UT-TT系列)
- [ ] 所有集成测试通过(IT-TF, IT-CF系列)
- [ ] 所有回测测试通过(BT-ACC, BT-DATA, BT-METRIC系列)
- [ ] 边界测试通过率≥90%
- [ ] NASDAQ市场功能未受影响
- [ ] 代码覆盖率≥80%
- [ ] 文档完整(API文档、使用说明、测试报告)
- [ ] .env文件未被提交到git

---

## 后续优化建议

**V2.0版本规划**:

1. **增强功能**:
   - 实时行情接入(WebSocket)
   - 多账户管理
   - 仓位优化算法
   - 风险预警系统

2. **性能优化**:
   - 数据库存储(替代JSONL)
   - 分布式回测
   - GPU加速计算

3. **用户体验**:
   - Web可视化界面
   - 移动端App
   - 微信/钉钉消息推送

4. **数据扩展**:
   - 财务数据接入
   - 新闻舆情分析
   - 宏观经济指标

---

**文档版本**: v1.0  
**创建日期**: 2024-01-15  
**预计完成日期**: 2024-01-26 (9.5个工作日)

**下一步行动**:  
1. 开发团队确认实施路线图
2. 分配各阶段负责人
3. 开始阶段1开发工作
