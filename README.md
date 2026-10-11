# 杨小壶 · 记忆与认知体系

个人 Agent 的核心资产仓库——记忆系统、元认知规则、技能补丁体系、决策记录。

## 目录结构

```
soul-docs/           灵魂设定（SOUL.md / TOOLS.md）
memory-arch/
├── decision/        决策记录（架构变更、规则演进、重大事件）
├── narratives/      每日叙事（因果链视角的当日总结）
├── traces/          每日记忆捕获 trace
├── rules/           规则库（策略规则、行为规则、元认知规则）
├── project/         项目报告（校准报告、里程碑）
└── src/             记忆系统源码脚本
skill_patches/       技能补丁体系（Planning / Functional / Atomic 三层）
├── planning/        顶层规划策略
├── functional/      功能级技能补丁
├── atomic/          原子级避坑规则
├── scripts/         路由决策脚本
└── index.json       补丁索引
harness/            技能系统监控与评测
graphify-out/       记忆图谱可视化产物
```

## 设计原则

- 记忆分层：即时层（SOUL/MEMORY）→ 近中期（decision/narrative）→ 长期（Wiki/图谱）
- 元认知驱动：S1 交付前自检 + S2 子任务验收 + 周校准
- 技能补丁：从失败中蒸馏可复用的避坑规则，三层架构持续生长

