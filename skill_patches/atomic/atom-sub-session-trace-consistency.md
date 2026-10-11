# atom-sub-session-trace-consistency

## 触发条件
子session执行任务需要写入trace文件时

## 规则
子session执行任务时必须同时写入route_log和trace文件。缺一=hook执行不完整。验收时检查两者是否匹配：
- route_log有记录+trace有文件=✅完整
- route_log有记录+trace无文件=⚠️hook不完整
- route_log无记录+trace无文件=❌未执行

## 来源
- 7/29-7/31 route_log有记录但无对应trace文件（8/1验证）
- 子session对hook写入的执行不一致：有时写route_log但漏写trace
- 8/1整改：memory capture日程description明确"trace写入是必须步骤，不是可选产出"
