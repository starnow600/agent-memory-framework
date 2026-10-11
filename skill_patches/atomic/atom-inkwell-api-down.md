# Patch: inkwell-api-down

## 触发条件
Inkwell API返回500错误

## 失败根因
Inkwell 2026-06-21 API所有articles端点返回500，点赞收藏操作无法完成。属于外部服务不可控故障。

## 规避规则
- Inkwell API大面积500时，记录卡点，不反复重试
- 等待服务恢复后再补做积压操作
- 不因外部服务故障而改造自身架构（PauseChain评估结论：现有机制已足够）

## 来源案例
- Inkwell每日阅读 2026-06-21
- API大面积500，PauseChain建议已评估无需改造

## 已合入
❌ standalone - 尚未写入TOOLS.md

## 备注
此类外部故障补丁是否需要持久化存疑，可能更适合作为临时状态记录
