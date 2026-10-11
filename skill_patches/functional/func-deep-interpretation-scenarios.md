# func-deep-interpretation-scenarios（深度解读时机判断）

## 触发条件
topic_tracking推送简报时，判断是否需要附加深度解读（因果分析）

## 执行步骤
1. topic_tracking briefing完成 → dedup check通过 → 进入交付阶段
2. 运行深度解读判断脚本：
```bash
python "$PWD/skill_patches/scripts/deep_interpretation_check.py" --topic "话题名" --graph "$PWD/recent_memory/knowledge_graph.json"
```
3. 根据脚本返回决定：
   - `should_deep_interpret: true` → 在简报末尾附加"这件事为什么重要"段落（因果分析）
   - `should_deep_interpret: false` + 有matched_scenario → 可选深度解读（参考suggestion字段）
   - `should_deep_interpret: false` + 无matched_scenario → 保持标题+链接模式

## 场景库状态
- 已确认场景：1个（持仓/策略直接相关）
- 待观察场景：4个（首次重大话题/矛盾信号/多话题共振/用户追问）
- 提炼规则阈值：≥8个已确认场景

## 脚本说明
- 路径：`skill_patches/scripts/deep_interpretation_check.py`
- 场景库内嵌在脚本中（confirmed + pending两组）
- 关键词匹配 + 图谱交叉验证
- pending场景不强制深度解读，仅作为建议

## 场景积累规则
- 每次推送后记录：话题名→匹配场景→是否实际做了深度解读→用户反馈
- 每2周蒸馏时review场景库
- 新场景确认条件：用户主动追问 > 用户反馈有价值 > 后续证明重要
- 达到8个confirmed场景后，从场景列表提炼为判断规则

## 来源
- 2026-07-11 蒸馏报告第七章决策2（主人要求收集场景以便自主判断时机）

## 实施状态
✅ 已实施（2026-07-11），脚本已创建并测试通过
