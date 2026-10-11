# atom-schedule-time-range

## Trigger
配置涉及时间窗口的日程/调度任务时

## Rule
时间窗口敏感的任务必须配置time_range参数。requires_time_range=true但未配置=调度时无优先级保护，会在资源竞争中被挤出（尤其凌晨多任务并发时段）。配置后需验证：删除重建确保生效。

## Why
7/18凌晨流水线Step 1(记忆捕获)和Step 3(图谱增量)失败。根因：日程配置requires_time_range=true但实际未配置time_range，导致凌晨多任务并发时被资源竞争挤出。修复后所有5步均配置time_range，7/19凌晨首次验证通过。

## Source
7/18 time_range缺失导致流水线部分失败 + 修复验证
