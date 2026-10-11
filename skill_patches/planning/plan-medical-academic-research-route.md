# Planning: 医学/学术研究场景路由决策

## 触发条件
用户提出医学/学术研究相关需求时，需要判断用什么工具/技能/路径来完成

## 路由决策树

```
用户需求：学术/医学研究类
├─ Q1: 是什么类型的需求？
│   ├─ 找某篇具体的论文（知道标题/作者/DOI）
│   │   → Semantic Scholar（atom-semantic-scholar-paper-search）
│   │   注：精确检索最快，SS覆盖全学科
│   │
│   ├─ 查某个医学主题的文献（疾病/药物/疗法）
│   │   ├─ Q2: 需要多全面？
│   │   │   ├─ 快速了解（5-10篇核心）
│   │   │   │   → PubMed综述检索（atom-pubmed-medical-search）
│   │   │   ├─ 标准综述（20-50篇）
│   │   │   │   → func-academic-literature-review（双源交叉验证）
│   │   │   └─ 深度研究（50+篇+多源验证）
│   │   │       → deep-research skill（文献+新闻+行业数据综合）
│   │   └─ Q3: 是纯医学还是跨学科？
│   │       ├─ 纯医学/生物医学
│   │       │   → PubMed为主 + Semantic Scholar补充引用网络
│   │       └─ 跨学科（AI+医学/医学工程/生物信息）
│   │           → Semantic Scholar为主 + PubMed补充临床证据
│   │
│   ├─ 查引用关系/研究脉络
│   │   → Semantic Scholar（atom-semantic-scholar-paper-search）
│   │   注：PubMed的引用功能弱，SS的引用网络和引用上下文是核心优势
│   │
│   ├─ 查作者/研究团队
│   │   → Semantic Scholar（作者论文列表+引用统计）
│   │   注：同名作者需结合机构和研究领域确认
│   │
│   ├─ 临床试验信息
│   │   ├─ 文献中的临床试验
│   │   │   → PubMed（过滤Clinical Trial类型）
│   │   └─ 临床试验注册信息
│   │       → web_search（ClinicalTrials.gov等注册库）
│   │
│   ├─ 行业/产业研究（医药行业/技术产业化）
│   │   → deep-research skill（学术文献+行业报告+公司数据+新闻）
│   │   注：纯学术文献不足以支撑产业研究
│   │
│   └─ 最新进展/新闻/政策
│       → web_search / topic_tracking（文献数据库有滞后性）
│
├─ Q4: 时间紧迫性？
│   ├─ 快速回答（1-2篇参考文献即可）
│   │   → 单库检索（PubMed或Semantic Scholar）
│   └─ 严谨研究
│       → 双源交叉验证（func-academic-literature-review）
│
└─ Q5: 需要中文文献吗？
    ├─ 是（中医/国内临床数据等）
    │   → web_search（知网/万方等中文数据库）
    │   注：PubMed和SS的中文文献都很少
    └─ 否（英文文献即可）
        → 走上述学术数据库路径
```

## 工具选择矩阵

| 场景 | PubMed | Semantic Scholar | web_search | deep-research |
|------|--------|------------------|------------|---------------|
| 医学文献检索 | ⭐⭐⭐ 首选 | ⭐⭐ 补充引用 | ⭐ 辅助 | ⭐ |
| 全学科学术论文 | ⭐ | ⭐⭐⭐ 首选 | ⭐ | ⭐⭐ |
| 引用网络分析 | ⭐ | ⭐⭐⭐ 首选 | ⭐ | ⭐⭐ |
| 临床试验 | ⭐⭐⭐ 首选 | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| 最新研究进展 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 行业/产业分析 | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ 首选 |
| 中文文献 | ⭐ | ⭐ | ⭐⭐⭐ 首选 | ⭐⭐ |
| 多源综合研究 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ 首选 |

## 决策原则

1. **医学主题PubMed优先**: 生物医学领域PubMed是金标准，覆盖面最广、质量最权威
2. **引用分析用Semantic Scholar**: 引用网络和引用上下文是SS的独特价值
3. **综述类需求双源交叉**: 重要的文献综述必须双库检索，避免漏检
4. **产业/行业研究走deep-research**: 学术文献只是产业研究的一部分，还需要公司数据、市场数据、政策分析
5. **时效性需求走web_search**: 文献数据库有发表滞后，最新进展和新闻用web_search或话题追踪
6. **轻量查询不加载skill**: 只是查几篇论文的话，直接用原子工具，不要走完整的deep-research流程

## 依赖的补丁
### Functional
- func-academic-literature-review
### Atomic
- atom-pubmed-medical-search
- atom-semantic-scholar-paper-search
- atom-route-before-execute
- atom-methodology-search-first（方法论类问题先搜索）
### Planning
- plan-research-deep（深度调研路由）

## 来源
- PubMed技能新装（2026-09-12）
- Semantic Scholar技能新装（2026-09-12）
- 防御股补跌学术搜索经验（2026-06-20）
- 深度调研路由体系（plan-research-deep）
