# A股市场配置说明文档

## 配置文件概览

A股市场适配后,项目提供了多个配置文件模板,适应不同的投资策略和需求:

### 1. 配置文件列表

| 配置文件 | 用途 | 适合人群 |
|---------|------|---------|
| `default_config.json` | 默认配置,包含基础A股规则 | 开发调试 |
| `astock_conservative.json` | 沪深300稳健策略 | 风险偏好低 |
| `astock_aggressive.json` | 科创50进取策略 | 风险偏好高 |
| `astock_custom_stocks.json` | 自定义股票池 | 有研究的投资者 |

---

## 2. default_config.json 配置说明

### 2.1 市场类型 (market)
```json
"market": "a_stock"
```
- 可选值: `"a_stock"`, `"us_stock"`
- 说明: 指定交易市场,决定应用哪套交易规则

### 2.2 交易规则 (trading_rules)
```json
"trading_rules": {
  "t_plus": 1,
  "price_limit": {
    "main_board": 0.1,      // 主板 ±10%
    "star_market": 0.2,     // 科创板 ±20%
    "gem_board": 0.2,       // 创业板 ±20%
    "st_stock": 0.05        // ST股票 ±5%
  },
  "min_unit": 100           // 最小交易单位100股
}
```

**说明**:
- `t_plus`: T+1交易制度,当日买入次日才能卖出
- `price_limit`: 不同板块的涨跌幅限制
- `min_unit`: 最小交易单位(手)

### 2.3 数据源 (data_source)
```json
"data_source": {
  "provider": "tushare",
  "api_token": "${TUSHARE_TOKEN}"
}
```

**说明**:
- `provider`: 主数据源,支持 `tushare` 或 `akshare`
- `api_token`: API密钥,使用环境变量引用
- **重要**: 需在 `.env` 文件中配置 `TUSHARE_TOKEN=your_token_here`

### 2.4 共识筛选 (consensus_filter)
```json
"consensus_filter": {
  "enabled": true,
  "min_score": 70,
  "weights": {
    "technical": 0.2,   // 技术面权重 20%
    "capital": 0.3,     // 资金面权重 30%
    "logic": 0.3,       // 逻辑面权重 30%
    "sentiment": 0.2    // 情绪面权重 20%
  }
}
```

**说明**:
- `enabled`: 是否启用共识筛选
- `min_score`: 最低总分阈值(0-100分)
- `weights`: 4个维度的权重,总和为1.0

### 2.5 股票池 (stock_pool)
```json
"stock_pool": "hs300",
"custom_stocks": []
```

**可选值**:
- `"hs300"`: 沪深300指数成分股(约300只)
- `"kc50"`: 科创50指数成分股(50只)
- `"custom"`: 自定义股票池,需配置 `custom_stocks` 数组

**示例**:
```json
"stock_pool": "custom",
"custom_stocks": ["600000", "600036", "600519"]
```

### 2.6 Agent配置 (agent_config)
```json
"agent_config": {
  "max_steps": 30,
  "max_retries": 3,
  "base_delay": 1.0,
  "initial_cash": 10000.0
}
```

**说明**:
- `max_steps`: 最大决策步数
- `max_retries`: API调用失败重试次数
- `base_delay`: 重试延迟时间(秒)
- `initial_cash`: 初始资金(元)

---

## 3. 环境变量配置 (.env)

在项目根目录创建 `.env` 文件(已在 `.gitignore` 中):

```bash
# Tushare Pro API Token
TUSHARE_TOKEN=your_tushare_token_here

# 可选:其他API密钥
AKSHARE_TOKEN=your_akshare_token_here

# OpenAI API配置(如果使用)
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_key
```

**获取Tushare Token**:
1. 注册账号: https://tushare.pro/register
2. 完成积分任务(建议积分≥500分,支持更多接口)
3. 在个人中心获取Token

---

## 4. 配置文件使用示例

### 4.1 使用默认配置运行回测
```bash
python main.py --config configs/default_config.json
```

### 4.2 使用沪深300稳健策略
```bash
python main.py --config configs/astock_conservative.json
```

### 4.3 使用科创50进取策略
```bash
python main.py --config configs/astock_aggressive.json
```

### 4.4 使用自定义股票池
```bash
python main.py --config configs/astock_custom_stocks.json
```

---

## 5. 配置验证清单

在运行前,请确认以下配置正确:

- [ ] `.env` 文件已创建,包含 `TUSHARE_TOKEN`
- [ ] `market` 字段设置为 `"a_stock"`
- [ ] `trading_rules` 包含完整的A股规则
- [ ] `data_source.provider` 设置为 `"tushare"` 或 `"akshare"`
- [ ] `stock_pool` 选择合适的股票池
- [ ] `initial_cash` 设置合理的初始资金
- [ ] `.gitignore` 已配置,避免提交敏感信息

---

## 6. 常见问题

### Q1: Tushare Token无效怎么办?
A: 检查 `.env` 文件中的 `TUSHARE_TOKEN` 是否正确,确认账号积分是否满足接口要求。

### Q2: 如何切换到AkShare数据源?
A: 修改配置文件:
```json
"data_source": {
  "provider": "akshare",
  "api_token": ""  // AkShare不需要Token
}
```

### Q3: 如何调整共识筛选权重?
A: 修改 `consensus_filter.weights`,确保4个权重之和为1.0:
```json
"weights": {
  "technical": 0.25,   // 技术面提高到25%
  "capital": 0.35,     // 资金面提高到35%
  "logic": 0.25,       // 逻辑面降低到25%
  "sentiment": 0.15    // 情绪面降低到15%
}
```

### Q4: 如何禁用共识筛选?
A: 设置 `"enabled": false`:
```json
"consensus_filter": {
  "enabled": false
}
```

### Q5: 回测时如何修改时间范围?
A: 修改 `date_range`:
```json
"date_range": {
  "init_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

---

## 7. 高级配置

### 7.1 风险控制参数
在自定义配置文件中可添加:
```json
"risk_control": {
  "max_drawdown_limit": 0.15,     // 最大回撤15%
  "stop_loss_ratio": 0.08,        // 止损线8%
  "take_profit_ratio": 0.20,      // 止盈线20%
  "max_position_ratio": 0.30,     // 单股最大仓位30%
  "reserve_ratio": 0.10           // 现金储备10%
}
```

### 7.2 回测参数
```json
"backtest": {
  "mode": "backtest",
  "enable_time_travel_check": true,
  "enable_compliance_check": true,
  "commission_rate": 0.0003,
  "slippage_rate": 0.001,
  "benchmark": "000300.SH"
}
```

### 7.3 日志配置
```json
"logging": {
  "level": "INFO",
  "log_file": "./logs/astock_backtest.log",
  "log_trades": true,
  "log_daily_positions": true
}
```

---

## 8. 配置模板对比

| 配置项 | 稳健策略 | 进取策略 | 自定义策略 |
|--------|---------|---------|-----------|
| 股票池 | 沪深300 | 科创50 | 10只精选 |
| 最大持仓 | 5只 | 8只 | 6只 |
| 单股仓位 | ≤30% | ≤25% | ≤25% |
| 现金储备 | 10% | 5% | 8% |
| 共识阈值 | ≥70分 | ≥65分 | ≥68分 |
| 止损线 | -8% | -12% | -10% |
| 止盈线 | +20% | +35% | +25% |
| 调仓频率 | 每周 | 每日 | 每周 |

---

## 9. 配置验证命令

运行配置验证脚本:
```bash
python -c "
import json
with open('configs/astock_conservative.json') as f:
    config = json.load(f)
    print('配置加载成功')
    print(f\"市场类型: {config.get('market', 'N/A')}\")
    print(f\"股票池: {config.get('data', {}).get('stock_pool', 'N/A')}\")
    print(f\"初始资金: {config.get('capital', {}).get('initial_capital', 'N/A')}\")
"
```

---

## 10. 参考资源

- [Tushare Pro文档](https://tushare.pro/document/2)
- [AkShare文档](https://akshare.akfamily.xyz/)
- [A股交易规则说明](https://www.sse.com.cn/)
- [项目完整文档](../docs/README_ASTOCK.md)
- [快速开始指南](../docs/ASTOCK_QUICKSTART.md)

---

**最后更新**: 2024年12月
**维护者**: AI-Trader Team
