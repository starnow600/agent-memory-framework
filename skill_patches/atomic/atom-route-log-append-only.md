# atom-route-log-append-only

## 触发条件
任何脚本/子session需要写入route_log.jsonl时

## 规则
route_log.jsonl必须append-only写入（`>>` 或 open('a')），禁止覆盖写入（`>` 或 open('w')）。同时必须纳入git追踪，防止数据丢失。

## 来源
- 7/26-7/28丢失约19条历史数据（T7月度review发现）
- route_log从未被git追踪（8/1验证：`git log --all -- harness/route_log.jsonl`返回空）
- 8/1整改：route_log和compression_traces已纳入git commit
