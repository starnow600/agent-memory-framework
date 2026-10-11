# 2026-10-11 风控cron调度根因修复：工单描述模式→脚本直调

## 一、根因

### 现象
- 10/9 主风控全市场扫描超时，只扫了 10/1587 只
- `daily_scan_progress_20261009.json`：status=running，daily_mode=full，coarse_screen=False

### 初步误判
- "10/9 跑的是 fast 模式" → 错
- "cron 参数被改成了 full" → 不完整

### 真正根因
原日程是**工单描述模式**（无 `script_path`，无 `script_args`），summary 写"（CodeAct脚本）"但实际是子 agent 读 description 理解后执行。
- 子 agent 质量不稳定时，可能不按 description 里写的"incremental 模式"传参
- 脚本默认值 `daily_mode="full"` + `coarse_screen="false"`
- 结果：跑了 full + coarse=off，1587 只全量，超 CodeAct 600s 上限 → 中断在第一批 10 只

### 证据
| 日期 | 模式 | coarse | 完成数 | 状态 |
|------|------|--------|--------|------|
| 9/28-10/6 工作日 | incremental | True | 50/50 | done ✅ |
| 9/11（周五） | full | False | 300/1587 | running（iFinD超限） |
| 10/9（周四） | full | False | 10/1587 | running（超时） |

9/14-10/6 期间子 agent 正确执行了 incremental，但 10/9 失败 → 证实**描述模式不可靠**，和 9/19 S2 加固期发现的"纯工单模式质量不稳定"是同一问题。

---

## 二、修复方案

把风控日程从"工单描述模式"改为 **CodeAct 脚本直调模式**（设置 `script_path` + `script_args`），参数硬编码，不依赖子 agent 理解。

### 两个日程

| 日程 | 频率 | 参数 | 说明 |
|------|------|------|------|
| 工作日增量（原日程改造） | 周一~周四 17:00 | `notify full --daily-mode incremental --coarse-screen` | ~50 只，2 分钟内完成 |
| 周五全量（新建） | 周五 17:00 | `notify full --daily-mode full --no-coarse-screen` | 1587 只，周度兜底 |

原日程 UID 保持不变（`ba6f7cc8-b255-4816-91f7-0affda7e223c`），因 rrule 从 MO-FR 改为 MO-TH，系统自动 split 为新分段。
新周五全量 UID：`b931cbad-1708-465b-b8da-6358369062fa`

---

## 三、验证计划

- **10/13（周一）首个验证日**：检查 `daily_scan_progress_20261013.json`
  - daily_mode = incremental ✅
  - coarse_screen = True ✅
  - status = done ✅
  - total ≈ 50 ✅
- **10/16（周五）**：验证全量模式正常
- 连续 3 个工作日达标 = 修复生效

---

## 四、关联教训

- **描述模式≠脚本模式**：summary 里写"CodeAct脚本"不代表就是脚本触发，必须设置 `script_path`
- **设计-执行断层**：9/12 决策"工作日默认 incremental"只改了 description，没改脚本默认值也没设 script_args → 靠子 agent 理解执行，不可靠
- **变更管理验证深度不足**：这是第 10 期 Review 🔴 问题的又一例（架构变更没端到端验）

---

*记录时间：2026-10-11 | 触发分类：架构修复 / cron调度*
