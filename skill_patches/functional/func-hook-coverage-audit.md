# func-hook-coverage-audit

## 触发条件
T7月度review执行时

## 操作步骤
1. 按场景拆分所有监控链（daily_risk_check / daily_memory_capture / forward_test_v6 等）
2. 对每条链统计：实际执行天数 / 应有执行天数 = 覆盖率
3. 验证原始数据完整性：`wc -l route_log.jsonl` + `ls traces/ | wc -l`，发现异常标注"数据不完整"而非直接算百分比
4. 按阈值标注状态：≥90% 🟢 / 50-89% 🟡 / <50% 🔴
5. 🔴链必须有明确整改行动项

## 关键约束
- 子session统计前**必须**先验证原始数据完整性（wc -l），不可直接基于不完整的文件算百分比
- route_log未纳入git追踪时，历史数据可能丢失——覆盖率统计需标注"仅统计当前文件内容"

## 来源
- 8/1 T7月度review首次引入hook覆盖率按场景拆分统计
- 8/1 主人质疑T7报告："13天无trace"实际9天，"route_log被清空"实为从未追踪
- 结论：T7的hook覆盖率数字不可靠，根因是统计逻辑问题+route_log未持久化
