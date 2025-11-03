# A股市场适配 - 5分钟快速开始

本指南帮助您在5分钟内完成A股市场适配方案的环境配置和首次回测。

---

## 🚀 第1步: 环境准备 (2分钟)

### 1.1 安装Python依赖

```bash
# 确保Python版本 >= 3.8
python --version

# 安装必需的包
pip install tushare akshare pandas pytest

# 可选:安装其他依赖
pip install -r requirements.txt
```

### 1.2 配置API密钥

创建 `.env` 文件(项目根目录):

```bash
# 方式1: 使用echo命令
echo "TUSHARE_TOKEN=your_tushare_token_here" > .env

# 方式2: 手动创建
# 用编辑器打开.env文件,添加以下内容:
```

`.env` 文件内容:
```ini
# Tushare Pro API Token (必需)
TUSHARE_TOKEN=your_token_here

# 可选:其他配置
AKSHARE_TOKEN=
OPENAI_API_KEY=
```

**获取Tushare Token**:
1. 注册: https://tushare.pro/register
2. 完成基础积分任务(建议积分≥500)
3. 在个人中心复制Token

---

## 📝 第2步: 生成测试数据 (1分钟)

```bash
# 进入测试目录
cd tests

# 运行数据生成脚本
python generate_test_data.py

# 验证生成的文件
ls test_data/
# 应该看到:
# - astock_list_sample.json
# - merged_sample.jsonl
# - consensus_sample.jsonl
```

---

## 🧪 第3步: 运行测试 (1分钟)

```bash
# 回到项目根目录
cd ..

# 运行交易规则测试
pytest tests/test_trading_rules.py -v

# 运行共识分数测试
pytest tests/test_consensus_score.py -v

# 运行所有测试
pytest tests/ -v
```

**预期输出**:
```
tests/test_trading_rules.py::test_t1_rule PASSED
tests/test_trading_rules.py::test_limit_price PASSED
tests/test_trading_rules.py::test_min_unit PASSED
...
==================== X passed in Xs ====================
```

---

## 🎯 第4步: 执行首次回测 (1分钟)

### 4.1 选择策略配置

我们提供3种预设策略:

| 配置文件 | 策略类型 | 风险 | 适合人群 |
|---------|---------|------|---------|
| `astock_conservative.json` | 沪深300稳健 | 低 | 保守投资者 |
| `astock_aggressive.json` | 科创50进取 | 高 | 激进投资者 |
| `astock_custom_stocks.json` | 自选股 | 中 | 专业投资者 |

### 4.2 运行回测

```bash
# 使用沪深300稳健策略
python main.py --config configs/astock_conservative.json

# 或使用科创50进取策略
python main.py --config configs/astock_aggressive.json
```

### 4.3 查看回测结果

回测完成后,查看生成的报告:

```bash
# 查看绩效报告
cat reports/astock_conservative_report.json

# 查看日志
tail -f logs/astock_conservative.log
```

**预期输出示例**:
```json
{
  "total_return": 15.3,
  "annual_return": 15.8,
  "max_drawdown": 8.2,
  "sharpe_ratio": 1.85,
  "win_rate": 62.5,
  "total_trades": 48
}
```

---

## ✅ 完成!

恭喜!您已经成功完成A股市场适配方案的快速启动。

---

## 📚 下一步学习

### 初级 (1-2天)
1. **理解配置文件**: 阅读 [配置指南](docs/ASTOCK_CONFIG_GUIDE.md)
2. **修改策略参数**: 调整止损/止盈、持仓数量等
3. **查看测试用例**: 学习如何编写和运行测试

### 中级 (3-5天)
1. **实现数据获取**: 填充 `get_astock_data.py` 中的TODO函数
2. **开发自定义策略**: 编写自己的选股和交易逻辑
3. **优化共识筛选**: 调整4维度权重和评分标准

### 高级 (1-2周)
1. **性能优化**: 提升回测速度,支持更大股票池
2. **实盘对接**: 连接券商API进行实盘交易
3. **机器学习**: 使用ML模型优化选股和择时

---

## 🔧 常见问题

### Q1: 运行pytest时报错"No module named 'tushare'"?
A: 执行 `pip install tushare akshare pandas`

### Q2: Tushare Token无效?
A: 检查 `.env` 文件格式,确保没有多余的空格或引号

### Q3: 测试数据不存在?
A: 先运行 `cd tests && python generate_test_data.py`

### Q4: 回测失败,提示"数据文件不存在"?
A: 这是正常的,因为真实数据需要调用API获取。当前测试数据仅用于单元测试。

### Q5: 如何切换数据源为AkShare?
A: 修改配置文件中的 `data_source.provider` 为 `"akshare"`

---

## 📞 获取帮助

- **文档**: 查看 [docs/](docs/) 目录下的完整文档
- **示例**: 参考 [examples/](examples/) 目录的示例代码
- **测试**: 查看 [tests/](tests/) 目录学习如何测试

---

## 🎉 快速命令备忘单

```bash
# 安装依赖
pip install tushare akshare pandas pytest

# 配置环境
echo "TUSHARE_TOKEN=your_token" > .env

# 生成测试数据
cd tests && python generate_test_data.py && cd ..

# 运行测试
pytest tests/ -v

# 执行回测(稳健策略)
python main.py --config configs/astock_conservative.json

# 执行回测(进取策略)
python main.py --config configs/astock_aggressive.json

# 查看结果
cat reports/astock_conservative_report.json
```

---

**祝您使用愉快!** 🎊

*如有问题,请查看完整文档或提交Issue*
