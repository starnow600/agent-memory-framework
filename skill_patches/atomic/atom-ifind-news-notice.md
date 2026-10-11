# atom-ifind-news-notice（iFinD新闻与公告查询）

**层级**: Atomic
**ID**: atom-ifind-news-notice
**触发**: 需要查询A股/基金/港美股公告、财经新闻、热门事件驱动资讯时
**来源**: iFinD MCP news模块（2026-09-12新增），新闻与公告工具集合

---

## 工具能力概述

| 工具 | 能力 | 典型场景 |
|------|------|----------|
| `mcp__hexin-ifind-ds-news-mcp__search_notice` | A股/基金/港美股公告内容语义查询，返回相关公告段落文本 | 查年报摘要、重大公告、公告关键词搜索 |
| `mcp__hexin-ifind-ds-news-mcp__search_news` | 同花顺财经新闻资讯片段检索 | 个股新闻、行业新闻检索 |
| `mcp__hexin-ifind-ds-news-mcp__search_trending_news` | 同花顺热门事件驱动资讯，注重时效性与传播性 | 近期热点事件、市场情绪判断 |

## 输入要求 / 参数规范

### search_notice / search_news
- **query**: 自然语言格式，要求包含证券实体/行业板块等关注实体 + 重点关注信息描述
- **time_start / time_end**: 日期范围，格式 `YYYY-MM-DD`
- **size**: 期望返回片段数量，上限20
  - 针对性查询（query详细）: 可调低（3-5）
  - 宽泛查询（query模糊）: 可调高（10-20）

### search_trending_news
- **time_scope**: 时效性范围 - `6小时` / `24小时` / `近一周`
- **sensitive**: 情感方向 - `正面` / `负面` / `中性` / `全部`
- **industry_name**: 行业名称筛选（单行业），为空代表全行业
- **keyword**: 资讯包含关键词，建议简洁通用
- **size**: 返回数量，上限20

## 输出格式说明
- 返回相关资讯/公告**片段文本**，不是全文
- 是语义匹配的段落级结果，不是简单标题列表
- trending_news注重时效性，覆盖低热度/旧资讯较少

## 常见坑与避错指南

1. **片段 vs 全文🔴**：返回的是语义匹配的片段，不是完整公告/新闻原文。需要全文时需用web_fetch打开对应链接
2. **query模糊度控制🟡**：query越具体，返回越精准但数量越少；query越宽泛，数量多但噪音大
3. **时间范围必设🟡**：不设时间范围可能返回很旧的内容，投资相关查询建议限制在近期
4. **trending_news时效性强🟢**：只适合查近期热点，做历史事件回顾用search_news
5. **行业筛选枚举值🟢**：industry_name需从给定枚举中选择，不是任意行业名都能用

## 适用边界（什么情况不用）

- ❌ 需要公告/新闻全文 → 用web_fetch或web_search获取原文链接
- ❌ 深度事件分析/研究报告 → 用deep-research skill
- ❌ 社交媒体舆情 → 用web_search或话题追踪
- ❌ 国际新闻/非财经新闻 → 用web_search
- ❌ 结构化事件数据（如IPO/解禁列表）→ 用 atom-ifind-stock-events

---

## 为什么重要

新闻和公告是基本面分析的重要补充——业绩公告、并购消息、政策新闻等都是股价变动的催化剂。iFinD的语义检索相比普通关键词搜索更精准，能快速定位公告/新闻中的关键信息片段。
