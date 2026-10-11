# atom-ifind-stock-fundamental（iFinD股票基本面查询）

**层级**: Atomic
**ID**: atom-ifind-stock-fundamental
**触发**: 需要查询A股个股的基本资料、财务数据、股本股东、ESG评级等基本面信息时
**来源**: iFinD MCP stock模块（2026-09-12新增），基本面分析工具集合

---

## 工具能力概述

覆盖iFinD stock-mcp中所有基本面类工具：

| 工具 | 能力 | 典型场景 |
|------|------|----------|
| `mcp__hexin-ifind-ds-stock-mcp__get_stock_info` | 证券基本信息 + 上市公司基本资料（上市发行信息、行业分类、工商信息、主营业务简介、是否属重要标的） | 快速了解公司基本情况 |
| `mcp__hexin-ifind-ds-stock-mcp__get_stock_financials` | 财务报表原始数据（资产负债/收入利润）+ 财务分析指标（偿债/盈利/成长/风险/规模/杠杆，如ROE/资产负债率）+ 估值类指标（PE/PB/PS/企业价值倍数+分位数） | 财务健康度分析、估值对比 |
| `mcp__hexin-ifind-ds-stock-mcp__get_stock_shareholders` | 股本结构（总股本/自由流通股本/AB股/限售解禁/海外股本占比）+ 股东数据（前n大股东/机构持股/各类型股东数量及比例） | 股东分析、解禁压力评估 |
| `mcp__hexin-ifind-ds-stock-mcp__get_esg_data` | ESG评级与报告数据 | ESG投资筛选 |

## 输入要求 / 参数规范

### 通用参数模式
- **query**: 自然语言格式，要求包含：证券实体 + 指标名称 + 日期（如适用）
- **日期格式**: 财务/报告期类数据使用报告期格式，如 `2025-12-31` 表示年报、`2025-06-30` 表示半年报
- **估值分位数**: get_stock_financials 返回PE/PB等指标的历史分位数，可直接判断估值高低

### 各工具要点
- **get_stock_info**: 轻量查询，适合快速了解公司行业/主营/上市时间
- **get_stock_financials**: 核心财务分析工具，单只股票的深度基本面分析首选
- **get_stock_shareholders**: 注意区分"流通股占比"和"前n大股东持股占比"
- **get_esg_data**: 评级机构为中诚信或其他第三方，需在query中明确评级机构（如"中诚信ESG评级"）

## 输出格式说明
- 自然语言描述的结构化查询结果
- 财务指标为报告期维度，不是实时数据
- 估值分位数是相对历史区间的百分位（0-100），数值越高估值越贵

## 常见坑与避错指南

1. **报告期 vs 自然日🔴**：财务数据用报告期格式（2025-06-30=半年报），不是交易日，不要和K线日期混淆
2. **PE口径混淆🟡**：PE有TTM（滚动12月）和静态（年报）之分，stock_highfreq_quotes里的PE是TTM，get_stock_financials里需明确口径
3. **流通股本口径🟡**：自由流通股本 ≠ 流通A股，前者剔除了大股东锁定等，计算换手率要用自由流通股本
4. **ESG评级机构差异🟡**：不同机构评级标准不同，比较时需同一机构
5. **财务数据延迟🟢**：年报通常4月底前披露，季报1个月内，注意时效性

## 适用边界（什么情况不用）

- ❌ 港股/美股基本面 → 用stock-data-skill或web_search
- ❌ 实时行情/技术指标 → 用 atom-ifind-stock-kline
- ❌ 公司公告/新闻 → 用 atom-ifind-news-notice
- ❌ 行业/板块整体财务 → 用 index-mcp sector_data 或 web_search
- ❌ 基金基本面 → 用 atom-ifind-fund-analysis

---

## 为什么重要

基本面分析是量化选股的重要补充维度。iFinD MCP提供了比腾讯/akshare更全面、更结构化的财务数据，尤其是估值分位数和财务分析指标（ROE/负债率等），可以直接用于选股评分和风险评估。
