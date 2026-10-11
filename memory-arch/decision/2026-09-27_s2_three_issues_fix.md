# S2加固期三问题修复决策

**日期**：2026-09-27  
**触发**：W12 S2周校准暴露3个问题，用户确认"周末跑"并要求修复全部

## 问题与修复

### 问题1：周末漏检（9条）
**根因**：daily_selfcheck_digest.py 仅工作日触发（日历WEEKLY byday MO-FR），周六周日无S2自动补录。  
**决策**：改为每日运行，含周末。  
**修复**：
- 日历事件"每日自检汇总（元认知规则生长）"rrule从 WEEKLY byday MO/TU/WE/TH/FR 改为 DAILY
- 描述同步更新："工作日22:00"→"每日22:00"，"5个已知日常子任务"→"9条已知日常子任务，含频率过滤"

### 问题2：周校准FS_PROBE_RULES不完整（5 vs 9条）
**根因**：weekly_s2_calibration.py 只写了初始5条规则，后续日检新增的4条未同步。  
**决策**：补齐4条规则并同步频率过滤逻辑。  
**修复**（weekly_s2_calibration.py）：
- 新增4个check函数：`_check_wiki_compile`、`_check_weekly_exploration`、`_check_weekly_invest_report`、`_check_skill_t7`
- 新增3个辅助函数：`_is_weekday`、`_is_sunday`、`_task_runs_today`
- FS_PROBE_RULES从5条扩充至9条，每条添加frequency字段
- `fs_probe_completed_sessions` 添加频率过滤（只探测当日应运行任务）

### 问题3：Wiki编译非周日误检（2条，09-22/09-23）
**根因**：双重——①周校准脚本无频率过滤；②Wiki编译频率标记不准确。  
**决策**：同步频率过滤 + 修正Wiki编译频率为daily。  
**修复**：
- weekly_s2_calibration.py 添加 `_task_runs_today` 频率过滤（同 daily_selfcheck_digest.py）
- daily_selfcheck_digest.py 中 wiki编译 frequency 从 weekly_sunday 改为 daily
  - 原因：Wiki现已扩展至 recent_memory 全量扫描（traces/decision/project/narratives），每日都有实际产出，不再是仅周日lint的周任务

## 验证结果
- 两脚本规则数一致：9条
- 所有规则名称+频率完全一致
- 周一应运行6条、周六4条、周日7条
- 周二无weekly_sunday任务通过频率过滤（误检根因已消除）
- 两脚本语法校验通过

## 相关文件
- `codeact/scripts/daily_selfcheck_digest.py` — wiki频率weekly_sunday→daily
- `codeact/scripts/weekly_s2_calibration.py` — 补齐4条规则+频率过滤
- 日历事件：每日自检汇总（DAILY，22:00）
