# Planning: 数据获取路由决策树

## 触发条件
任何需要从外部获取数据/信息的场景，需要判断用什么数据源/工具/路径来完成。这是顶层路由——所有数据获取需求的入口。

## 路由决策树

```
用户需求：数据/信息获取类
├─ Q1: 需求属于哪个领域？
│   ├─ A股/基金/指数/宏观经济
│   │   ├─ Q1a: 是实时行情还是历史/基本面？
│   │   │   ├─ 实时行情/高频 → iFinD MCP stock_highfreq_quotes
│   │   │   ├─ 历史行情/技术面 → iFinD MCP get_stock_performance
│   │   │   ├─ 基本面/财务/估值 → iFinD MCP get_stock_financials
│   │   │   ├─ 快速了解/选股 → iFinD MCP get_stock_summary / search_stocks
│   │   │   ├─ 事件/风险 → iFinD MCP get_stock_events / get_risk_indicators
│   │   │   ├─ 指数/板块 → iFinD MCP index_data / sector_data
│   │   │   ├─ 基金 → iFinD MCP fund系列
│   │   │   ├─ 宏观/行业经济 → iFinD MCP get_edb_data
│   │   │   └─ 新闻/公告 → iFinD MCP search_news / search_notice
│   │   ├─ Q1b: iFinD不可用/超限？
│   │   │   ├─ 是 → 三级兜底：腾讯财经(akshare) → web_search + stock-data-skill
│   │   │   └─ 否 → 继续用iFinD
│   │   └─ Q1c: 需要交叉验证？
│   │       ├─ 是 → AgentKey finance (Tushare/yfinance/Alpha Vantage)
│   │       └─ 否 → iFinD足够
│   │
│   ├─ 美股/港股/全球市场
│   │   ├─ Q2a: 需要什么深度？
│   │   │   ├─ 简单价格查询 → web_search 或 stock-data-skill
│   │   │   ├─ 基本面/财报/新闻 → AgentKey finance (Finnhub)
│   │   │   ├─ 技术指标/全球覆盖 → AgentKey finance (Alpha Vantage)
│   │   │   └─ 全球市场广覆盖 → AgentKey finance (yfinance)
│   │   └─ Q2b: 需要与A股对比分析？
│   │       ├─ 是 → iFinD MCP + AgentKey finance 组合
│   │       └─ 否 → 按需选择
│   │
│   ├─ 加密货币
│   │   ├─ Q3a: 需要什么数据？
│   │   │   ├─ 价格行情 → AgentKey crypto (market类)
│   │   │   ├─ 链上数据 → AgentKey crypto (on-chain/chain类)
│   │   │   ├─ 交易所数据 → AgentKey crypto (exchange类)
│   │   │   ├─ 社交情绪 → AgentKey crypto (social intel类)
│   │   │   ├─ 新闻/事件 → AgentKey crypto (news/events类)
│   │   │   └─ NFT → AgentKey crypto (nft类)
│   │   └─ ⚠️ 注意：仅用于了解研究，不做投资决策（A股为主业）
│   │
│   ├─ 社媒/内容平台数据
│   │   ├─ Q4a: 是长期追踪还是一次性深度分析？
│   │   │   ├─ 长期定期追踪 → 话题追踪v3（topic_tracking skill）
│   │   │   └─ 一次性深度钻取 → AgentKey social
│   │   ├─ Q4b: 需要哪些平台？
│   │   │   ├─ 消费/品牌 → 小红书 + 抖音 + 微博（AgentKey social）
│   │   │   ├─ 科技/行业 → 知乎 + B站（AgentKey social）
│   │   │   ├─ 舆情/热点 → 微博 + 抖音 + 知乎（AgentKey social）
│   │   │   └─ 海外 → Twitter + TikTok + Reddit（AgentKey social）
│   │   └─ Q4c: 简单了解还是深度数据？
│   │       ├─ 简单了解 → web_search 即可
│   │       └─ 深度数据 → AgentKey social + func-agentkey-social-trend-tracking
│   │
│   ├─ 普通网页搜索/信息查询
│   │   ├─ Q5a: 需求复杂度？
│   │   │   ├─ 简单事实查询/日常搜索 → 原生 web_search（免费，先用）
│   │   │   ├─ 高质量深度搜索 → AgentKey search (Perplexity/Tavily)
│   │   │   ├─ 多源并行验证 → AgentKey search (Parallel)
│   │   │   └─ 快速检索 → AgentKey search (Brave/Serper)
│   │   ├─ Q5b: web_search结果够不够？
│   │   │   ├─ 够 → 就用web_search（省钱）
│   │   │   └─ 不够 → 升级到 AgentKey search
│   │   └─ 成本原则：免费能用就不花credits
│   │
│   ├─ 网页抓取/特定网站内容提取
│   │   ├─ Q6a: 目标网站有反爬吗？
│   │   │   ├─ 无/不确定 → 先用 web_fetch（简单免费）
│   │   │   └─ 有/普通方式失败 → AgentKey scrape (Firecrawl/Bright Data)
│   │   ├─ Q6b: 需要抓取多少页面？
│   │   │   ├─ 少量（<10页） → web_fetch 或 AgentKey scrape
│   │   │   └─ 大量/全站 → AgentKey scrape (Tavily站点映射 + Firecrawl)
│   │   └─ 成本原则：先简单后复杂，先免费后付费
│   │
│   └─ 深度研究/多源交叉验证
│       ├─ Q7a: 是系统性研究项目吗？
│       │   ├─ 是 → deep-research skill（完整研究工作流）
│       │   └─ 否 → 按需组合AgentKey工具
│       ├─ Q7b: 需要哪些维度的数据？
│       │   ├─ 搜索层 → AgentKey search (Perplexity + Brave)
│       │   ├─ 社媒层 → AgentKey social（按主题选平台）
│       │   ├─ 网页抓取层 → AgentKey scrape (Firecrawl)
│       │   └─ 金融数据层 → iFinD MCP + AgentKey finance
│       └─ 推荐流程：func-agentkey-multi-source-research
│
├─ Q2: 成本意识检查
│   ├─ 原生免费工具够不够？→ 够就用免费的
│   ├─ AgentKey credits消耗预估？→ 高成本调用先评估
│   └─ 有没有更便宜的路径？→ 优先选低成本方案
│
└─ Q3: 已有专用Skill吗？
    ├─ stock-insight → 综合股票分析
    ├─ sector-hotness-analysis → 板块热度分析
    ├─ deep-research → 深度研究
    ├─ topic_tracking → 话题追踪
    └─ 没有专用skill → 按上述路由选择原子工具组合
```

## 成本优先级原则

**免费 > 低成本 > 高成本**

1. **第一梯队（免费）**：web_search、web_fetch、iFinD MCP（已有配额）
2. **第二梯队（低成本）**：AgentKey search（Brave/Serper）、AgentKey finance 简单查询
3. **第三梯队（高成本）**：AgentKey social 大数据量、AgentKey 批量抓取、深度研究全流程

**核心原则**：能原生搞定的不要浪费credits。先用免费工具探路，不够再升级。

## 数据源故障兜底

### iFinD MCP 故障
1. 首选：腾讯财经（akshare封装）
2. 次选：AgentKey finance (Tushare/yfinance)
3. 兜底：web_search + stock-data-skill

### AgentKey 故障
- 降级到对应领域的原生工具/web_search
- 搜索类 → web_search
- 金融类 → iFinD MCP（A股）/ web_search（美股）
- 社媒类 → web_search + 话题追踪v3

## 与已有路由补丁的关系

| 补丁 | 关系 |
|------|------|
| plan-stock-analysis-route | 本决策树的"A股/基金/指数"分支的细化 |
| plan-medical-academic-research-route | 本决策树的"深度研究"分支中医学领域的细化 |
| plan-route-first | 本决策树是"选工具/方案前"的具体执行规范 |
| plan-data-source-failover | 数据源故障时的处理流程，与本决策树互补 |

## 依赖的补丁

### Functional
- func-agentkey-multi-source-research（多源交叉研究流程）
- func-agentkey-social-trend-tracking（社媒趋势追踪流程）
- func-ifind-stock-full-analysis（iFinD股票全景分析）
- func-ifind-market-regime-check（市场状态判断）
- func-academic-literature-review（学术文献综述）

### Atomic
- atom-ifind-stock-kline/fundamental/summary/events（iFinD股票系列）
- atom-ifind-index-sector / atom-ifind-fund-analysis / atom-ifind-macro-edb（iFinD其他模块）
- atom-ifind-news-notice（iFinD新闻公告）
- atom-agentkey-web-search（AgentKey搜索）
- atom-agentkey-social-media（AgentKey社媒）
- atom-agentkey-crypto-data（AgentKey加密货币）
- atom-agentkey-finance-data（AgentKey金融补充）
- atom-route-before-execute（路由前置检查）

## 决策原则

1. **领域优先**：先判断需求属于哪个领域，再选对应数据源
2. **成本意识**：免费工具能用就不用付费的，低成本能搞定就不用高成本的
3. **渐进式深入**：从简单到复杂，从低成本到高成本，每步判断是否需要继续
4. **iFinD主力**：A股相关的首选iFinD MCP，AgentKey finance做补充
5. **交叉验证**：关键数据点用不同数据源交叉验证，提高可靠性
6. **故障兜底**：每个领域都有降级方案，单源故障不中断输出

## 来源
- AgentKey MCP接入（2026-09-12）
- iFinD MCP三级兜底机制
- 路由前置检查规则（atom-route-before-execute）
- 数据源故障切换框架（plan-data-source-failover）
