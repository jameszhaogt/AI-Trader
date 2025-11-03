# 回测结果目录

此目录用于存储AI-Trader回测引擎生成的回测报告。

## 目录结构

```
backtest_results/
├── {回测名称}_{时间戳}/
│   ├── trades.jsonl              # 交易明细
│   ├── daily_positions.jsonl     # 每日持仓记录
│   ├── metrics.json              # 绩效指标
│   ├── portfolio_value.png       # 资金曲线图
│   ├── drawdown.png             # 回撤曲线图
│   ├── positions_distribution.png # 持仓分布图
│   ├── trades_timeline.png      # 交易时间线图
│   └── report.html              # HTML综合报告
└── README.md                     # 本文件
```

## 数据文件说明

### 1. trades.jsonl
交易明细，每行一条交易记录，包含：
- `date`: 交易日期
- `symbol`: 股票代码
- `action`: 操作类型（buy/sell）
- `shares`: 股数
- `price`: 成交价格
- `cost`: 交易成本（佣金+滑点+印花税）
- `total`: 交易总额

示例：
```json
{
  "date": "2024-01-15",
  "symbol": "600519.SH",
  "action": "buy",
  "shares": 100,
  "price": 1688.50,
  "cost": 168.85,
  "total": 169018.85
}
```

### 2. daily_positions.jsonl
每日持仓记录，每行一天的持仓快照：
- `date`: 日期
- `cash`: 现金余额
- `positions`: 股票持仓 {symbol: shares}
- `portfolio_value`: 组合总价值
- `daily_return`: 当日收益率

示例：
```json
{
  "date": "2024-01-15",
  "cash": 50000.00,
  "positions": {
    "600519.SH": 100,
    "000858.SZ": 200
  },
  "portfolio_value": 250000.00,
  "daily_return": 0.0125
}
```

### 3. metrics.json
回测绩效指标：
- `total_return`: 总收益率 (%)
- `annual_return`: 年化收益率 (%)
- `max_drawdown`: 最大回撤 (%)
- `sharpe_ratio`: 夏普比率
- `win_rate`: 胜率 (%)
- `total_trades`: 总交易次数
- `trading_days`: 交易天数
- `start_date`: 回测开始日期
- `end_date`: 回测结束日期
- `initial_capital`: 初始资金
- `final_value`: 最终价值

示例：
```json
{
  "total_return": 45.23,
  "annual_return": 52.18,
  "max_drawdown": -12.45,
  "sharpe_ratio": 1.85,
  "win_rate": 62.5,
  "total_trades": 48,
  "trading_days": 242,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000.00,
  "final_value": 145230.00
}
```

## 可视化报告

### 图表说明

1. **portfolio_value.png** - 资金曲线图
   - 展示组合价值随时间的变化
   - 包含初始资金基准线

2. **drawdown.png** - 回撤曲线图
   - 展示回撤随时间的变化
   - 标注最大回撤点

3. **positions_distribution.png** - 持仓分布饼图
   - 展示最终持仓的股票分布

4. **trades_timeline.png** - 交易时间线图
   - 绿色三角形：买入点
   - 红色倒三角形：卖出点

### HTML报告

`report.html` 是一个综合性的可视化报告，包含：
- 所有关键绩效指标
- 所有图表的集成展示
- 响应式设计，支持移动端查看

## 使用方法

### 生成回测报告

```python
from tools.backtest_engine import BacktestEngine

# 创建回测引擎
engine = BacktestEngine(config_path="configs/backtest_config.json")

# 运行回测
results = engine.run()

# 生成报告
report_path = engine.generate_report(output_name="my_strategy")
print(f"报告已生成: {report_path}")
```

### 生成可视化图表

```python
from tools.backtest_visualizer import BacktestVisualizer

# 创建可视化器
visualizer = BacktestVisualizer("data/backtest_results/my_strategy_20240101")

# 生成完整报告
visualizer.generate_full_report()
```

### 命令行生成报告

```bash
python tools/backtest_visualizer.py --results_dir data/backtest_results/my_strategy_20240101
```

## 注意事项

1. **目录命名规范**：建议使用 `{策略名}_{日期}` 格式命名回测结果目录
2. **数据保留**：回测结果会永久保存，定期清理过期数据以节省空间
3. **HTML报告**：可直接用浏览器打开 report.html 查看完整报告
4. **图表格式**：所有图表默认保存为PNG格式，分辨率300dpi

## 性能指标说明

### 总收益率 (Total Return)
```
总收益率 = (最终价值 - 初始资金) / 初始资金 × 100%
```

### 年化收益率 (Annual Return)
```
年化收益率 = (1 + 总收益率) ^ (252 / 交易天数) - 1
```

### 最大回撤 (Max Drawdown)
```
最大回撤 = min((当前价值 - 历史最高价值) / 历史最高价值) × 100%
```

### 夏普比率 (Sharpe Ratio)
```
夏普比率 = (年化收益率 - 无风险利率) / 收益波动率
```
注：无风险利率默认为3%，收益波动率为日收益率标准差的年化值

### 胜率 (Win Rate)
```
胜率 = 盈利交易次数 / 总交易次数 × 100%
```

## 示例报告查看

访问生成的HTML报告即可查看完整的回测分析：

```bash
# 在浏览器中打开
open data/backtest_results/my_strategy_20240101/report.html

# 或使用Python服务器
cd data/backtest_results/my_strategy_20240101
python -m http.server 8080
# 然后访问 http://localhost:8080/report.html
```

## 常见问题

**Q: 如何比较多个策略的回测结果？**  
A: 可以编写脚本读取多个 metrics.json 文件，生成对比报告。

**Q: 为什么回撤曲线总是负值？**  
A: 回撤定义为相对历史最高点的下跌幅度，因此总是 ≤ 0。

**Q: 如何导出数据到Excel？**  
A: 可以使用pandas读取jsonl文件并导出：
```python
import pandas as pd
df = pd.read_json('trades.jsonl', lines=True)
df.to_excel('trades.xlsx', index=False)
```

---

更多信息请参考项目主文档：[AI-Trader README](../../README.md)
