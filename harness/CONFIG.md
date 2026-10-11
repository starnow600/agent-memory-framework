# Harness 配置

> 将散落在行为模式中的决策逻辑提取为可审计、可度量的显性配置
> 创建时间：2026-05-24
> 原则：隐性知识显性化 → 可观测 → 可优化

---

## 1. 路由日志

### 1.1 日志格式

每次工具/技能选择时，写入 `./harness/route_log.jsonl`，一行一条：

```json
{
  "ts": "2026-05-24T11:30:00+08:00",
  "scenario": "A股收盘价查询",
  "chosen": "fetch_web(新浪)",
  "fallback_used": false,
  "success": true,
  "latency_ms": 1200
}
```

字段说明：
- `ts`: ISO8601时间戳
- `scenario`: 场景描述（从fallback链的场景名取）
- `chosen`: 实际选用的工具/技能
- `fallback_used`: 是否因为首选失败而降级
- `success`: 本次调用是否成功
- `latency_ms`: 耗时（可估）

### 1.2 写入触发

路由日志在以下时机写入：
- 主动工具选择时（search_web vs TinyFish vs fetch_web 等）
- 技能路由选择时（从技能指纹索引选技能时）
- 降级发生时（首选工具失败，切换到备选）

### 1.3 统计产出

每日记忆捕获任务中，扫描 `route_log.jsonl` 输出：
- 各工具调用次数和成功率
- 各场景首选命中率
- 降级触发次数和原因分布

写入 `./harness/route_stats.md`（每周日覆盖更新）。

---

## 2. Fallback 链

### 2.1 网页/信息获取

| 场景 | 首选 | 二选 | 三选 | 四选 | 备注 |
|------|------|------|------|------|------|
| A股信息搜索 | TinyFish Search | search_web | — | — | 结构化JSON优先 |
| A股收盘价 | fetch_web(新浪) | TinyFish Fetch(新浪) | — | — | 交叉验证需要新浪源 |
| 网页渲染读取 | TinyFish Fetch | fetch_web | agent-browser | — | 渲染能力递减 |
| 通用搜索 | search_web | TinyFish Search | — | — | 覆盖面优先 |
| 需交互的网页 | agent-browser | — | — | — | 唯一选择，需云电脑 |
| 微信视频号 | agent-browser(云电脑) | search_web(关键词搜) | — | — | fetch_web和TinyFish均无法获取 |

### 2.2 文档处理

| 场景 | 首选 | 二选 | 三选 | 备注 |
|------|------|------|------|------|
| Word新建空白文档 | docx技能(docx-js) | — | — | 无合并单元格问题，docx-js最干净 |
| Word编辑，无合并单元格 | OfficeCLI | python-docx | — | OfficeCLI精确编辑更方便 |
| Word编辑，有合并单元格 | OfficeCLI(语义→DOM→XML三层) | OOXML手动改XML | python-docx(兜底) | python-docx会破坏合并结构(6/25教训) |
| Word复杂嵌套+合并单元格 | OfficeCLI→失败则OOXML手动改XML | python-docx(最后兜底) | — | 复杂场景python-docx风险太大 |
| Excel全操作 | OfficeCLI | excel_master | — | OfficeCLI支持query/remove/chart等 |
| PDF读取内容 | parse_file | pdf技能 | — | parse_file优先 |
| PDF填表单 | pdf技能 | — | — | 唯一选择 |

> **Word处理工具选择规则（7/8修正）**：
> - 新建空白 docx → docx skill (docx-js)，无合并单元格问题
> - 编辑已有 docx，无合并单元格 → OfficeCLI 优先
> - 编辑已有 docx，有合并单元格 → OfficeCLI（语义→DOM→XML三层）优先，python-docx 会破坏合并结构
> - 复杂嵌套+合并单元格 → OfficeCLI 先试 → 失败则 OOXML 手动改 XML
> - python-docx 仅作最后兜底，绝不作为编辑已有 docx 的首选
> - 历史教训：5/13 OfficeCLI复杂嵌套也搞不定→python-docx兜底；6/25 python-docx破坏合并单元格→必须走docx skill OOXML流程

### 2.3 A股分析

| 场景 | 首选 | 二选 | 备注 |
|------|------|------|------|
| 技术面分析 | stock-analysis | — | 均线/MACD/RSI |
| 基本面分析 | astock-casestudy | — | 恒生聚源8维 |
| 板块热度 | sector-hotness-analysis | — | 政策/产业/资金 |
| 机构观点 | institutional-opinion-summary | — | 研报汇总 |
| 量化评分 | quant_engine.py | — | 多因子+风控 |
| 选股扫描 | stock_scanner.py → quant_engine.py | — | 双模式→评分 |
| K线数据获取 | 东财curl | 腾讯K线 | 新浪K线(456限流风险) |

### 2.4 PPT

| 场景 | 首选 | 二选 | 备注 |
|------|------|------|------|
| 从零创建 | create-ppt | — | 出图后OfficeCLI精修 |
| 文章转PPT | article-to-ppt | — | 输入是文章 |
| 风格提取→PPT | ppt-style-generator → create-ppt | — | 需风格参考图 |

### 2.5 网页/可视化

| 场景 | 首选 | 二选 | 备注 |
|------|------|------|------|
| 成品HTML网页 | premium-webapp-design | — | 直接可用 |
| 设计方案/配色 | web-design-master | — | 指导不落地 |
| 数据可视化 | echart | — | ECharts JSON |
| 结构图/流程图 | drawio-generator | — | .drawio文件 |

### 2.6 降级规则

- 首选失败后立即降级到二选，不重试首选
- 同一场景连续3次首选失败 → 临时调换首选和二选的优先级，并在路由日志标记
- 降级时在路由日志记录 `fallback_used: true` 和首选失败原因
- 每周日lint时检查 `route_stats.md`，如果某工具7日成功率<70%，触发优先级调整讨论

### 2.7 Fallback统计口径说明（9/1月度回顾新增 · 10/1方案A落地）

> **核心区分**：路由日志区分两层降级——**路由决策降级**（换工具/技能）和**数据层面降级**（同一工具内换数据源），分别用两个字段追踪。

#### 字段定义

| 字段 | 类型 | 含义 | 典型值 |
|-----|------|------|-------|
| `fallback_used` | bool | 路由决策层面的降级：首选工具/技能失败，切换到不同的工具/技能 | true / false |
| `data_fallback_used` | bool | 数据层面的降级：同一工具/路径内换数据源，如MCP空返回→腾讯接口兜底 | true / false |
| `data_source_level` | string | 最终数据来源级别，用于统计降级深度 | `"mcp"` / `"ifind_cli"` / `"tencent"` / `"akshare"` / `""` |

#### 三级降级链路与字段取值

| 场景 | fallback_used | data_fallback_used | data_source_level | 说明 |
|-----|---------------|---------------------|-------------------|------|
| iFinD MCP 直接成功 | false | false | `"mcp"` | 首选路径，正常 |
| iFinD CLI 直接成功 | false | false | `"ifind_cli"` | 首选路径，正常 |
| MCP空→腾讯兜底成功 | false | true | `"tencent"` | 数据层面降级，路由未变 |
| MCP空→腾讯空→akshare成功 | false | true | `"akshare"` | 数据层面两级降级 |
| 全链路失败 | false | true | `""` | 数据全部失败 |
| 路由决策换工具（如Python→Skill） | true | false / true | 取决于最终工具 | 路由层降级，数据层单独标记 |

#### 统计口径

**T7月度报告需分别统计**：
- 路由决策降级率 = `fallback_used=true` 记录数 / 总记录数（计入T6 Fallback链评分）
- 数据层面降级率 = `data_fallback_used=true` 记录数 / 总数据调用数（反映数据源健康度）
- 降级深度分布 = `data_source_level` 各层级占比

避免仅用 `fallback_used` 字段判断系统降级率导致的统计偏差。

---

## 3. Harness 决策配置

### 3.1 任务派发决策

```
任务来了：
├─ 能1-2步完成？ → 主会话自己做
├─ 可独立闭环(>3步) + 无需频繁确认？ → sessions_spawn
├─ 有明确时间 + 未来执行？ → Calendar
├─ 需轻量周期检查？ → Heartbeat
├─ 需浏览器交互？ → 子session(云电脑)
├─ 需手机App？ → mobile_use(需云手机)
└─ 不确定 → 先推进再判断
```

### 3.2 记忆写入决策

```
信息出现了：
├─ 是API Key/密码/Token？ → SECRET.md
├─ 是主人对我的身份/性格设定？ → 基础设定/SOUL.md
├─ 换项目还成立的个人信息？ → USER.md
├─ 能填进"用XX工具时要注意YY"的？ → 基础设定/TOOLS.md
├─ 和具体工作相关的规则/决策/进度？ → MEMORY.md
│  ├─ 事实记录 → 原样存储
│  ├─ 偏好约束 → 原样存储(硬约束)
│  └─ 经验规则 → 三段式写入(触发条件|具体行动|不适用边界)
└─ 不确定是否要记 → 记(宁可多记不漏记，但只记长期稳定信息)
```

### 3.3 搜索策略决策

```
需要搜索信息：
├─ 具体事实/当前状态/强时效？ → 必须搜再答
├─ A股相关？ → TinyFish Search首选
├─ 通用知识？ → search_web
├─ 需要网页全文？ → fetch_web(静态) / TinyFish Fetch(渲染)
├─ 需要交互？ → agent-browser
├─ 我认识但不确定？ → 先搜确认，不凭内部知识
└─ 常识确定？ → 直接答(但标注置信度)
```

### 3.4 子Session健康检查

- 派发后5分钟未返回 → sessions_status检查一次
- 10分钟未返回 → sessions_history查看进展
- 严重跑偏 → sessions_send修正
- 不可挽回 → sessions_abort重来
- 结果返回后 → 轻量验收(产物存在性+格式+无明显错误)

### 3.5 错误恢复决策

```
工具调用失败：
├─ 同一工具同一参数 → 最多重试1次
├─ 重试仍失败 → 查看错误类型
│  ├─ 授权/权限问题 → 报告用户，不绕过
│  ├─ 限流/频率 → 等待后重试或换源
│  ├─ 参数错误 → 修正参数重试
│  ├─ 工具不可用 → fallback链降级
│  └─ 未知错误 → 换策略，不盲目重试
├─ 同一路径失败2次 → 必须换策略
└─ 失败信息不写入文件
```

---

## 4. 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-05-24 | 初始创建：路由日志、Fallback链、决策配置 |
| v1.1 | 2026-07-08 | Word处理工具按复杂度分层（新建→docx-js；无合并单元格→OfficeCLI；有合并单元格→OfficeCLI三层；复杂嵌套→OOXML手动改XML）。python-docx降级为最后兜底。 |
