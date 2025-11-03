# A股市场适配 - 快速开始指南

## 📋 概述

本项目为AI-Trader系统增加A股市场支持,包括数据源适配、交易规则实现、共识筛选系统和历史回测功能。

**当前状态**: 
- ✅ 阶段0已完成 (设计缺陷修复)
- 📋 阶段1-4待执行 (开发、测试、优化)

**预计完成时间**: 9.5个工作日

---

## 🚀 快速开始

### 1. 查看核心文档(5分钟)

```bash
# 设计缺陷修复方案 - 必读!
cat docs/DESIGN_DEFECTS_FIX.md

# 实施路线图 - 了解开发计划
cat docs/ASTOCK_IMPLEMENTATION_ROADMAP.md

# 执行总结 - 了解已完成工作
cat docs/ASTOCK_ADAPTATION_SUMMARY.md

# 任务清单 - 跟踪开发进度
cat docs/TASK_CHECKLIST.md
```

### 2. 环境准备(10分钟)

```bash
# 1. 安装依赖
pip install tushare akshare pandas numpy pytest pytest-cov pytest-mock

# 2. 配置环境变量
cp .env.example .env

# 编辑 .env 文件,填入:
# TUSHARE_TOKEN=你的tushare_token
# OPENAI_API_KEY=你的openai_key

# 3. 验证配置
python -c "import tushare as ts; pro = ts.pro_api()"
```

### 3. 理解核心设计(15分钟)

#### 四大设计缺陷修复

| 缺陷 | 修复方案 | 代码位置 |
|------|---------|---------|
| **D1: 涨跌停精度** | `round(price * 1.1, 2)` 精确到分 | DESIGN_DEFECTS_FIX.md §1 |
| **D2: ST识别** | 通过名称前缀识别,增加`is_st`字段 | DESIGN_DEFECTS_FIX.md §2 |
| **D3: 数据缺失** | 缺失维度记0分,不抛异常 | DESIGN_DEFECTS_FIX.md §3 |
| **D4: 停牌处理** | 使用前收盘价填充,增加`status`字段 | DESIGN_DEFECTS_FIX.md §4 |

#### 数据结构

```
data/
├── astock_list.json          # 股票列表(含is_st字段)
├── merged.jsonl              # 行情数据(含status字段)
└── consensus_data.jsonl      # 共识数据(缺失为null)
```

#### 核心功能

```
数据层 → 工具层 → 回测层
  ↓        ↓        ↓
获取数据  交易规则  历史模拟
  ↓        ↓        ↓
停牌处理  共识筛选  绩效分析
```

---

## 📊 开发阶段

### 阶段1: 基础适配 (3天)

**核心任务**:
- [ ] 创建 `data/get_astock_data.py` (数据下载)
- [ ] 修改 `agent_tools/tool_get_price_local.py` (价格查询)
- [ ] 修改 `agent_tools/tool_trade.py` (交易规则)
- [ ] 修改提示词和配置

**验收**: 可下载10只股票数据,UT-TR测试全通过

### 阶段2: 共识系统 (2天)

**核心任务**:
- [ ] 创建 `data/get_consensus_data.py` (共识数据)
- [ ] 创建 `agent_tools/tool_consensus_filter.py` (筛选逻辑)

**验收**: 可筛选高共识股票,UT-CS测试全通过

### 阶段3: 回测系统 (2天)

**核心任务**:
- [ ] 创建 `tools/backtest_engine.py` (回测引擎)
- [ ] 创建 `agent/backtest_agent.py` (回测Agent)

**验收**: 可执行全年回测,生成HTML报告

### 阶段4: 测试优化 (2天)

**核心任务**:
- [ ] 边界测试、集成测试、性能测试
- [ ] 兼容性测试、安全测试
- [ ] 文档完善

**验收**: 所有测试通过,代码覆盖率≥80%

---

## 🧪 测试用例

### 单元测试
```bash
# 交易规则测试(UT-TR系列,9个用例)
pytest tests/unit/test_trade_rules.py -v

# 共识分数测试(UT-CS系列,5个用例)
pytest tests/unit/test_consensus_score.py -v

# 时间旅行测试(UT-TT系列,4个用例)
pytest tests/unit/test_time_travel.py -v
```

### 集成测试
```bash
# 完整交易流程(IT-TF系列,4个用例)
pytest tests/integration/test_trade_flow.py -v

# 共识筛选流程(IT-CF系列,3个用例)
pytest tests/integration/test_consensus_filter.py -v
```

### 回测测试
```bash
# 准确性验证(BT-ACC系列,2个用例)
pytest tests/backtest/test_backtest_accuracy.py -v

# 数据处理(BT-DATA系列,3个用例)
pytest tests/backtest/test_backtest_data.py -v

# 绩效指标(BT-METRIC系列,3个用例)
pytest tests/backtest/test_backtest_metrics.py -v
```

**详细测试代码**: 参见 `docs/TEST_IMPLEMENTATION.md`

---

## 📁 文档导航

| 文档 | 描述 | 用途 |
|------|------|------|
| **DESIGN_DEFECTS_FIX.md** | 设计缺陷修复方案 | 了解4个高优先级缺陷的详细修复方案 |
| **TEST_IMPLEMENTATION.md** | 测试用例实现 | 获取完整的pytest测试代码 |
| **ASTOCK_IMPLEMENTATION_ROADMAP.md** | 实施路线图 | 查看详细的开发计划和时间安排 |
| **ASTOCK_ADAPTATION_SUMMARY.md** | 执行总结报告 | 了解项目概况和已完成工作 |
| **TASK_CHECKLIST.md** | 任务执行清单 | 跟踪开发进度 |

---

## 🔑 关键代码示例

### 涨跌停价格计算

```python
def calculate_limit_prices(symbol: str, prev_close: float, is_st: bool = False) -> dict:
    """计算涨跌停价格(精确到分)"""
    if symbol.startswith("688") or symbol.startswith("300"):
        limit_ratio = 1.20  # 科创板/创业板 ±20%
    elif is_st:
        limit_ratio = 1.05  # ST股票 ±5%
    else:
        limit_ratio = 1.10  # 主板 ±10%
    
    return {
        "limit_up": round(prev_close * limit_ratio, 2),
        "limit_down": round(prev_close * (2 - limit_ratio), 2)
    }
```

### ST股票识别

```python
def identify_st_stock(stock_name: str) -> bool:
    """判断是否为ST股票"""
    name = stock_name.strip()
    st_prefixes = ["ST", "*ST", "SST", "S*ST"]
    return any(name.startswith(prefix) for prefix in st_prefixes)
```

### 共识分数计算(含缺失处理)

```python
def calculate_consensus_score(symbol: str, date: str) -> dict:
    """计算共识分数,缺失维度记0分"""
    technical = calculate_technical_score(symbol, date)  # 0-20分,缺失返回0
    fund = calculate_fund_score(symbol, date)            # 0-30分,子项缺失返回0
    logic = calculate_logic_score(symbol, date)          # 0-30分,子项缺失返回0
    sentiment = calculate_sentiment_score(symbol, date)  # 0-20分,缺失返回0
    
    total = technical + fund + logic + sentiment
    missing_data = [维度 for 维度 in [技术,资金,逻辑,情绪] if 分数==0]
    
    return {
        "total_score": total,
        "missing_data": missing_data,
        "data_completeness": 1.0 - (len(missing_data) / 4.0)
    }
```

### 时间旅行验证

```python
def get_price_data(self, symbol: str, date: datetime) -> dict:
    """获取价格数据(禁止访问未来数据)"""
    if date > self.current_date:
        raise TimeViolationError(f"禁止访问未来数据: {date} > {self.current_date}")
    return self.data_cache.get(f"{symbol}_{date}")
```

---

## ⚠️ 注意事项

### 1. API限流处理
- Tushare Pro免费用户: 120次/分钟
- 建议每次调用后 `time.sleep(0.5)`
- 备用方案: 切换到AkShare

### 2. 数据质量检查
- 价格异常: 涨跌幅>50%需人工确认
- 停牌日处理: 必须使用前收盘价填充
- ST识别: 通过股票名称前缀判断

### 3. 测试覆盖率
- 目标: ≥80%
- 每完成一个模块立即测试
- 修改代码后重新执行相关测试

### 4. 安全性
- `.env`文件绝不提交到git
- 检查命令: `git status .env` (应提示未追踪)
- 日志中不输出敏感信息

---

## 📞 问题反馈

### 遇到问题?

1. **查看文档**: 优先查阅 `docs/DESIGN_DEFECTS_FIX.md` 中的FAQ
2. **查看示例**: 参考 `docs/TEST_IMPLEMENTATION.md` 中的测试代码
3. **查看清单**: 检查 `docs/TASK_CHECKLIST.md` 确认未遗漏任务

### 常见问题

| 问题 | 解决方案 | 文档位置 |
|------|---------|---------|
| Tushare API限流 | 降低调用频率或切换AkShare | DESIGN_DEFECTS_FIX.md §FAQ |
| 停牌日数据缺失 | 使用前收盘价填充,status=suspended | DESIGN_DEFECTS_FIX.md §4 |
| ST股票识别错误 | 检查名称前缀是否包含ST | DESIGN_DEFECTS_FIX.md §2 |
| 共识数据缺失报错 | 应返回null而非抛异常 | DESIGN_DEFECTS_FIX.md §3 |

---

## 📈 进度跟踪

### 当前进度
```
✅ 阶段0: 前置准备 (100%)
📋 阶段1: 基础适配 (0%)
📋 阶段2: 共识系统 (0%)
📋 阶段3: 回测系统 (0%)
📋 阶段4: 测试优化 (0%)

总计: 5/29 任务完成 (17%)
```

### 下一步行动
1. ✅ 阅读核心文档(本文档)
2. ✅ 环境准备(安装依赖、配置.env)
3. 📋 开始阶段1开发
4. 📋 执行阶段1测试
5. 📋 继续后续阶段...

---

## 🎯 验收标准

### 最终验收清单
- [ ] 所有单元测试通过 (UT-TR + UT-CS + UT-TT = 18个)
- [ ] 所有集成测试通过 (IT-TF + IT-CF = 7个)
- [ ] 所有回测测试通过 (BT系列 = 8个)
- [ ] 边界测试通过率 ≥ 85%
- [ ] 代码覆盖率 ≥ 80%
- [ ] 全年回测耗时 < 10分钟
- [ ] NASDAQ市场功能未受影响
- [ ] 文档完整(API文档、用户指南、测试报告)

---

## 📚 参考资源

### 外部资源
- [Tushare Pro文档](https://tushare.pro/document/2)
- [AkShare文档](https://akshare.akfamily.xyz/)
- [Pytest文档](https://docs.pytest.org/)

### 项目文档
- 设计文档: `docs/DESIGN_DEFECTS_FIX.md`
- 测试文档: `docs/TEST_IMPLEMENTATION.md`
- 路线图: `docs/ASTOCK_IMPLEMENTATION_ROADMAP.md`
- 总结报告: `docs/ASTOCK_ADAPTATION_SUMMARY.md`
- 任务清单: `docs/TASK_CHECKLIST.md`

---

**开始时间**: 待定  
**预计完成**: 开始后9.5个工作日  
**当前状态**: 阶段0已完成,等待启动 ✅

**祝开发顺利! 🚀**
