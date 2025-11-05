# Tushare 切换为 AkShare 迁移文档

## 概述

本次迁移将项目的数据源从 Tushare 完全切换为 AkShare。AkShare 是完全免费的开源金融数据接口库,无需API Token即可使用。

## 修改文件列表

### 1. 依赖文件
- **文件**: `requirements.txt`
- **变更**: 移除 `tushare>=1.2.89`,仅保留 `akshare>=1.11.0`

### 2. 数据获取模块
- **文件**: `data/get_astock_data.py`
- **主要变更**:
  - 移除 `import tushare as ts`
  - 使用 `ak.index_stock_cons_csindex()` 获取沪深300/科创50成分股
  - 使用 `ak.stock_info_a_code_name()` 获取全部A股列表
  - 使用 `ak.stock_zh_a_hist()` 获取历史日线数据(支持前复权/后复权)
  - 使用 `ak.stock_individual_info_em()` 获取个股行业信息
  
### 3. 共识数据模块
- **文件**: `data/get_consensus_data.py`
- **主要变更**:
  - 移除 Tushare 相关代码和 `TUSHARE_AVAILABLE` 标志
  - 移除 `_fetch_northbound_tushare()` 等 Tushare 方法
  - 统一使用 AkShare 获取:
    - 北向资金: `ak.stock_hsgt_individual_em()`
    - 融资融券: `ak.stock_margin_detail_em()`
    - 券商评级: `ak.stock_rating_all()`
    - 行业热度: `ak.stock_board_industry_name_em()`

### 4. MCP工具接口
- **文件**: `agent_tools/tool_get_consensus.py`
- **主要变更**:
  - 函数参数 `tushare_token` 标记为废弃参数(保持API兼容性)
  - 更新文档注释,移除 Tushare 相关说明
  - 创建 `ConsensusDataFetcher` 时不再传递 token

### 5. 测试文件
- **文件**: `tests/test_astock_data.py`
- **主要变更**:
  - 移除 `TUSHARE_TOKEN` 环境变量检查
  - 直接使用 `import akshare as ak` 初始化
  - 测试用例需要根据实际的AkShare API调整

## API 映射关系

| 功能 | Tushare API | AkShare API |
|------|------------|-------------|
| 沪深300成分股 | `pro.index_weight('000300.SH')` | `ak.index_stock_cons_csindex('000300')` |
| 科创50成分股 | `pro.index_weight('000688.SH')` | `ak.index_stock_cons_csindex('000688')` |
| 全部A股列表 | `pro.stock_basic()` | `ak.stock_info_a_code_name()` |
| 日线数据(前复权) | `ts.pro_bar(adj='qfq')` | `ak.stock_zh_a_hist(adjust='qfq')` |
| 北向资金 | `pro.hk_hold()` | `ak.stock_hsgt_individual_em()` |
| 融资融券 | `pro.margin_detail()` | `ak.stock_margin_detail_em()` |
| 券商评级 | `pro.stk_rating()` | `ak.stock_rating_all()` |
| 行业数据 | `pro.ths_index()` | `ak.stock_board_industry_name_em()` |
| 交易日历 | `pro.trade_cal()` | `ak.tool_trade_date_hist_sina()` |

## 数据字段映射

### 日线数据字段映射
| Tushare字段 | AkShare字段 |
|------------|-----------|
| trade_date | 日期 |
| open | 开盘 |
| close | 收盘 |
| high | 最高 |
| low | 最低 |
| vol | 成交量 |
| amount | 成交额 |
| pre_close | 昨收 |

## 环境变量变更

### 移除
- `TUSHARE_TOKEN` - 不再需要

### 保留
- `ALPHAADVANTAGE_API_KEY` - 如果使用Alpha Vantage
- `JINA_API_KEY` - 搜索功能
- 其他业务相关环境变量

## 数据差异说明

### 1. 停牌数据
- **Tushare**: 提供专门的 `suspend_d` 接口获取停牌信息
- **AkShare**: 通过成交量为0判断停牌

### 2. 上市日期
- **Tushare**: 直接提供 `list_date` 字段
- **AkShare**: 基础接口不提供,需要额外查询或设为空

### 3. 交易日历
- **Tushare**: 提供完整交易日历
- **AkShare**: 提供交易日历,但接口略有不同

### 4. 北向资金
- **Tushare**: 提供持股数量变化
- **AkShare**: 提供买入/卖出/净流入金额,数据更详细

### 5. 券商评级
- **Tushare**: 按股票查询评级历史
- **AkShare**: 提供全市场评级数据,需自行筛选

## 优势对比

### AkShare 优势
1. **完全免费**: 无需注册、无需Token
2. **无积分限制**: Tushare高级数据需要积分
3. **开源透明**: 代码完全开源
4. **数据丰富**: 覆盖A股、港股、期货等多个市场
5. **更新及时**: 社区活跃,问题响应快

### 注意事项
1. **数据延迟**: AkShare数据可能有1-2天延迟
2. **稳定性**: 依赖第三方网站,可能受网站维护影响
3. **字段差异**: 部分字段名称和格式与Tushare不同,需要适配

## 迁移步骤

1. **更新依赖**
   ```bash
   pip uninstall tushare
   pip install -r requirements.txt
   ```

2. **移除环境变量**
   编辑 `.env` 文件,删除或注释 `TUSHARE_TOKEN` 相关配置

3. **测试验证**
   ```bash
   # 测试数据获取
   python data/get_astock_data.py
   
   # 测试共识数据
   python data/get_consensus_data.py
   
   # 运行单元测试
   python tests/run_tests.py
   ```

4. **数据更新**
   ```bash
   # 重新下载股票列表
   python data/get_astock_data.py
   ```

## 常见问题

### Q: 为什么切换到 AkShare?
A: AkShare完全免费且无需API Token,降低了使用门槛。Tushare的高级数据需要积分,对新用户不友好。

### Q: 数据质量有保证吗?
A: AkShare从多个公开数据源获取数据,质量可靠。适合个人研究和小型项目。如需更专业的数据服务,可考虑付费数据源。

### Q: 原有代码兼容性如何?
A: 保持了API接口兼容性,`tushare_token` 参数仍然存在但已废弃。调用方无需修改代码。

### Q: 如果 AkShare 不可用怎么办?
A: 代码中保留了错误处理机制,数据缺失时返回 null 而不是抛出异常,不影响系统其他功能运行。

## 回退方案

如需回退到 Tushare:

1. 恢复 `requirements.txt`:
   ```
   tushare>=1.2.89
   akshare>=1.11.0
   ```

2. 恢复代码使用 Git:
   ```bash
   git checkout HEAD -- data/get_astock_data.py
   git checkout HEAD -- data/get_consensus_data.py
   ```

3. 配置 `.env`:
   ```
   TUSHARE_TOKEN=your_token_here
   ```

## 测试清单

- [ ] 股票列表获取 (沪深300/科创50/全部)
- [ ] 日线数据下载 (前复权/后复权)
- [ ] ST股票识别
- [ ] 停牌日处理
- [ ] 北向资金查询
- [ ] 融资融券数据
- [ ] 券商评级获取
- [ ] 行业热度排名
- [ ] 数据质量校验
- [ ] 回测功能验证

## 更新日志

### 2025-11-05
- 完成 Tushare 到 AkShare 的完整迁移
- 更新所有数据获取接口
- 保持 API 向后兼容性
- 文档更新

---

**注意**: 本迁移已完成核心功能切换,建议在生产环境使用前进行充分测试。
