# 决策日志：索引同步从子session迁移为CodeAct脚本

**日期**：2026-08-14 启动 → 2026-08-15 凌晨完成
**类型**：架构变更 / 任务迁移
**重要性**：高
**决策人**：杨小壶（主人确认后执行）

---

## 背景

索引同步是每日凌晨流水线的最后一步（记忆捕获→图谱增量→叙事review→Wiki编译→**索引同步**），负责将当日新增的decision/project/trace条目同步到检索索引，供memory_search召回。

### 故障触发
- **8/13凌晨**：子session沙箱启动失败（RPC超时），基础设施层故障
- **8/14凌晨**：子session ChatModel超出最大迭代次数，索引同步步骤挂掉
- **影响**：连续2天索引未同步，8/12-8/14新增的decision/project条目未进入检索链路

### 根因分析
| 日期 | 错误类型 | 直接原因 | 根因 |
|------|---------|---------|------|
| 8/13 | sandbox start failed (RPC超时) | 沙箱环境启动失败 | 平台抖动，与改造无关 |
| 8/14 | ChatModel exceeds max iterations | 子session迭代超限 | 日程description仍指向旧版unified_index.json链路，PlugMem改造后索引结构变更但description未同步，子session反复找文件耗尽迭代 |

**本质问题**：子session模式不稳定（平台抖动+逻辑漂移双重风险），且description维护滞后于架构变更。

---

## 决策内容

### 方案：索引同步从子session模式迁移为CodeAct脚本触发
1. **脚本化**：开发 `codeact/scripts/index_sync.py`，将索引同步逻辑固化为确定性Python脚本
2. **索引统一**：旧 `unified_index.json` 的40条全量迁入新体系 `memory-arch/recent_index.json`
3. **日程切换**：旧Calendar子session日程替换为CodeAct脚本触发，每日凌晨3:45自动执行
4. **路径调整**：原定 `recent_memory/index.json` → 实际 `memory-arch/recent_index.json`（FUSE顶层不可写，与知识节点索引同目录更合理）

### 验证结果
- ✅ 40条旧索引全量迁入新体系
- ✅ 幂等性测试通过（连续运行无重复）
- ✅ decay衰减机制正常
- ✅ 首次试跑验证通过（8/15 01:13）
- ✅ 日程已切换，下一次自动运行：8/16凌晨3:45

### 遗留小项
- Git commit因index.lock卡住已清理
- MEMORY.md在git里显示deleted，凌晨同步时应自动恢复

---

## 影响范围

| 维度 | 变化 |
|------|------|
| 可靠性 | 子session不稳定 → 脚本确定性执行，预计故障率大幅下降 |
| 索引格式 | unified_index.json → memory-arch/recent_index.json（PlugMem体系） |
| 维护成本 | 无需维护子session description，改脚本更可控 |
| 检索一致性 | 修复了连续2天索引断档的问题 |

---

## 后续行动
- [ ] 下周一（8/17）观察首次自动运行结果
- [ ] 验证Git commit恢复正常
- [ ] 如稳定，考虑将其他凌晨子session任务也迁为CodeAct脚本
