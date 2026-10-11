# atom-v11-miss-detection

## Trigger
v1.1协议检测规则同步状态 / TOOLS.md变更日志审计 / 规则新增后的48h内

## Rule
v1.1协议miss（漏登）的检测与处理：

### 检测信号
- 变更日志最后日期距当前>7天 = 漏登信号
- MEMORY.md新加🔒规则但TOOLS.md变更日志未登记 = 漏登信号
- 主人新加/修改规则但unified_index.json未更新 = 漏登信号

### 检测方法（自动+手动）
- **自动**：每72h扫描一次TOOLS.md变更日志最后日期
- **手动**：每次添加🔒规则后立即检查unified_index.json一致性
- **复检**：每次review检查"漏登候选"清单

### 处理流程
1. **识别**：扫描最近添加的规则 vs 变更日志最后条目
2. **补登记**：按格式 `"YYYYMMDD | 规则名 | 来源"` 追加到变更日志
3. **追溯源**：找到规则的实际添加时间/触发事件（避免凭印象）
4. **更新unified_index.json**：确保新规则的索引条目存在
5. **下次review优先验证**：48h后复检漏登是否被吸收

## Why
7/24 10:42 TOOLS.md新加🔒规则PPT路由（dashi-ppt/create-ppt/article-to-ppt），但变更日志最后=07-16，7天漏登。7/24 17:00 review#24未识别。7/25 03:54 status更新才标注"v1.1协议miss"+7/24 4:20需自检+补登记。**核心教训**：v1.1协议是"规则同步"的护栏，但护栏本身需要自检——否则会"协议在但执行miss"。

## Source
- 7/24 10:42 TOOLS.md新加PPT路由规则（dashi-ppt默认可编辑⭐5）
- 7/24 17:00 review#24 未识别漏登
- 7/25 03:54 status更新标注"TOOLS.md规则同步漏登🔴"+"v1.1协议miss"
- 7/24 4:20 凌晨流水线时间窗自检
- 7/22 21:52 主人纠正"先排自身再考虑平台" 第3次应用 mtime误判
- v1.1协议设计初衷（7/9🔒规则体系建立时引入）

## Anti-pattern
- ❌ 漏登>7天才发现（应72h内自动检测）
- ❌ 补登记时凭印象写日期（应追溯源trace）
- ❌ 补登后不复检（48h后需验证一致性）
- ❌ 只补登记不更新unified_index.json（双重漏登）
- ❌ "v1.1协议存在=自动同步"的错误假设

## Related
- plan-precise-failure-attribution：v1.1漏登是"自身问题"的第一层
- atom-field-migration-check：迁移/升级后字段兼容性（同类"系统变更后检查"模式）
- MEMORY 🔒规则"TOOLS.md 🔒规则强制执行+变更日志"
