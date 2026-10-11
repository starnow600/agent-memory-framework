# atom-agentkey-web-search（AgentKey统一搜索网关）

**层级**: Atomic
**ID**: atom-agentkey-web-search
**触发**: 需要高质量网页搜索、多源冗余搜索、特定搜索API能力时；web_search 结果质量不足或需要深度研究时
**来源**: 2026-09-12_AgentKey_MCP接入，统一数据网关搜索类工具实测

---

## 工具能力概述

AgentKey 是一个统一数据网关 MCP，通过一个 API Key 调用 6 家搜索引擎、30+ 搜索工具，支持自动故障转移（同类别多供应商冗余）。按 credits 计费。

### 覆盖的搜索供应商

| 供应商 | 工具数量 | 核心能力 | 适用场景 |
|--------|----------|----------|----------|
| Brave | 16 | 网页搜索/图片搜索/新闻/本地POI/LLM Context | 快速检索、日常搜索 |
| Exa | - | 语义搜索 | 语义相近内容查找 |
| Perplexity | - | AI搜索（带引用回答） | 深度研究、复杂问题 |
| Serper | 10 | 网页/图片/地图/新闻/自动补全 | 多格式搜索、快速检索 |
| Tavily | 4 | 搜索/爬取/提取/站点映射 | 研究级搜索、站点内容提取 |
| Parallel | - | 并行多源搜索 | 多引擎同时查询、交叉验证 |

### 调用三步法
1. `mcp__agentkey__find_tools` — 发现工具（keyword搜索或prefix浏览）
2. `mcp__agentkey__describe_tool` — 查参数定义 + 单次调用成本（credits）
3. `mcp__agentkey__execute_tool` — 执行调用

## 输入要求 / 参数规范

### find_tools
- **q**: 自然语言查询，直接传入用户的完整搜索需求（不要只抽单个关键词）
- **prefix**: 类别浏览，如 `search/`、`search/brave`

### describe_tool
- **name**: 工具的规范名（Provider/Operation格式），如 `Brave/getWebSearch`
- 返回：参数定义 + `credits_per_call` + `cost_by_provider` + execute_as模板

### execute_tool
- **name**: 规范工具名
- **params**: 真实JSON对象（从describe_tool的execute_as模板复制填充）

## 输出格式说明
- 各供应商返回格式不同，以 describe_tool 中描述为准
- 搜索结果为未处理的原始返回，需要自行提取关键信息
- Perplexity 返回带引用的 AI 回答

## 常见坑与避错指南

1. **成本意识🔴**：AgentKey 搜索按 credits 计费，不要用来做免费 web_search 就能搞定的简单搜索。简单查询先用 web_search，质量不够再升级
2. **批量调用前预估成本🟡**：`describe_tool` 返回 `credits_per_call`，大批量调用前先查单价，避免超支
3. **不要每次都find_tools🟡**：常用工具名记下来直接用，减少不必要的发现调用（每次find_tools也消耗credits）
4. **参数格式必须匹配🟡**：严格按照 describe_tool 返回的 execute_as 模板填参数，类型必须一致（数组/对象/字符串）
5. **供应商冗余自动failover🟢**：同一类搜索有多家供应商，一家失败可以自动切另一家，可靠性高
6. **深度研究优先高质量引擎🟢**：Perplexity/Tavily 适合深度研究，Brave/Serper 适合快速检索

## 适用边界（什么情况不用）

- ❌ 简单事实查询/日常搜索 → 用原生 web_search（免费）
- ❌ 中文搜索为主且质量要求不高 → web_search 足够
- ❌ 需要抓取特定网页全文 → 用 web_fetch（简单）或 AgentKey scrape（反爬场景）
- ❌ 批量大规模搜索 → 成本可能很高，先评估再执行

## 与同类工具的比较

| 维度 | AgentKey search（本补丁） | 原生 web_search | deep-research skill |
|------|---------------------------|-----------------|---------------------|
| 搜索质量 | 高（6家专业引擎） | 中（通用搜索） | 高（多源交叉） |
| 供应商数量 | 6家（自动failover） | 1家 | 多源调度 |
| 调用成本 | 有（按credits） | 免费 | 有（子agent成本） |
| 中文支持 | 因供应商而异 | 好 | 好 |
| 深度研究能力 | Perplexity/Exa较强 | 弱 | 强（完整报告） |
| 适用场景 | 需要高质量/多源/特定API的搜索 | 日常简单查询 | 系统性研究报告 |

## 最佳实践

1. **深度研究优先**：Perplexity（AI搜索带引用）+ Tavily（研究级搜索）组合
2. **快速检索**：Brave 或 Serper，响应快成本低
3. **并行交叉验证**：Parallel 同时查多个引擎，结果交叉比对
4. **成本控制**：先用 web_search 探路，结果不理想再上 AgentKey
5. **调用节奏**：ONE call per turn，等结果再下一个，不要batch

---

## 为什么重要

AgentKey 搜索是原生 web_search 的升级替代方案，在需要高质量、多源冗余、特定搜索API的场景下提供更强的数据获取能力。但它是付费的（按credits），必须有成本意识——能原生搞定的不要浪费credits。这是数据获取路由决策中的关键分支点。
