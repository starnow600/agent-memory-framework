# atom-field-migration-check

## Trigger
系统迁移/升级后，涉及已有脚本/代码的字段引用时

## Rule
迁移完成后必须检查所有下游脚本/代码的旧字段引用兼容性。检查项：(1)字段名是否变更 (2)字段类型是否变更 (3)字段是否已废弃。验证方式：运行受影响脚本的dry-run/import测试，捕获AttributeError等引用错误。

## Why
7/17 LLM Verifier论文迁移实施后，runner.py仍引用旧字段(mode_score/variance)→AttributeError。字段映射已更新(mean_score/cv)但下游脚本未同步检查。修复：P0-001 24h闭环。

## Source
7/17 runner.py字段兼容问题 + P0-001修复
