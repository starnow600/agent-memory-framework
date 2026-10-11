# atom-ifind-fund-analysis（iFinD基金分析全套工具）

**层级**: Atomic
**ID**: atom-ifind-fund-analysis
**触发**: 需要筛选基金、查询基金基本资料、业绩表现、持仓明细、基金公司信息等时
**来源**: iFinD MCP fund模块（2026-09-12新增），基金分析工具集合

---

## 工具能力概述

覆盖iFinD fund-mcp全部8个工具：

| 工具 | 能力 | 典型场景 |
|------|------|----------|
| `mcp__hexin-ifind-ds-fund-mcp__search_funds` | 智能选基：按行情表现/业绩指标/持仓分布/基金管理人等条件筛选 | 找符合条件的基金 |
| `mcp__hexin-ifind-ds-fund-mcp__get_fund_profile` | 基金基本资料：名称/代码/分类/费率/发行信息 | 了解基金基本情况 |
| `mcp__hexin-ifind-ds-fund-mcp__get_fund_market_performance` | 基金行情/业绩/绩效评价：净值/收益率/溢价率/同类排名/alpha/beta/夏普 | 基金业绩评估 |
| `mcp__hexin-ifind-ds-fund-mcp__get_fund_ownership` | 基金份额与持有人结构：当前份额/申赎/持有人数量/各类持有人占比 | 资金流分析 |
| `mcp__hexin-ifind-ds-fund-mcp__get_fund_portfolio` | 投资组合与持仓明细：大类资产配置/行业分布/前n大持股/持债 | 持仓分析 |
| `mcp__hexin-ifind-ds-fund-mcp__get_fund_financials` | 基金财务数据（季报披露） | 基金利润/资产分析 |
| `mcp__hexin-ifind-ds-fund-mcp__get_fund_company_info` | 基金公司维度：公司信息/基金经理数量/资管规模/旗下基金/业绩绩效 | 选基金公司 |
| `mcp__hexin-ifind-ds-fund-mcp__fund_highfreq_quotes` | 基金实时行情：最新价/IOPV净值估值/振幅/折价 | 盘中ETF/LOF实时监控 |

## 输入要求 / 参数规范

### 通用规范
- **query**: 自然语言，包含基金实体 + 查询信息
- **日期格式**:
  - 行情/业绩类：用 `YYYYMMDD-YYYYMMDD` 起止日期，避免相对日期
  - 持仓/财报类：用报告期格式 `2025-06-30`（季报/半年报/年报披露）

### 各工具要点
- **search_funds**: 条件越具体结果越精准，避免模糊描述
- **get_fund_portfolio**: 持仓明细为季报披露，有滞后性（季报结束后15个工作日内披露）
- **fund_highfreq_quotes**:
  - symbols支持同花顺代码（如`000307.OF`）/六位代码/简称，上限10只
  - data_mode: real_time / highfreq
  - 仅实时模式支持IOPV净值估值、折价等指标

## 输出格式说明
- 自然语言描述的结构化查询结果
- 持仓/财务数据为报告期维度，不是实时数据
- 业绩评价指标（alpha/beta/夏普）基于历史净值计算

## 常见坑与避错指南

1. **基金代码后缀🔴**：基金代码用`.OF`后缀区分于股票，如`000307.OF`
2. **持仓数据滞后性🟡**：季报披露有15个工作日延迟，用持仓数据时注意时效性
3. **ETF折溢价🟡**：fund_highfreq_quotes可查实时折价/溢价，ETF交易需关注
4. **A类/C类份额混淆🟡**：同一只基金不同份额费率不同，业绩表现也有差异
5. **同类排名基准🟢**：业绩排名的"同类"定义很重要，股票型vs混合型排名不可比

## 适用边界（什么情况不用）

- ❌ 个股分析 → 用 stock-mcp 系列
- ❌ 指数行情 → 用 index-mcp 系列
- ❌ 公募基金以外的产品（私募/信托等）→ 不覆盖
- ❌ 基金经理个人深度研究 → 需结合web_search补充

---

## 为什么重要

基金分析是投资分析的重要组成部分——无论是选基金、分析基金持仓、还是通过基金持仓反向推断机构动向，都需要基金数据。iFinD MCP fund模块提供了完整的基金分析工具链，覆盖从选基到持仓到业绩评估的全流程。
