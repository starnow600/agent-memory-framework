# atom-agentkey-finance-data（AgentKey金融数据补充）

**层级**: Atomic
**ID**: atom-agentkey-finance-data
**触发**: iFinD 覆盖不足的金融数据场景：美股/港股/全球市场/另类数据/技术指标补充；需要与iFinD数据交叉验证时
**来源**: 2026-09-12_AgentKey_MCP接入，金融类工具实测（4家、311工具）

---

## 工具能力概述

AgentKey 金融类覆盖 4 家数据供应商、311 个工具，作为 iFinD MCP（A股主力）的补充。按 credits 计费。

### 覆盖的金融数据源

| 供应商 | 工具数 | 核心能力 | 优势领域 |
|--------|--------|----------|----------|
| Alpha Vantage | 114 | 技术指标（50+）/商品/汇率/全球股票 | 技术指标丰富、全球覆盖 |
| Finnhub | 33 | 美股基本面/新闻/财报/内幕交易/分析师评级 | 美股基本面、实时新闻 |
| Tushare | 155 | A股全量数据（行情/财务/基本面/债券/基金） | A股数据全、本土优势 |
| yfinance | 9 | 雅虎财经数据（全球股票/指数/基金） | 全球市场覆盖广、免费API封装 |

### 调用三步法
1. `mcp__agentkey__find_tools(q="美股+财务" 或 prefix="finance/")`
2. `mcp__agentkey__describe_tool(name="<工具名>")` — 查参数+成本
3. `mcp__agentkey__execute_tool(...)` — 执行

## 输入要求 / 参数规范

### Alpha Vantage
- 技术指标：需要symbol + interval + 时间范围 + 指标参数（如time_period）
- 全球股票：支持美股/港股/国际市场代码
- 商品/汇率：大宗商品（原油/黄金等）+ 外汇汇率

### Finnhub
- 美股为主，支持基本面/新闻/财报日历/内幕交易
- 需要ticker代码（如 AAPL, TSLA）

### Tushare
- A股全量数据，与iFinD重叠度高
- 数据量大，按需使用，注意调用成本
- 可作为iFinD的交叉验证数据源

### yfinance
- 雅虎财经免费API的封装
- 全球股票/指数/基金/加密货币
- 作为低成本全球市场数据补充

## 常见坑与避错指南

1. **A股优先用iFinD🔴**：Tushare与iFinD重叠度高，A股场景优先用iFinD（质量更有保障+已有工具链），Tushare仅作交叉验证或iFinD不可用时备用
2. **美股/全球市场是核心价值🟢**：iFinD主要覆盖A股，美股/港股/全球市场数据 AgentKey finance 是重要补充
3. **Tushare数据量大🟡**：Tushare有155个工具，全量调用成本高，按需精准查询
4. **技术指标补充🟢**：Alpha Vantage 有50+技术指标，当iFinD的技术指标不够用时可以补充
5. **交叉验证价值🟢**：关键数据点（如重要财务指标、行情拐点）可用不同数据源交叉验证，提高准确性
6. **代码格式差异🟡**：不同供应商代码格式不同（美股代码/A股代码/港股代码），注意转换

## 与 iFinD MCP 的关系

| 维度 | iFinD MCP（主力） | AgentKey finance（补充） |
|------|-------------------|--------------------------|
| A股覆盖 | 全面（首选） | Tushare有覆盖（备用/验证） |
| 美股/港股 | 弱/无 | 强（Finnhub + yfinance + Alpha Vantage） |
| 全球市场 | 弱 | 强（Alpha Vantage + yfinance） |
| 技术指标 | 丰富（MACD/KDJ/MA等） | 更丰富（Alpha Vantage 50+） |
| 基本面/财务 | 全面（A股） | Finnhub美股强 |
| 另类数据 | 有限 | 商品/汇率/预测市场等 |
| 数据质量 | 高（专业金融数据商） | 中高（各供应商参差不齐） |
| 调用成本 | 有token配额 | 按credits |

**定位**：iFinD 是 A 股主力数据源，AgentKey finance 做补充/交叉验证/非A股市场覆盖。

## 适用边界（什么情况不用）

- ❌ A股常规数据查询 → 用 iFinD MCP（首选数据源）
- ❌ 指数/板块/基金分析 → 用 iFinD index/fund 模块
- ❌ 简单美股价格查询 → web_search 或 stock-data-skill 即可
- ❌ 全量A股扫描 → iFinD + 量化引擎更高效

---

## 为什么重要

AgentKey finance 填补了 iFinD 在非A股市场的覆盖空白，特别是美股基本面（Finnhub）、全球市场（yfinance/Alpha Vantage）和丰富的技术指标。在以下场景有独特价值：
1. 美股/港股个股分析（iFinD覆盖不足）
2. 全球市场宏观观察
3. 关键数据点的交叉验证
4. iFinD 技术指标不够用的时候补充

核心原则：iFinD 优先，AgentKey finance 补位，不要重复造轮子。
