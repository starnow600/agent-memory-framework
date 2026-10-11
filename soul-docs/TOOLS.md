# TOOLS.md — 操作守则与索引
> 原则：高频必看规则留此，低频参考全部迁入skill_patches，仅留指针指向。

## 规则标记说明
- 🔒 = 必须遵从，跳过等同违规（SOUL.md兜底强制执行）
- 💡 = 建议参考，可根据上下文灵活调整
- 修改🔒规则时的同步流程：详见 `基础设定/experience/rule_sync_protocol.md`

---

## 🔒 工具调用检查清单
调用前5问：①必要性：真需要调用还是凭记忆能答？②选型：工具/skill是最优的吗？③参数：完整吗？有没有漏必填项？④并行：能和其他独立调用并行吗？⑤兜底：失败了有备选吗？
- **并行优先原则**：多个独立数据查询（同时查多只股/搜多个关键词）优先批量并行，有依赖关系（先查A再根据A查B）才串行。

## 🔒 工具失败处理规范
三级兜底，逐级降级：
1. **同类重试**：最多2次，指数退避（1s→3s）
2. **降级备选**：按优先级切换工具（如iFinD→腾讯→akshare，具体见路由补丁）
3. **两次降级失败**：告知用户+说明影响+给出替代方案
- 所有工具失败写入usage_log，用于统计和改进。

## 🔒 引用规范
- 非计算性事实数据必附来源
- 来源标注格式：`[来源: 工具/文件/网页名]`，关键结论后就近标注
- 关键数据点可追溯到原始查询
- 计算性结论（评分、指标）说明计算口径即可
- 这是"交付数据自证🔒"的细化执行标准

---

## 🎯 PPT路由 🔒
PPT任务最高优先级。默认dashi-ppt(可编辑⭐5)|精美→create-ppt|文章转→article-to-ppt。`/root/.agents/skills/dashi-ppt/SKILL.md`
## ⚡ 最高频必触发规则
- **🔒 sessions_spawn 派发**：调用前必过3条：指定skill名，task含5字段（目标/约束/输入/验收/禁止），验收可客观判断。偏离锚点立即停。
- **🔒 语义退出条件**：执行型任务三类退出：✅完成/⏸️降级标`[PARTIAL]`/🛑中止回报。禁静默降级。
- **🔒 docx分层选择规则**：按复杂度选工具，禁python-docx作已有docx首选。详见 `基础设定/experience/docx_editing_rules.md`。
- **🔒 路由优先于执行**：复杂任务（>3步/工具歧义/数据采集分析）前跑路由脚本，写route_log.jsonl。简单任务记skip。
- **🔒 A股数据源规则**：K线iFinD>腾讯>akshare三级兜底，15:05后盘后校验。单源故障自动穿透。
- **🔒 A股交易硬约束**：建仓整手100股，禁亏损补仓和T-trading。
- **🔒 记忆检索协议v0.5**：索引优先4步，18用例77.8%达标。详见 `基础设定/experience/memory_retrieval_protocol_v05.md`。
- **🔒 高风险操作Control Policy**：{docx编辑/邮件/资金/删文件/改核心配置}必过3步校验，用户授权可例外。
- **🔒 route_log自动写入**：路由脚本自动写入，决策和skip都记。
- **🔒 评测持久化协议**：5类评测必出持久化文件+入索引，禁仅存在上下文。详见 `基础设定/experience/review_persistence_protocol.md`。
- **💡 Context Compression v1.0**：压缩前3条checklist，留记录。详见 `基础设定/experience/compression_v1_rules.md`。

## 规则变更日志
> 🔒规则修改需记录，凌晨流水线校验。历史条目仅留锚点。

- 💡 docx CLI边界：仅纯内容编辑，不处理严格格式
- **🔒 网页获取优先级**：Crawl4AI > scrapling > fetch_web
- 💡 风险标注协议：输出分[事实]/[决策]/[推测]三类
- 💡 topic_tracking推送去重：推送前校验历史答案
- 💡 话题追踪交付：日程日报走verify-run验收
- **🔒 规避损失算法**：Σ(卖价-当日收盘)×股数，时点数不累加
- 💡 流水线技巧：重跑/子会话校验/调度约束
- 💡 index_sync全量重建：支持full参数/关键词识别
- 💡 ima知识库：PDF解析/微信文章，200002重试
- **🔒 决策即记录**：重大决策24h内入decision log
- 💡 FUSE坑点：Python不可直建新目录
- 💡 元认知标签系统：3元标签，>3次反馈自动标候选
- 💡 CodeAct SDK坑点：call签名/S2自动补录等
- 💡 风控LLM约束：基准价优先iFinD收盘价，禁联网覆盖
- 💡 akshare指数修复：14指数白名单
- 💡 止损回测：胜率44.4%，新浪K兜底akshare
- 💡 iFinD降级：令牌超限/502立即标记不可用
- 💡 扫描v6.2提速：增量+粗筛+跨日续扫
- 💡 Scratchpad机制：复杂任务(≥3步)开scratchpad记中间状态，模板 `memory-arch/project/scratchpad_template.md`
- 💡 记忆最小化原则：只记需要的，不记能猜到的。详见 `memory-arch/memory_minimization_guidelines.md`
