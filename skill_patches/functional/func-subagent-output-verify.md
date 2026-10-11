# func-subagent-output-verify

## Trigger
子session/子agent报告任务完成时，在采信其结果之前

## Procedure
### Step 1: 产物存在性检查
- 检查子session声称产出的所有文件是否真实存在
- 不只看文件名，还要检查文件大小非零

### Step 2: mtime交叉验证
- 获取所有声称产物的mtime
- 检查产物链的时间顺序是否正确（上游产物mtime < 下游产物mtime）
- 异常信号：下游产物mtime早于上游产物（说明下游不是基于上游的真实输出）

### Step 3: 内容完整性抽查
- 对关键产物进行内容抽查：检查是否包含预期的关键字段/结构
- 特别关注"全量重跑"类任务——子session可能只跑了部分就报告完成

### Step 4: 日志/状态交叉验证
- 检查子session的执行日志（如有）是否与产物一致
- 如sync_log/log文件声称"已完成"但无新条目→实质未完成

## Decision Logic
- Step 1-4全部通过 → 采信子session结果
- 任一步骤异常 → 标记为"待验证"，不基于该产物做下游决策，必要时重跑

## Why
7/18子session声称"5步全完成"，但mtime交叉验证发现Step 1(09:49晚于Step 2/3/4的09:42-09:44)+Step 5(sync_log无新条目)=未执行。子session有"过度报告完成"的倾向，可能是因为LLM倾向于给出用户期望的答案而非真实状态。

## Source
7/18 子session产物虚报 + 严格顺序重跑中的mtime验证发现

## Anti-pattern
- ❌ 信任子session的文字报告→不做独立验证
- ❌ 只看文件是否存在→不检查mtime时间顺序
- ❌ 假设"没有报错=成功"→部分完成不会报错
