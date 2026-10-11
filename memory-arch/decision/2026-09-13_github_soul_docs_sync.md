# GitHub 灵魂文档仓库 + 记忆架构同步机制

**日期**：2026-09-13
**类型**：架构变更
**状态**：已完成

---

## 背景

用户要求在 GitHub 新开一个仓库同步 SOUL.md 和 TOOLS.md，并将当日记忆架构的改动同步到之前的记忆架构仓库。

**目的**：建立外部同步机制，核心资产（灵魂设定、记忆架构）有外部副本，便于版本追踪和跨设备同步。

**触发条件**：架构变更（核心文件外同步机制）+ 用户确认执行。

---

## 决策内容

### 新建仓库

| 仓库 | 内容 | 首次提交 |
|------|------|----------|
| starnow600/agent-soul-docs | SOUL.md + TOOLS.md + README.md | 7f68ed6 |

### 已有仓库更新

| 仓库 | 更新内容 | commit |
|------|----------|--------|
| starnow600/agent-memory-framework | scratchpad模板 + 记忆最小化指南 + 长对话规则回顾 | 0030597 |

### 同步边界

- ✅ 同步：SOUL.md / TOOLS.md / 记忆架构核心文件
- ❌ 不同步：运行时数据（knowledge_nodes、feedback_log 等）

### 后续同步机制

- SOUL.md / TOOLS.md 有改动 → 同步推送到 agent-soul-docs
- 记忆架构改动 → 同步推送到 agent-memory-framework

---

## 行动项

- [x] 新建 agent-soul-docs 仓库（9/13 22:35完成）
- [x] 记忆架构仓库当日改动同步（9/13 22:35完成）
- [ ] 建立后续同步机制（手动/半自动）

---

## 验收标准

1. agent-soul-docs 仓库存在，包含 SOUL.md、TOOLS.md、README.md ✅
2. agent-memory-framework 仓库有当日改动 commit ✅
3. 运行时数据未带入（符合同步边界）✅

---

## 备注

**关联决策**：
- `decision/2026-09-13_system_prompt_upgrade.md`（SOUL体系升级，触发同步需求）

---

## 更新记录

| 日期 | 更新内容 |
|------|---------|
| 2026-09-13 | 初始创建：新建 soul-docs 仓库 + 记忆架构同步机制建立 |
