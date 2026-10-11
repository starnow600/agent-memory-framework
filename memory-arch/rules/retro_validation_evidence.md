# 元认知规则回溯验证 — 证据文件

**回测周期**：2026-08-01 ~ 2026-08-30
**证据来源**：memory_search对话记录、决策文档、初筛报告、规则库JSON
**生成日期**：2026-08-30

---

## P类事件证据块（问题事件）

### P01: 持仓预警脚本bug — 异常被误报为disk I/O error

Claim: 8/12持仓预警脚本在submit_result失败时，异常被捕获后错误地报成了"disk I/O error"，导致误导性的错误信息；实际数据已正常写入，仅上报环节出问题。
Source: 对话记录 2026-08-12
URL: memory_search 2026-08-12 18:59:27
Date: 2026-08-12
Excerpt: "Bug原因：脚本最后提交结果时连不上本地SDK端口（9999），异常被捕获后错误地报成了'disk I/O error'。实际数据已正常写入。"
Context: 这是一个代码层面的错误信息映射问题——网络连接失败被笼统地归类为磁盘IO错误，属于异常处理不严谨。
Scope fit: IN-SCOPE
Confidence: HIGH

### P02: 拍脑袋估计数据 — "你倒是算一下啊"

Claim: 8/12用户指出我在给出数据结论时拍脑袋估计，没有实际计算验证，用户原话"你倒是算一下啊"。
Source: 对话记录 2026-08-12
URL: memory_search 2026-08-30 21:49:49（证据链引用）
Date: 2026-08-12
Excerpt: "8/12你说'你倒是算一下啊'——我拍脑袋估计数被你怼了"
Context: 这是S009"先验后断原则"的核心证据事件之一，属于用户反复纠正的高频问题模式。
Scope fit: IN-SCOPE
Confidence: HIGH

### P03: 索引同步mtime增量失效 — 漏扫22条

Claim: 8/17发现索引同步增量识别逻辑依赖mtime，但云盘环境中mtime全为1970年，导致持续漏扫。全量回扫后发现漏了22条（从45条增至67条）。
Source: 对话记录 2026-08-17
URL: memory_search 2026-08-17 10:07:10
Date: 2026-08-17
Excerpt: "全量回扫完成。结果：45 → 67条，新增22条。之前因mtime bug漏的8/14、8/15文件"
Context: 增量系统依赖不可靠的增量识别逻辑（mtime），导致静默漏扫且不易发现。修复方案是新增--full全量重建参数。
Scope fit: IN-SCOPE
Confidence: HIGH

### P04: 子session迭代超限（8/12持仓预警相关）

Claim: 8/12凌晨子session执行失败（max iterations超限），需要主session手动确认和补救。
Source: 对话记录 2026-08-12
URL: memory_search 2026-08-12 04:47:10
Date: 2026-08-12
Excerpt: "子会话执行失败（max iterations超限），看session_id是7672862294120071439。先确认是哪个任务。"
Context: 子session因迭代次数超限而中止，属于子任务执行失败的典型场景。
Scope fit: IN-SCOPE
Confidence: HIGH

### P05: 子session迭代超限（8/20）

Claim: 8/20子session迭代次数超限，还没跑完就挂了，需要主session接手。
Source: 对话记录 2026-08-20
URL: memory_search 2026-08-20 19:36:13
Date: 2026-08-20
Excerpt: "子session迭代次数超限了，还没跑完就挂了。我先看一下当前脚本改到什么程度了。"
Context: 又一次子session超限失败，说明这是一个反复出现的模式问题。
Scope fit: IN-SCOPE
Confidence: MEDIUM

### P06: JitRL评测报告核心数据全错 — 53.3% vs 实际76.7%

Claim: 8/26 JitRL与记忆系统融合评估报告中，冷启动Top-1准确率数据错误（报告写53.3%，实际测试为76.7%），评测脚本算错了。用户说"报告里的数据全错了"。
Source: 对话记录 2026-08-26
URL: memory_search 2026-08-26 02:22:14
Date: 2026-08-26
Excerpt: "报告里的数据全错了。我重新写一份正确的。" "实际测试冷启动Top-1=76.7%，和基线持平。报告里的53.3%大概率是评测脚本算错了"
Context: 核心数据错误来自有问题的评测脚本，交付前未做自证校验。用户直接指出错误后才返工修复。
Scope fit: IN-SCOPE
Confidence: HIGH

### P07: 风控报告紫光持股和成本价错误

Claim: 8/26风控报告中紫光股份的持股数量和成本价错误，用户指出"报告中紫光的持股和成本价错误"。
Source: 对话记录 2026-08-26
URL: memory_search 2026-08-26 17:54:57
Date: 2026-08-26
Excerpt: "报告中紫光的持股和成本价错误"
Context: 交付的报告中核心数据不准确，需要用户指出后修正。
Scope fit: IN-SCOPE
Confidence: HIGH

### P08: 速览消息手动打错价格 — 长川/紫光两个都写错

Claim: 8/26在速览消息中手动敲错了长川科技和紫光股份的收盘价和涨跌幅（长川写成269/-0.23%实际276.20/+4.77%，紫光写成34.30/-2.43%实际34.90/-0.57%），两个数字都错，属于低级错误。
Source: 对话记录 2026-08-26
URL: memory_search 2026-08-26 17:57:12
Date: 2026-08-26
Excerpt: "长川科技：276.20元，+4.77%（我写成了269/-0.23%，错）；紫光股份：34.90元，-0.57%（我写成了34.30/-2.43%，错）。两个都写错了，低级错误。"
Context: 口头速览时手敲数据出错，报告文件本身是对的，但快速总结时出错。属于交付数据自证的边缘场景。
Scope fit: IN-SCOPE
Confidence: HIGH

### P09: 小问题拖延 — "路线粘连bug等下次修"

Claim: 8/23用户纠正"路线粘连bug等下次修"的拖延习惯，指出攒着下次修会累积成技术债。当天新增🔒级"小问题即改"规则。
Source: 对话记录 2026-08-23
URL: memory_search 2026-08-23 08:46:25 + 11:37:59
Date: 2026-08-23
Excerpt: "还没处理，之前计划等下次有内容编译时一并修复。" "发现一个问题：当前有两条重复的'小问题即改原则🔒'"
Context: 小bug发现后不立即修，拖延到下次有相关任务时一并处理，这是一种会累积技术债的不良习惯。
Scope fit: IN-SCOPE
Confidence: HIGH

### P10: Phase 1子会话挂了 + 核心产物写完但不完整

Claim: 8/26 PlugMem Phase 1子会话因迭代超限挂掉，后来发现核心产出其实写完了，但部分内容（如速查表）遗漏。主session需要验货并补全。
Source: 对话记录 2026-08-26
URL: memory_search 2026-08-26 01:37:21 + 02:09:04
Date: 2026-08-26
Excerpt: "Phase 1子会话挂了（超过最大迭代次数）。我重开一个，减少任务范围，聚焦核心目标。" "子session两次都在迭代上超限，但看文件列表核心产出其实写完了。我来验货，缺的我自己补。"
Context: 子任务执行不完整，需要主session验收和补救。这是"子任务验收制"规则的典型反面案例。
Scope fit: IN-SCOPE
Confidence: HIGH

### P11: 凌晨任务遗漏 — 缺失两天的内容

Claim: 8/14用户指出凌晨任务有缺失，"我记得前天的凌晨任务也有问题"，说明定时任务执行有遗漏且未被及时发现。
Source: 对话记录 2026-08-14
URL: memory_search 2026-08-14 18:45:24
Date: 2026-08-14
Excerpt: "所以缺失的任务是不是包含了两天的内容，我记得前天的凌晨任务也有问题"
Context: 定时任务执行不完整但未被自动检测到，属于任务执行监控的盲区。
Scope fit: IN-SCOPE
Confidence: MEDIUM

### P12: Wiki缺编译未及时处理

Claim: 8/23用户问起时才发现Wiki缺的编译还没处理，之前计划"等下次有内容编译时一并修复"，属于拖延+遗漏。
Source: 对话记录 2026-08-23
URL: memory_search 2026-08-23 08:46:25
Date: 2026-08-23
Excerpt: "还没处理，之前计划等下次有内容编译时一并修复。既然你问了，现在就补上。"
Context: 与P09同类——小问题拖延不立即处理，攒着等"一并修"。
Scope fit: IN-SCOPE
Confidence: HIGH

---

## S类事件证据块（成功事件）

### S01: Caveman叙事review双轨验证成功（8/3-8/9）

Claim: 8/3-8/9共7天双轨并行验证（压缩版Caveman vs 原版），7天零失败、零纠正，凌晨5步流水线全绿，最终Caveman版本稳定性验证达标，下线旧版。
Source: 对话记录 2026-08-09
URL: memory_search 2026-08-09 03:34:11
Date: 2026-08-09
Excerpt: "8/3-8/9共7天双轨并行验证。结果：7天零失败、零纠正、凌晨5步流水线全绿。结论：Caveman版本稳定性已验证达标。建议：下线旧版同步流水线，只保留Caveman版本"
Context: 这是S001影子测试方法论的典型成功案例——新老版本并行运行，对比验证后再切换。
Scope fit: IN-SCOPE
Confidence: HIGH

### S02: v6.0前瞻测试并行运行（8/3-8/15）

Claim: 8/3起v6.0前瞻测试与v5.x版本并行运行，追踪948+只股票，8/15截止后评估效果。同时smevals因子快验也并行运行做对比。
Source: 对话记录 2026-08-02 ~ 08-03
URL: memory_search 2026-08-02 14:46:21
Date: 2026-08-03
Excerpt: "v6.0前瞻测试：工作日18:07，MO-FR，至8/15，累计追踪948+只" "两套并行对比，8/6开始出对比数据"
Context: v6.0算法升级采用前瞻测试（影子模式），与现有版本并行运行收集数据，验证通过后再考虑切换。
Scope fit: IN-SCOPE
Confidence: HIGH

### S03: 全市场扫描接入 — 子任务验收制首次实战6项全过

Claim: 8/19全市场v6.0扫描接入风控流水线，子任务验收制首次实战，6项验收标准全部通过。先给出方案A vs方案B供用户选定后才执行。
Source: 决策文档 2026-08-19 + 对话记录
URL: initial_screening_report.md S003证据链
Date: 2026-08-19
Excerpt: "6项验收标准（脚本模块/扫描范围/三产物完整性/报告章节/index注册/试跑通过），子任务验收制首次实战6项全过"
Context: 这是S003子任务验收制和R009大任务确认制的成功实践——先确认方案，后验收产物。
Scope fit: IN-SCOPE
Confidence: HIGH

### S04: 数据源切换+批量优化 — 提速35倍

Claim: 8/20数据源从腾讯API切换为iFinD，同时做批量K线优化。决策一7项验收+决策二7项验收，全部通过后才标记完成，实际提速35倍。
Source: 决策文档 2026-08-20
URL: initial_screening_report.md S003/S001证据链
Date: 2026-08-20
Excerpt: "决策一7项验收、决策二7项验收，全部通过后才标记完成，实际提速35倍"
Context: 数据源切换是高风险操作，采用先验证后切换的策略，配合子任务验收制确保质量。
Scope fit: IN-SCOPE
Confidence: HIGH

### S05: 索引同步mtime bug修复 — 增量+全量双模式

Claim: 8/17索引同步mtime bug发现后，通过新增--full全量重建参数快速补回22条遗漏。日常用增量模式提升效率，全量模式作为兜底。
Source: 决策文档 2026-08-17
URL: memory_search 2026-08-17 10:07:10
Date: 2026-08-17
Excerpt: "附带修复：脚本新增--full全量重建模式，以后再遇到类似问题直接全量扫一遍就行。"
Context: 这是S005"增量为主+全量兜底"策略的成功实践——增量出问题时全量模式作为安全网。
Scope fit: IN-SCOPE
Confidence: HIGH

### S06: PlugMem L0摘要预取改造 — Benchmark验证后上线

Claim: 8/23 PlugMem L0层改造后，先跑Benchmark验证（Recall不下降+L0命中率显著提升双条件），确认效果后再正式上线，不影响L1/L2现有功能。
Source: 决策文档 2026-08-23
URL: initial_screening_report.md S001证据链
Date: 2026-08-23
Excerpt: "L0层改造后先跑Benchmark验证（Recall不下降+L0命中率显著提升双条件），确认效果后再正式上线"
Context: 影子测试方法论在记忆系统改造中的应用——先验证效果，再正式上线，不影响现有功能。
Scope fit: IN-SCOPE
Confidence: HIGH

### S07: PlugMem价值化升级 — 方案B分4Phase渐进推进

Claim: 8/26 PlugMem价值化升级采用方案B（中度融合），分4个Phase渐进实施（Phase0基线→Phase1价值重排序→Phase2质量闭环→Phase3 C方案预评估），每阶段有独立验收节点。
Source: 决策文档 2026-08-26
URL: initial_screening_report.md S002证据链
Date: 2026-08-26
Excerpt: "分4个Phase渐进实施，每阶段有独立验收节点，Phase3结束后设Go/No-Go决策门"
Context: 这是S002渐进式上线策略的典型成功案例——大项目分阶段推进，每阶段有Gate验收。
Scope fit: IN-SCOPE
Confidence: HIGH

### S08: 风控专家知识编码 — 4周影子测试+3个Gate

Claim: 8/30风控技能专家知识编码完成冒烟测试，启动4周影子测试计划，设3个Gate验收节点（Gate0编码完成/Gate1稳定性/Gate2中期评估/Gate3最终验收），通过后分三步转正。
Source: 决策文档 2026-08-30
URL: initial_screening_report.md S001/S002证据链
Date: 2026-08-30
Excerpt: "4周影子测试（9/1~9/28），两套系统共用输入、独立输出、每日自动diff。4个核心硬指标：一致性≥95% / 完整性100% / 漏报≤1次 / 误报≤3次"
Context: 影子测试+渐进式上线的组合应用，是S001和S002两条策略规则同时发挥作用的典型场景。
Scope fit: IN-SCOPE
Confidence: HIGH

---

## 规则覆盖映射表

| 事件ID | 对应规则 | 规则类型 | 场景分类 |
|--------|----------|----------|----------|
| P01 | S012 故障归因分层排查 / R018 先排自身问题 | 策略+禁令 | 故障排查 |
| P02 | S009 先验后断原则 | 策略 | 交付结论 |
| P03 | S005 增量+全量兜底 / S012 故障分层排查 | 策略+策略 | 工程架构 |
| P04 | S003 子任务验收制 / R007 子session验收 | 策略+禁令 | 子任务派发 |
| P05 | S003 子任务验收制 / R007 子session验收 | 策略+禁令 | 子任务派发 |
| P06 | S010 交付数据自证 / S009 先验后断 | 策略+策略 | 交付质量 |
| P07 | S010 交付数据自证 / R017 用户陈述验证 | 策略+禁令 | 交付质量 |
| P08 | S010 交付数据自证 | 策略 | 交付质量 |
| P09 | R010 小问题即改 / S011 问题分级响应 | 禁令+策略 | 问题处理 |
| P10 | S003 子任务验收制 / R008 语义退出规范 | 策略+禁令 | 子任务派发 |
| P11 | S006 幂等保护 / R006 评测持久化 | 策略+禁令 | 任务监控 |
| P12 | R010 小问题即改 / S011 问题分级响应 | 禁令+策略 | 问题处理 |
