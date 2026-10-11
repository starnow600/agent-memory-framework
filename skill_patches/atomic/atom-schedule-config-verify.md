# atom-schedule-config-verify（日程配置修改后的反向验证）

**层级**: Atomic
**ID**: atom-schedule-config-verify
**触发**: 修改日程配置（描述、触发方式、参数、脚本路径）后
**来源**: 9/9每日自检日程修复教训：改了description但script_path没清除 → 实际执行模式没变 → 连续两天挂掉 → 删除重建才解决

---

## 失败模式

修改日程配置时，**只修改了description（或某个字段），但实际执行模式没改变**，导致"改了配置但效果没变"。常见于：
- 想把日程从"脚本模式"改为"工单模式"，只改了description，没清script_path
- 想修改触发频率，只改了description，没改rrule
- 想修改参数，只改了description，没改script_args
- 改完不验证，以为改好了，结果下次执行还是老样子

### 根因：description ≠ 实际执行模式

description是给人看的说明文字，不是实际执行逻辑。系统调度日程时看的是script_path、rrule、script_args等真正的执行字段，不是description。

如果修改日程的人（或agent）把description当成了"配置本身"，就会出现"我明明改了怎么还没生效"的困惑。

### 为什么会反复踩坑

1. **description的语义误导**：写得越详细的description，越容易让人误以为"这就是配置"
2. **calendar_update的API限制**：某些字段只能设置新值不能清除（如script_path），导致"想清掉清不掉"
3. **改完不验的惯性**：改完就走，不反向验证是否真的生效。如果是手动改的，更倾向于"我改了肯定对"
4. **跨日执行导致反馈延迟**：下次执行可能是第二天/下周，发现没生效时已经过了很久，排查成本高

---

## 约束

1. **日程配置修改后必须反向验证**
   - 修改完成后立即调用查询API（如calendar_get）确认目标状态
   - 验证清单：触发时间、执行模式（工单/脚本）、脚本路径、参数、时区
   - 核心原则：**信查询结果，不信自己"改了"的感觉**

2. **description与执行字段分离修改**
   - 改description ≠ 改执行模式
   - 要改执行模式，必须明确修改对应的执行字段（script_path/rrule/script_args）
   - 如果API无法清除某个字段（如script_path），采用"删除重建"而非"修改"

3. **模式切换类修改优先用删除重建**
   - 涉及执行模式根本性切换（工单↔脚本、DAILY↔WEEKLY等），优先删除旧日程创建新日程
   - 原因：修改模式可能有API限制（字段不能清除、隐含依赖等），删除重建更干净
   - 参考atom-schedule-transition-guard：新旧日程要有重叠期，不能"旧先停新未启"

4. **修改记录必须包含验证结果**
   - 不能只记"我改了X"，必须记"验证结果：Y字段已更新为Z值，符合预期"
   - 没有验证记录的修改 = 未完成的修改

### 与S1-Lite的关系

这是S1-Lite在"配置修改"场景的具体应用：
- S1-Lite通用原则：改完东西，验一下再发
- 日程配置场景具体化：改完日程，calendar_get确认生效再结束

属于S1-Lite v1.5扩展场景（配置类修改）。

---

## 为什么重要

9/8发现每日自检挂了（CodeAct沙箱缺sessions_list），当晚决定改回主agent触发。修改了schedule的description为"主agent触发"，以为改好了。

结果9/9又挂了——因为只改了description，script_path没清除，系统还是按CodeAct脚本模式执行。calendar_update API无法清除script_path字段，只能设置新值。

最后通过"删除旧日程 + 重新创建纯工单模式日程"才彻底解决。中间浪费了一整天。

这不是一个"操作失误"，而是一个**可复用的模式**：凡是涉及配置修改，都有"改了A但实际生效的是B"的风险。改完不验，等于没改。

---

## Source
- 9/9 每日自检连续第二天挂：改了description但script_path没清除 → 实际还是CodeAct模式
- 9/9 修复方案：删除旧日程 + 重新创建纯工单模式日程
- 相关trace：2026-09-10_daily_memory_capture.md（"description ≠ 执行模式"洞察）
- 相关decision：2026-09-09_risk_full_scan_architecture_optimization.md（背景中的运维调整）
- 配合规则：atom-schedule-transition-guard（日程切换的重叠期保障）

## Anti-pattern
- ❌ 改完description就以为配置改好了（description是给人看的，不是给系统执行的）
- ❌ 信自己"改了"的感觉，不信查询结果（感觉会骗人，API查询不会）
- ❌ 模式切换用修改而不是删除重建（API可能有字段限制，删重建更干净）
- ❌ 修改不记录验证结果（下次出问题不知道是"没改对"还是"改了但有新bug"）

## Related
- atom-schedule-transition-guard：日程切换的重叠期保障（本条是"切换是否成功"的验证保障）
- atom-schedule-time-range：日程时间范围配置注意事项
- func-s1-lite-expand-to-scheduled-reports：S1-Lite的扩展场景之一就是配置修改类
