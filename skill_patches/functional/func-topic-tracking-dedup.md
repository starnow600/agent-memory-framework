# func-topic-tracking-dedup（追踪推送去重：已解答检测）

## 触发条件
每次topic_tracking推送简报前（verify-run之后、交付之前）

## 执行步骤
1. topic_tracking briefing完成 → verify-run确认可交付
2. 运行去重检查脚本：
```bash
python "$PWD/skill_patches/scripts/topic_dedup_check.py" --topic "话题名" --graph "$PWD/recent_memory/knowledge_graph.json"
```
3. 根据脚本返回的recommendation字段决定交付方式：
   - `"deliver"` → 正常交付，不附加额外信息
   - `"annotate"` → 交付简报，但开头附加一行：`⚠️ 此话题在图谱中已有结论：[answer_summary]。以下为最新动态供参考。`
   - `"skip"` → 仅当answer_summary明确覆盖本次简报所有事件时使用，标注"此话题已有结论，无新增动态"
4. 如果recommendation是"annotate"但answer_summary为空或过时（如旧策略已废弃），降级为"deliver"

## 逻辑方向
- ❌ 不是"没连接就过滤"（那会误杀新信号）
- ✅ 是"有连接就检查是否已有答案"（避免重复推送已解决话题）

## 脚本说明
- 路径：`skill_patches/scripts/topic_dedup_check.py`
- 匹配逻辑：节点ID + aliases精确匹配 + 部分匹配
- "已有结论"判定：节点有narrative_digest（长度>20）或关联decision节点有digest
- 不修改topic_tracking技能内部文件，作为交付层包装

## 来源
- 2026-07-11 蒸馏报告第七章决策1（主人纠正逻辑方向）
- 核心问题：当前推送包含已处理/已有答案的话题，造成噪音

## 实施状态
✅ 已实施（2026-07-11），脚本已创建并测试通过
