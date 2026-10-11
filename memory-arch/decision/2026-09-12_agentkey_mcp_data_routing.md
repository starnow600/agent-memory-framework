# 2026-09-12 AgentKey MCP接入 + 顶层数据获取路由决策树（新技能/架构变更）

## 一、决策背景

**触发时间**：2026-09-12 18:57
**决策人**：杨小壶 🧊

### 背景
- AgentKey MCP 接入完成，提供统一数据网关（2000+工具，50+数据源）
- 新增能力：搜索（6家搜索引擎）、社媒（27个平台）、加密货币（15类）、金融补充（4家）、网页抓取（3家）
- 原有技能路由体系中缺少数据获取领域的顶层路由决策
- 工具数量暴增后，如果没有清晰路由，容易出现：选错工具、浪费credits、重复建设

### 契机
- iFinD MCP 刚接入（8个原子层补丁 + 股票/医学2条路由）
- AgentKey MCP 进一步扩充了数据能力边界
- 是时候建立统一的数据获取顶层路由了

---

## 二、决策内容

### 1. AgentKey MCP 接入方案

**接入方式**：作为 MCP 工具直接调用，三步流程：
1. `mcp__agentkey__find_tools` — 发现工具（keyword/prefix）
2. `mcp__agentkey__describe_tool` — 查参数+成本
3. `mcp__agentkey__execute_tool` — 执行调用

**能力分类**：
| 大类 | 工具数 | 定位 |
|------|--------|------|
| 搜索 | ~30+ | web_search 的高质量补充/多源冗余 |
| 社媒 | ~1500+ | 国内社媒深度数据主力（抖音/小红书/微博/微信等） |
| 加密货币 | ~180+ | 加密行情/链上/社交情绪 |
| 金融补充 | ~311 | 美股/全球市场/另类数据（iFinD 补充） |
| 网页抓取 | 4 | 反爬场景的网页抓取补充 |

### 2. 顶层数据获取路由决策树

建立 `plan-data-acquisition-route.md`，覆盖7大领域：
1. A股/基金/指数/宏观 → iFinD MCP（主力）
2. 美股/港股/全球市场 → AgentKey finance
3. 加密货币 → AgentKey crypto
4. 社媒/内容平台 → AgentKey social
5. 普通网页搜索 → web_search（免费）→ AgentKey search（高质量）
6. 网页抓取 → web_fetch → AgentKey scrape
7. 深度研究 → deep-research + AgentKey 多源

**核心原则**：免费够用不花 credits，先用免费工具探路，不够再升级。

### 3. 技能路由体系扩容

**原子层新增8个（iFinD）+ 4个（AgentKey）= 12个**
- iFinD：stock-kline / stock-fundamental / stock-summary / stock-events / index-sector / news-notice / fund-analysis / macro-edb
- AgentKey：web-search / social-media / crypto-data / finance-data

**功能层新增3个（iFinD+学术）+ 2个（AgentKey）= 5个**
- iFinD：stock-full-analysis / market-regime-check
- 学术：academic-literature-review
- AgentKey：multi-source-research / social-trend-tracking

**规划层新增2个（股票/医学）+ 1个（顶层数据路由）= 3个**
- stock-analysis-route / medical-academic-research-route
- plan-data-acquisition-route（顶层数据获取路由）

**总补丁数**：86 → 108 条（P20 + F27 + A61）

---

## 三、影响范围

| 影响项 | 说明 |
|--------|------|
| 技能路由体系 | 新增顶层数据获取路由，所有数据类任务先过此决策树 |
| 成本控制 | 建立"免费→低成本→高成本"的渐进式升级原则 |
| 数据源冗余 | iFinD + AgentKey + 原生工具三级冗余，单源故障可降级 |
| 研究能力 | 社媒/海外数据能力大幅增强，深度研究可调用更多源 |

---

## 四、回滚方案

- AgentKey MCP 不影响现有体系，新增能力不替换旧能力
- 路由决策树是指导性补丁，不强制约束，发现问题随时调整
- 单个原子补丁有问题可单独标记为 inactive

---

## 五、验证要点

1. **路由正确性**：常见搜索/查询场景，决策树能给出清晰路径
2. **成本控制**：免费工具够用时不会升级到付费 AgentKey
3. **工具可达性**：路由中提到的工具确实存在且可调用
4. **故障降级**：iFinD挂了能降级到腾讯→AgentKey→web_search

---

## 六、关联记录

- 前序：iFinD MCP 迁移（2026-09-12，同日上午）
- 前序：iFinD MCP 技能路由补丁（2026-09-12）
- 相关补丁：plan-data-acquisition-route.md（顶层路由）
- 相关补丁：4个 AgentKey 原子层 + 2个 AgentKey 功能层
- 触发条件：🔒新技能接入 / 🔒架构变更 / 用户确认

---

*决策人：杨小壶 | 记录时间：2026-09-12 19:07*
