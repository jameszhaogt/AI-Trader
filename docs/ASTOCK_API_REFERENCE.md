# A股适配 API 文档

## 目录
- [数据获取API](#数据获取api)
- [交易规则API](#交易规则api)
- [共识数据API](#共识数据api)
- [回测引擎API](#回测引擎api)

---

## 数据获取API

### AStockDataFetcher

A股历史行情数据获取器

#### 初始化

```python
from data.get_astock_data import AStockDataFetcher

fetcher = AStockDataFetcher(token="your_tushare_token")
```

**参数**:
- `token` (str, optional): Tushare API token，未提供时从环境变量TUSHARE_TOKEN读取

#### load_stock_pool()

加载股票池

```python
symbols = fetcher.load_stock_pool(pool_name="hs300")
```

**参数**:
- `pool_name` (str): 股票池名称
  - `hs300`: 沪深300
  - `zz500`: 中证500
  - `kc50`: 科创50
  - `custom`: 自定义

**返回**: `List[str]` - 股票代码列表

#### fetch_daily_data()

获取单只股票日线数据

```python
df = fetcher.fetch_daily_data(
    symbol="600519.SH",
    start_date="20240101",
    end_date="20241231"
)
```

**参数**:
- `symbol` (str): 股票代码，如 `600519.SH`
- `start_date` (str): 开始日期，格式 `YYYYMMDD`
- `end_date` (str): 结束日期，格式 `YYYYMMDD`

**返回**: `pd.DataFrame` - 包含以下列:
- `trade_date`: 交易日期
- `open`, `high`, `low`, `close`: 原始价格
- `adj_open`, `adj_high`, `adj_low`, `adj_close`: 前复权价格
- `vol`: 成交量（手）
- `adj_factor`: 复权因子

#### download_stock_data()

批量下载并保存数据

```python
fetcher.download_stock_data(
    symbols=["600519.SH", "000858.SZ"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    incremental=False
)
```

**参数**:
- `symbols` (List[str]): 股票代码列表
- `start_date` (str): 开始日期，格式 `YYYY-MM-DD`
- `end_date` (str): 结束日期，格式 `YYYY-MM-DD`
- `incremental` (bool): 是否增量更新

**输出**: 保存到 `data/merged.jsonl`

---

## 交易规则API

### AStockRuleValidator

A股交易规则校验器

#### 初始化

```python
from tools.astock_rules import AStockRuleValidator

validator = AStockRuleValidator()
```

或使用全局实例：

```python
from tools.astock_rules import get_validator

validator = get_validator()
```

#### get_board_type()

识别股票板块类型

```python
board = validator.get_board_type("600519.SH")  # 返回: 'main_board'
board = validator.get_board_type("688001.SH")  # 返回: 'star_market'
```

**参数**:
- `symbol` (str): 股票代码

**返回**: `str` - 板块类型
- `main_board`: 主板
- `star_market`: 科创板
- `gem_board`: 创业板
- `st_stock`: ST股票

#### get_price_limit()

获取涨跌幅限制

```python
limit = validator.get_price_limit("600519.SH")  # 返回: 0.1 (10%)
limit = validator.get_price_limit("688001.SH")  # 返回: 0.2 (20%)
```

**参数**:
- `symbol` (str): 股票代码

**返回**: `float` - 涨跌幅限制（小数形式）

#### check_limit_up()

检查是否涨停

```python
is_limit_up = validator.check_limit_up(
    symbol="600519.SH",
    current_price=2200.0,
    prev_close=2000.0
)  # 返回: True (涨幅10%)
```

**参数**:
- `symbol` (str): 股票代码
- `current_price` (float): 当前价格
- `prev_close` (float): 前收盘价

**返回**: `bool` - True表示涨停

#### check_limit_down()

检查是否跌停

```python
is_limit_down = validator.check_limit_down(
    symbol="600519.SH",
    current_price=1800.0,
    prev_close=2000.0
)  # 返回: True (跌幅10%)
```

**参数**:
- `symbol` (str): 股票代码
- `current_price` (float): 当前价格
- `prev_close` (float): 前收盘价

**返回**: `bool` - True表示跌停

#### check_suspended()

检查是否停牌

```python
is_suspended = validator.check_suspended(
    symbol="600519.SH",
    date="2024-01-15"
)
```

**参数**:
- `symbol` (str): 股票代码
- `date` (str): 交易日期，格式 `YYYY-MM-DD`

**返回**: `bool` - True表示停牌

#### check_t_plus_1()

检查T+1限制

```python
can_sell, error = validator.check_t_plus_1(
    symbol="600519.SH",
    current_date="2024-01-15",
    signature="model_v1"
)
```

**参数**:
- `symbol` (str): 股票代码
- `current_date` (str): 当前日期
- `signature` (str): 模型签名

**返回**: `Tuple[bool, Optional[str]]`
- `can_sell`: 是否可以卖出
- `error`: 错误信息（如果不能卖出）

#### validate_trade_rules()

综合校验交易规则

```python
result = validator.validate_trade_rules(
    symbol="600519.SH",
    amount=100,
    action="buy",
    current_date="2024-01-15",
    signature="model_v1"
)
```

**参数**:
- `symbol` (str): 股票代码
- `amount` (int): 交易数量
- `action` (str): `buy` 或 `sell`
- `current_date` (str): 交易日期
- `signature` (str): 模型签名

**返回**: `Dict[str, Any]`
```python
{
    "valid": True,      # 是否合规
    "error": None       # 错误信息
}
```

或

```python
{
    "valid": False,
    "error": "买入数量必须是100股的整数倍（1手=100股）"
}
```

---

## 共识数据API

> **注意**: 此部分API待实现

### 预期接口设计

#### get_northbound_flow()

获取北向资金流向

```python
from agent_tools.tool_get_consensus import get_northbound_flow

result = get_northbound_flow(
    symbol="600519.SH",
    date="2024-01-15"
)
```

**返回**:
```python
{
    "net_buy": 120000000,  # 净买入额（元）
    "rank": 5,             # 排名
    "buy_amount": 150000000,
    "sell_amount": 30000000
}
```

#### get_margin_info()

获取融资融券信息

```python
from agent_tools.tool_get_consensus import get_margin_info

result = get_margin_info(
    symbol="600519.SH",
    date="2024-01-15"
)
```

**返回**:
```python
{
    "margin_balance": 5000000000,  # 融资余额（元）
    "chg_rate": 0.05,              # 变化率
    "margin_buy": 100000000,
    "margin_repay": 50000000
}
```

#### filter_by_consensus()

按共识分数筛选股票

```python
from agent_tools.tool_consensus_filter import filter_by_consensus

result = filter_by_consensus(
    date="2024-01-15",
    min_consensus_score=70
)
```

**返回**:
```python
[
    {
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "consensus_score": 85,
        "details": {
            "technical": 18,   # 技术共识分
            "capital": 28,     # 资金共识分
            "logic": 30,       # 逻辑共识分
            "sentiment": 19    # 情绪共识分
        }
    },
    ...
]
```

---

## 回测引擎API

> **注意**: 此部分API待实现

### BacktestEngine

回测引擎核心类

#### 初始化

```python
from tools.backtest_engine import BacktestEngine

engine = BacktestEngine(config_path="configs/backtest_config.json")
```

#### run()

执行回测

```python
results = engine.run(
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_cash=1000000
)
```

**返回**: 回测结果对象

#### generate_report()

生成回测报告

```python
engine.generate_report(
    output_dir="data/backtest_results/run_20241231"
)
```

**输出文件**:
- `trades.jsonl`: 交易明细
- `daily_positions.jsonl`: 每日持仓
- `metrics.json`: 绩效指标
- `report.html`: 可视化报告

---

## 工具函数

### 便捷函数

```python
from tools.astock_rules import validate_trade_rules

# 快速校验交易规则
result = validate_trade_rules(
    symbol="600519.SH",
    amount=100,
    action="buy",
    current_date="2024-01-15",
    signature="model_v1"
)
```

### 配置读取

```python
from tools.general_tools import get_config_value

market = get_config_value("MARKET")
today_date = get_config_value("TODAY_DATE")
```

---

## 错误处理

### 常见错误码

| 错误信息 | 说明 | 解决方案 |
|---------|------|---------|
| `T+1规则：今日买入股票明日才可卖出` | 违反T+1规则 | 等待下一个交易日 |
| `买入数量必须是100股的整数倍` | 最小交易单位错误 | 调整数量为100的倍数 |
| `股票XXX在XXXX-XX-XX停牌` | 股票停牌 | 选择其他股票 |
| `Insufficient cash!` | 资金不足 | 减少买入数量 |
| `Symbol XXX not found!` | 股票不存在 | 检查股票代码 |

### 异常捕获示例

```python
try:
    result = validator.validate_trade_rules(
        symbol="600519.SH",
        amount=100,
        action="buy",
        current_date="2024-01-15",
        signature="model_v1"
    )
    
    if not result["valid"]:
        print(f"交易不合规: {result['error']}")
except Exception as e:
    print(f"校验失败: {e}")
```

---

## 数据格式说明

### merged.jsonl 格式

每行一个股票的JSON对象：

```json
{
  "Meta Data": {
    "1. Information": "Daily Prices (open, high, low, close) and Volumes",
    "2. Symbol": "600519.SH",
    "3. Last Refreshed": "20241231",
    "4. Output Size": "Full size",
    "5. Time Zone": "Asia/Shanghai"
  },
  "Time Series (Daily)": {
    "2024-01-15": {
      "1. buy price": "2000.0000",
      "2. high": "2050.0000",
      "3. low": "1980.0000",
      "4. sell price": "2020.0000",
      "5. volume": "1234567"
    }
  }
}
```

### consensus_data.jsonl 格式（待实现）

```json
{
  "date": "2024-01-15",
  "symbol": "600519.SH",
  "northbound_flow": 120000000,
  "margin_balance_chg": 0.05,
  "broker_recommend_count": 12,
  "industry": "白酒",
  "industry_heat": 0.85
}
```

---

## 版本兼容性

| API | 版本 | 状态 |
|-----|------|------|
| AStockDataFetcher | v1.0 | ✅ 已实现 |
| AStockRuleValidator | v1.0 | ✅ 已实现 |
| 共识数据API | v1.0 | ⏳ 待实现 |
| 回测引擎API | v1.0 | ⏳ 待实现 |

---

## 更新日志

### v1.0.0 (2025-11-03)

- ✅ 新增 AStockDataFetcher 数据获取器
- ✅ 新增 AStockRuleValidator 规则校验器
- ✅ 集成 tool_trade.py A股规则校验
- ⏳ 共识数据API设计完成，待实现
- ⏳ 回测引擎API设计完成，待实现
