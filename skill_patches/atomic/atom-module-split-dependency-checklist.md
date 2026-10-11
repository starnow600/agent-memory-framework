# atom-module-split-dependency-checklist

**代码拆分/迁移时必须有依赖checklist——主逻辑+全局变量+import+工具函数+调用方引用，五件事一个都不能少**

## 触发条件
将代码从一个文件/模块拆到另一个文件/模块时（模块化重构、渐进式披露、抽取公共库、适配器拆分等）

## 规则
代码拆分不是"把函数搬走"那么简单，必须逐项检查以下5类依赖，形成checklist逐一打勾：

1. **全局变量/状态标志**：`_MCP_ADAPTER_AVAILABLE`、`AVOIDED_LOSS_RECORDS` 等模块级变量，是否一起搬了？搬到新模块后，旧模块的引用是否更新了前缀？

2. **import 语句**：新文件是否有完整的import？注意import方式可能不一致（`import datetime` vs `from datetime import datetime`），函数体里的调用方式要和import对应。

3. **工具函数/辅助函数**：主逻辑调用的私有工具函数（如 `_write_route_log`、`_parse_kline_data`），是否一起搬了？还是需要保留在原模块通过import引用？

4. **调用方引用**：其他文件引用了被移动的变量/函数吗？如果有，所有调用方的import路径都要更新。拆分漏项的第4例就是——变量搬到data_layer了，主脚本的引用没改前缀。

5. **异常处理**：try/except 包裹的逻辑，异常是被吞掉了还是会上报？静默失败的代码，bug藏得最深（如S2探测函数的try/except Exception吞掉了import错误，18天没发现）。

## 验证要求
- 拆分完成后，必须同时验证 **fast模式** 和 **full模式**（如果有多个运行模式）
- 不能只验"能不能跑"，要验"输出对不对/全不全"
- 有单元测试的，拆分后先跑单元测试再跑集成测试
- 对于有多个入口的系统（cron/手动/子任务），每个入口都要验证

## 为什么是Atomic层
这是代码拆分时的具体操作约束，每一次拆分都应该对照这个checklist检查。它是单动作（拆分代码）的扩展约束，不是流程层面的规划问题。

## 来源
- 10/7 S2探测规则统一：`import datetime` 却用 `datetime.strptime`，三个探测函数静默失败18天（import方式不匹配 + try/except吞异常）
- 10/8 风控data_layer拆分漏3个依赖：`_MCP_ADAPTER_AVAILABLE` 全局变量 + `timedelta` 导入 + `_write_route_log` 函数
- 10/9 第4例漏项：`AVOIDED_LOSS_RECORDS` 变量搬到data_layer了，主脚本引用没改前缀
- 4例同一模式：拆分只搬主逻辑，依赖项没带全
- 来源叙事：
  - 2026-10-08_daily_narrative.md（核心叙事：统一即放大 + try/except是bug藏身之所）
  - 2026-10-09_daily_narrative.md（核心叙事：拆分依赖遗漏是系统性问题）
  - 2026-10-10_daily_narrative.md（核心叙事：第4例AVOIDED_LOSS_RECORDS + 验证深度不足）

## 相关Patch
- **atom-field-migration-check**：迁移后检查字段引用兼容性，本条是拆分/迁移时的事前checklist——一个事前一个事后，互补
- **plan-change-impact-and-verify**：变更管理的宏观框架，本条是代码拆分这个具体变更场景的执行checklist
- **func-optimization-uncovers-bugs**：优化/重构会发现隐藏bug，本条是减少重构本身引入bug的方法
