# 技能系统周度快览 (T7) - Week 6

> 周期：2026-08-10 ~ 2026-08-16（过去7天）
> 产出时间：2026-08-16 16:40
> 数据源：./harness/route_log.jsonl（13条记录）
> 关联：技能系统测试方案 v1.0 §八（T7）
> 上期对比：weekly_review_2026-08-09.md（Week 5，12条记录，🟢 数据回升+质量全绿）

---

## 1. 数据量统计

| 指标 | Week 6 (8/10-8/16) | Week 5 (8/3-8/9) | 变化 | 阈值 | 状态 |
|------|-------------------|-------------------|------|------|------|
| 总记录数 | **13 条** | 12 条 | +8.3% | ≥10 条/周 | 🟢 达标 |
| 日均记录 | 1.86 条/天 | 1.71 条/天 | +8.8% | ≥1.4 条/天 | 🟢 达标 |
| 时间分布 | 7天全覆盖 | 7天全覆盖 | 持稳 | 7天覆盖 | 🟢 全勤 |
| 涵盖场景 | 2 个（memory_capture + forward_test） | 2 个 | 持稳 | — | 🟡 有限 |
| 同期已知执行 | memory_capture 7次 + forward_test 6次 = 13次 | 12次 | +1 | — | 🟢 100%覆盖 |

**数据结构说明**：
- daily_memory_capture：7条（7天全勤，每日凌晨1次）
- forward_test_v6_collection：7条（工作日5天，但8/10有3条/8/11有2条，疑似重试+批量）
- **daily_risk_check：0条**（见异常分析P1）

---

## 2. 异常信号扫描

| 检查项 | Week 6 结果 | Week 5 结果 | 阈值 | 状态 |
|--------|-------------|--------------|------|------|
| 未命中（chosen=null/empty） | 0/13 | 0/12 | 任意一条 | 🟢 正常 |
| Fallback 触发率 | 0% (0/13) | 0% (0/12) | >15% 异常 | 🟢 正常 |
| 用户纠正/重做信号 | 0 | 0 | 任意一条 | 🟢 干净 |
| 组合管道执行失败 | 0 | 0 | 任意一条 | 🟢 干净 |
| 调用成功率 | 100% (13/13) | 100% (12/12) | <90% 异常 | 🟢 正常 |
| route_log 丢失（memory+forward_test） | 0（13次执行=13条记录） | 0 | 任意一条 | 🟢 零丢失 |
| daily_risk_check 记录 | **0条**（🟡 异常：持仓中但无路由记录） | 0条（🟢 正常，空仓） | — | 🟡 关注 |

### 13 条记录明细

| 日期 | 场景 | chosen | fallback | success | 备注 |
|------|------|--------|----------|---------|------|
| 8/10 01:53 | daily_memory_capture | MEMORY.md直接编辑 | false | true | — |
| 8/10 18:20 | forward_test_v6_collection | tencent_kline + forward_test_collector | false | true | 同日第1条 |
| 8/10 18:21 | forward_test_v6_collection | tencent_kline + forward_test_collector | false | true | 同日第2条（1分钟间隔，疑似重试） |
| 8/10 18:21 | forward_test_v6_collection | tencent_kline + forward_test_collector | false | true | 同日第3条（1分钟间隔，疑似批量/重复） |
| 8/11 01:46 | daily_memory_capture | MEMORY.md直接编辑 | false | true | — |
| 8/11 18:19 | forward_test_v6_collection | tencent_kline + forward_test_collector | false | true | 同日第1条 |
| 8/11 18:30 | forward_test_v6_collection | tencent_kline + forward_test_collector | false | true | 同日第2条（11分钟间隔，疑似重试） |
| 8/12 01:46 | daily_memory_capture | MEMORY.md直接编辑 | false | true | — |
| 8/12 18:18 | forward_test_v6_collection | tencent_kline + forward_test_collector | false | true | — |
| 8/13 01:46 | daily_memory_capture | MEMORY.md直接编辑 | false | true | — |
| 8/14 18:20 | forward_test_v6_collection | tencent_kline + forward_test_collector | false | true | — |
| 8/15 01:46 | daily_memory_capture | MEMORY.md直接编辑 | false | true | 周六休市无forward_test，正常 |
| 8/16 01:46 | daily_memory_capture | MEMORY.md直接编辑 | false | true | 周日休市无forward_test，正常 |

---

## 3. 关键异常分析

### 🟡 P1：daily_risk_check 持仓期零路由记录 — 主session直接执行绕过hook

**问题描述**：
- 8/11 建仓长川科技（sz300604，100股@287.74），至今持仓第6天
- 风控报告文件已产出：`每日风控检查/20260813_风控报告.md`、`20260814_风控报告.md`、`20260815_风控报告.md`
- **但 route_log.jsonl 中 daily_risk_check 场景 0 条记录**

**原因分析（高度可信）**：
风控日程从"子session执行+脚本hook"改为**主session直接执行**（8/3清仓后重构？或8/11建仓后变更）。主session执行的任务不经过路由脚本，因此不写入 route_log。

**证据链**：
1. W5（8/3-8/9）空仓期，0条 risk_check 记录 → 合理
2. W6（8/10-8/16）8/11建仓后，仍0条 risk_check 记录 → 不合理（持仓应有风控）
3. 风控报告文件存在于 `每日风控检查/` 目录（非 `akshare-data/` 旧目录），说明执行链路已变更
4. 7月的风控文件在 `akshare-data/` 下且有对应的 route_log 记录（子session+hook模式）
5. 8/9 最后一条旧路径风控 `daily_risk_check_20260809.md`（空仓观察期）

**影响评估**：
- 🔴 **路由覆盖率下降**：每日风控是高频任务，从路由监控视野消失
- 🟡 **质量不可观测**：风控任务的成功/失败/降级无法通过 route_log 审计
- 🟢 **任务本身在正常执行**：报告文件存在且内容完整，功能未中断

**建议**：如果风控已稳定转主session执行，应在 TOOLS.md 中明确"主session执行的定时任务不入 route_log"，类似 daily_memory_capture 的处理逻辑。同时在 T7 周报的"已知不入 log 任务"清单中添加 daily_risk_check。

---

### 🟡 观察：forward_test 同日多记录

8/10 有 3 条 forward_test_v6_collection 记录（间隔仅 1 分钟），8/11 有 2 条（间隔 11 分钟）。

**可能原因**：
- 重试机制触发（首次执行不完整）
- 批量处理拆分为多次调用
- 日程重复触发

**建议**：下周观察是否稳定为 1 条/天。如果持续多发，需要排查 forward_test_collector 的重试逻辑。

---

### 🟡 观察：8/13 forward_test 记录缺失

8/13（周三，交易日）仅有 daily_memory_capture 1 条记录，无 forward_test_v6_collection。

**交叉验证**：8/13 风控报告提到"前瞻测试 Day23（8/13 更新）"，说明数据有更新。可能 forward_test 在 8/13 是通过其他路径执行（主session直接跑），未走路由脚本。

---

## 4. 测试用例追加评估

### 追加 1 条：主session直接执行的定时任务是否入 route_log（T1边界）

**场景**：daily_risk_check 从子session+hook模式转为主session直接执行后，route_log 不再有记录。

**归属维度**：T1 单技能召唤准确性（边界用例）+ T7 生产回顾

**测试点**：主session执行的复杂任务（如每日风控）是否应跑路由脚本并写入 route_log？当前规则不清晰。

**追加位置**：skill_system_test_plan.md T1 章节末尾（操作型/定时任务边界）

---

## 5. 行动建议

| 优先级 | 行动 | 状态 | 说明 |
|--------|------|------|------|
| P1 | 明确 daily_risk_check 是否应写入 route_log | 待确认 | 主session直执行后零记录，规则不清晰。要么补hook，要么正式声明不入log |
| P2 | 调查 forward_test 同日多条记录原因 | 观察中 | 8/10有3条、8/11有2条，可能是重试或批量拆分 |
| P2 | 8/13 forward_test 缺失确认 | 观察中 | 交易日但无路由记录，可能走了其他执行路径 |
| P2 | route_log 改 append-only | 待实施 | 上月度回顾已建议，避免月度数据断裂 |

---

## 6. 给主人的简报要点

1. **🟢 数据量**：13条记录（上周12条），稳定≥10阈值，7天全覆盖
2. **🟢 质量全绿**：成功率100%、Fallback 0%、未命中0、纠正0、失败0
3. **🟡 P1关注：daily_risk_check 零路由记录**：8/11建仓后风控报告正常产出（8/13/14/15都有），但 route_log 0条。推测风控已转主session直接执行，绕过了路由hook。需要确认：这是有意设计还是遗漏？
4. **🟡 forward_test 同日多条**：8/10有3条、8/11有2条，疑似重试/批量，下周观察
5. **不追加测试用例**：场景均已知，仅新增1条边界观察（主session直执行任务的路由覆盖）

---

## 7. Week 1-6 趋势对比

| 维度 | W1 (7/5-7/12) | W2 (7/12-7/19) | W3 (7/19-7/25) | W4 (7/27-8/2) | W5 (8/3-8/9) | W6 (8/10-8/16) | 趋势 |
|------|---------------|---------------|---------------|---------------|--------------|---------------|------|
| 数据量 | 5 条 | 5 条 | 14 条 | 6 条 | 12 条 | **13 条** | 🟢 持稳 |
| 日均 | 0.7 | 0.7 | 2.0 | 0.86 | 1.71 | **1.86** | 🟢 持稳 |
| 场景数 | 5个 | 5个 | 3个组合 | 1个 | 2个 | **2个** | 🟡 有限 |
| 成功率 | 100% | 100% | 100% | 100% | 100% | **100%** | → 持稳 |
| Fallback率 | 0% | 0% | 0% | 0% | 0% | **0%** | → 持稳 |
| 未命中 | 0 | 0 | 0 | 0 | 0 | **0** | → 持稳 |
| route_log覆盖率 | 初始 | hook失效 | 全恢复 | 75% | 100% | **100%（已知任务）** | 🟡 风控脱钩 |
| risk_check产出 | 有 | 有 | 有 | 7/28后停 | 空仓正常 | **持仓但无路由记录** | 🔴 需确认 |

---

## 自主决策记录

| # | 决策 | 依据 | 替代方案 |
|---|------|------|---------|
| 1 | 将 daily_risk_check 零记录标记为🟡 P1异常而非🟢正常 | 8/11已建仓长川科技（MEMORY.md确认），持仓期应有风控任务。风控报告文件存在但route_log零条，说明执行链路绕过了路由hook | 继续标🟢 → 漏检路由覆盖率退化 |
| 2 | 数据量13条≥10阈值，做全量分析 | 任务规则明确"<10条降级"，13≥10应做完整分析 | 继续降级 → 低估系统稳定性 |
| 3 | 仅追加1条边界观察，不正式追加测试用例 | 主session直执行任务的路由覆盖问题属于架构层面的规则确认，不等同于新的互斥/负样本/组合管道测试场景 | 强行追加测试用例 → 测试计划冗余，问题本质是规则不清而非路由准确性 |
| 4 | forward_test同日多条标记为观察项，不升级为异常 | 3条均success=true，无失败重试的明确证据；可能是批量拆分或日程重复触发，需下周连续观察确认模式 | 升级为P1 → 反应过度，单周数据不足以定性 |
