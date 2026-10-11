# Atomic: sessions_spawn必须指定技能+含验收

## 触发条件
调用sessions_spawn派发任务

## 规则
1. 扫描技能→显式指定skill名
2. task含5字段：目标/约束/输入/验收/禁止
3. 验收条件必须可客观判断

## 反面教训
6/4未指定create-ppt→子session用python-pptx重建→模板丢失

## 来源
- TOOLS.md sessions_spawn派发规则
