# 三层Skill补丁库（SkillX架构）

基于 [SkillX (arxiv:2604.04804, zjunlp)](https://arxiv.org/abs/2604.04804) 架构，结合我们的反向蒸馏经验构建。

## 架构概述

```
三层结构：
├── Planning（规划层）  - 任务级路由决策，"做什么、先做什么"。来源：成功轨迹
├── Functional（功能层）- 跨工具组合子程序，"怎么做某类子任务"。来源：成功轨迹  
└── Atomic（原子层）    - 单工具使用经验/常见失败，"用某工具注意什么"。来源：失败轨迹
```

## 目录概览

```
skill_patches/
├── atomic/          # 原子层：单工具使用经验（61个补丁）
├── functional/      # 功能层：跨工具组合的功能单元（27个补丁）
├── planning/        # 规划层：任务级策略选择（20个补丁）
├── scripts/         # 脚本：routing_decision.py / topic_dedup_check.py / deep_interpretation_check.py
├── index.json       # 索引文件（全量检索入口）
├── README.md        # 本文件
└── distill_report_*.md  # 历次蒸馏报告（6/22-9/6，每周六产出）
```

## 补丁数量统计

| 层级 | 数量 | 说明 |
|------|------|------|
| Planning | 20 | 任务级路由决策（量化建仓/深度调研/数据源故障/影子测试/数据获取路由等） |
| Functional | 27 | 跨工具功能单元（止损计算/文献综述/数据完整性/争议解决/多源研究/社媒趋势等） |
| Atomic | 61 | 单工具经验（PPT规则/量化约束/iFinD MCP/学术搜索/AgentKey/数据字段等） |
| **合计** | **108** | |

## 2026-09-12 新增能力（15条）

### iFinD MCP系列（11条，domain=stock）

**原子层（8条）**：按模块合并
- `atom-ifind-stock-kline` — 股票行情与技术指标查询（get_stock_performance + stock_highfreq_quotes）
- `atom-ifind-stock-fundamental` — 股票基本面查询（get_stock_info + get_stock_financials + get_stock_shareholders + get_esg_data）
- `atom-ifind-stock-summary` — 股票快速查询与智能选股（get_stock_summary + search_stocks）
- `atom-ifind-stock-events` — 公司事件与风险指标（get_stock_events + get_risk_indicators）
- `atom-ifind-index-sector` — 指数与板块数据（index_data + sector_data + index_highfreq_quotes）
- `atom-ifind-news-notice` — 新闻与公告（search_news + search_notice + search_trending_news）
- `atom-ifind-fund-analysis` — 基金分析全套（fund-mcp 8个工具）
- `atom-ifind-macro-edb` — 宏观经济数据（get_edb_data）

**功能层（2条）**
- `func-ifind-stock-full-analysis` — iFinD单只股票全景分析标准流程（Phase 1-5组合调用）
- `func-ifind-market-regime-check` — 市场状态快速判断（指数+板块+新闻+情绪 四维交叉）

**规划层（1条）**
- `plan-stock-analysis-route` — 股票分析场景路由决策树（iFinD vs web_search vs stock-insight skill）

### 学术技能系列（4条，domain=medical/academic）

**原子层（2条）**
- `atom-pubmed-medical-search` — PubMed医学文献搜索（NCBI E-utilities，3500万+生物医学文献）
- `atom-semantic-scholar-paper-search` — Semantic Scholar学术论文搜索（知识图谱，2亿+全学科论文）

**功能层（1条）**
- `func-academic-literature-review` — 学术文献综述标准流程（PubMed + Semantic Scholar双源交叉验证）

**规划层（1条）**
- `plan-medical-academic-research-route` — 医学/学术研究场景路由决策（PubMed vs SS vs web_search vs deep-research）

### AgentKey MCP系列（7条，domain=data-integration）

**原子层（4条）**：按大类合并
- `atom-agentkey-web-search` — AgentKey统一搜索网关（Brave/Exa/Perplexity/Serper/Tavily/Parallel 6家引擎）
- `atom-agentkey-social-media` — AgentKey社交媒体数据（27个平台、1500+工具，国内社媒覆盖极全）
- `atom-agentkey-crypto-data` — AgentKey加密货币数据（15大类、180+工具，行情/链上/社交情绪/NFT等）
- `atom-agentkey-finance-data` — AgentKey金融数据补充（Alpha Vantage/Finnhub/Tushare/yfinance）

**功能层（2条）**
- `func-agentkey-multi-source-research` — 多源交叉研究流程（搜索→社媒→网页抓取→交叉验证）
- `func-agentkey-social-trend-tracking` — 社媒趋势追踪流程（多平台热度对比+热点内容提取）

**规划层（1条）**
- `plan-data-acquisition-route` — 数据获取路由决策树（顶层路由：A股/iFinD → 美股/AgentKey → 加密/AgentKey → 社媒/AgentKey → 搜索/web_search→AgentKey）

## 领域分布

| 领域 | 补丁数 | 说明 |
|------|--------|------|
| stock（股票） | ~25 | iFinD MCP全模块 + 量化引擎 + 风控规则 |
| data-integration（数据集成） | ~7 | AgentKey MCP统一数据网关（搜索/社媒/加密/金融） |
| dev（开发） | ~15 | 代码审计/迁移/脚本规范/子session |
| research（研究） | ~10 | 深度调研/学术文献/方法论 |
| medical（医学） | ~3 | PubMed相关 |
| academic（学术） | ~3 | Semantic Scholar相关 |
| general（通用） | ~20 | 路由/记忆/叙事/蒸馏 |
| content（内容） | ~15 | PPT制作 |
| meta（元认知） | ~10 | 自我美化/监控漂移/规则生长 |

## 使用方式

### 查找补丁
- **通过关键词**：`memory_search` 语义检索补丁内容
- **通过索引**：读取 `index.json`，按 layer/domain/trigger 筛选
- **通过路由脚本**：`scripts/routing_decision.py` 自动匹配任务到对应补丁

### 新增补丁流程
参见 `functional/func-skill-patch-distill.md`（每周六蒸馏日程）

### 路由前置检查
参见 `atomic/atom-route-before-execute.md`（选工具前必查路由）

## 核心原则

1. **Planning从成功轨迹来**：任务级路由 = 做对过的方法
2. **Functional从成功轨迹来**：功能单元 = 做对过的子流程
3. **Atomic从失败轨迹来**：工具约束 = 做错过的坑
4. **双向蒸馏**：成功→提取策略→Planning/Functional；失败→提取教训→Atomic
5. **激活机制**：路由到某技能/进入某任务类型时，通过 memory_search + 技能指纹索引 关联激活相关补丁

## 历史蒸馏

| 次数 | 日期 | 关键产出 |
|------|------|----------|
| v1→v2 | 6/22 | 初始10条重构为三层架构 |
| 1 | 6/27 | 首次双向蒸馏，+6条 |
| 2 | 7/4 | 叙事增强+Wiki支撑，+4条 |
| 3 | 7/11 | 魔鬼代言人+事实验证，+6条 |
| 4 | 7/19 | 子session产物虚报+部分成功危险，+5条 |
| 5 | 7/26 | 主人纠正元教训+事实验证闭环，+8条 |
| 6 | 8/2 | 监控断档+数据完整性链+hook审计，+6条 |
| 7 | 8/9 | 稳态事件驱动+MEMORY压缩+3日确认，+6条 |
| 8 | 8/16 | 政策技术双确认+代码审计P0闭环，+4条 |
| 9 | 8/23 | 数据源故障切换+小问题即改+试跑外推，+4条 |
| 10 | 8/30 | 影子测试默认方法论+监控覆盖漂移，+2条 |
| 11 | 9/6 | 影子测试加速迭代+数据驱动争议+资源竞争，+5条 |
| 12 | 9/12 | iFinD MCP+PubMed+Semantic Scholar扩容，+15条 |
| 13 | 9/12 | AgentKey MCP数据集成层，+7条 |
