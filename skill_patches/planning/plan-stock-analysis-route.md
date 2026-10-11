# Planning: 股票分析场景路由决策

## 触发条件
用户提出股票分析相关需求时，需要判断用什么工具/技能/路径来完成

## 路由决策树

```
用户需求：股票分析类
├─ Q1: 是单只股票还是批量/全市场？
│   ├─ 单只/少量（≤5只）
│   │   ├─ Q2: 需要什么维度的分析？
│   │   │   ├─ 快速了解（公司做什么/行业/市值）
│   │   │   │   → atom-ifind-stock-summary（get_stock_summary）
│   │   │   ├─ 技术面/行情/走势分析
│   │   │   │   → atom-ifind-stock-kline（get_stock_performance + stock_highfreq_quotes）
│   │   │   ├─ 基本面/财务/估值分析
│   │   │   │   → atom-ifind-stock-fundamental（get_stock_info + get_stock_financials + get_stock_shareholders）
│   │   │   ├─ 事件/风险/合规
│   │   │   │   → atom-ifind-stock-events（get_stock_events + get_risk_indicators）
│   │   │   ├─ 新闻/公告
│   │   │   │   → atom-ifind-news-notice（search_news + search_notice）
│   │   │   └─ 全面分析（多维度）
│   │   │       → func-ifind-stock-full-analysis（组合调用全套stock-mcp）
│   │   └─ 批量选股/条件筛选
│   │       ├─ Q3: 什么类型的筛选？
│   │       ├─ 按行业/概念/基本面指标筛选
│   │       │   → atom-ifind-stock-summary（search_stocks）
│   │       ├─ 按技术面量化因子筛选（全市场）
│   │       │   → 量化扫描引擎（stock_scanner_v6.x.py）
│   │       └─ 综合量化评分排序
│   │           → 量化扫描引擎 + func-ifind-stock-full-analysis（高评分标的深入）
│   └─ 指数/板块/行业分析
│       ├─ Q4: 需要什么维度？
│       ├─ 指数行情/技术面/估值
│       │   → atom-ifind-index-sector（index_data + index_highfreq_quotes）
│       ├─ 板块行情/成分股/板块轮动
│       │   → atom-ifind-index-sector（sector_data）
│       └─ 市场状态/Regime判断
│           → func-ifind-market-regime-check（指数+板块+新闻三维度）
│
├─ Q5: 需要深度研究/多源验证吗？
│   ├─ 是（行业研究/公司深度/竞争分析/投资逻辑验证）
│   │   → deep-research skill（多信源交叉+引用报告）
│   │   注：iFinD数据可作为deep-research的数据来源之一
│   └─ 否（数据查询即可回答）
│       → 走上述iFinD MCP路径
│
├─ Q6: 是A股还是港股/美股/其他市场？
│   ├─ A股
│   │   → iFinD MCP（首选）→ 三级兜底
│   ├─ 港股/美股
│   │   → stock-data-skill 或 web_search
│   └─ 不确定
│       → 先确认，或先用iFinD尝试再兜底
│
└─ Q7: 已有专用Skill吗？
    ├─ stock-insight skill（综合股票分析）
    │   → 当需求是"帮我分析XX股票"这类综合分析时优先用
    ├─ sector-hotness-analysis skill（板块热度分析）
    │   → 政策-产业-资金三维度板块分析
    └─ 没有专用skill
        → 用iFinD MCP + web_search组合
```

## 数据源优先级（三级兜底🔒）

1. **首选**: iFinD MCP（数据质量最高，接口最稳定）
2. **次选**: 腾讯财经（akshare封装，免费但易限流）
3. **兜底**: web_search + stock-data-skill（其他途径）

降级触发条件：
- iFinD token超限
- MCP调用失败/超时
- 返回数据明显异常

## 与专用Skill的关系

| Skill | 适用场景 | 与iFinD MCP的关系 |
|-------|----------|-------------------|
| stock-insight | 综合股票分析（一键分析） | Skill内部可能也用到iFinD数据，MCP是更底层的原子能力 |
| sector-hotness-analysis | 板块热度三维分析 | 补充iFinD纯数据维度的政策面分析 |
| stock-data-skill | 多市场行情查询 | 当iFinD不可用时的备用，或非A股市场查询 |

## 决策原则

1. **能不用skill就不用skill（原子优先）**: 如果只是查个数据/看个行情，直接用iFinD MCP原子工具，不要加载完整skill
2. **综合分析用skill**: 如果是"帮我全面分析一下"这类综合性需求，用stock-insight skill（如果质量验证过）
3. **iFinD优先（A股场景）**: A股相关的数据查询，iFinD MCP是首选数据源
4. **深度研究走deep-research**: 需要多源交叉验证+分析报告的，走deep-research skill路由

## 依赖的补丁
### Functional
- func-ifind-stock-full-analysis
- func-ifind-market-regime-check
- func-data-driven-dispute-resolution（投资争议时的数据驱动）
### Atomic
- atom-ifind-stock-kline
- atom-ifind-stock-fundamental
- atom-ifind-stock-summary
- atom-ifind-stock-events
- atom-ifind-index-sector
- atom-ifind-news-notice
- atom-route-before-execute（路由前置检查）
- atom-shared-resource-competition-risk（iFinD token资源竞争）

## 来源
- iFinD MCP系列工具新增（2026-09-12）
- 风控v6.x三级兜底机制
- 路由前置检查规则（atom-route-before-execute）
