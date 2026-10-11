# Functional: 周度Skill补丁蒸馏

## 触发条件
每周六22:00蒸馏日程

## 操作模式
1. **Step 0：扫描叙事**：扫描 `recent_memory/narratives/` 本周叙事文件，提取因果链（不是"做了什么"而是"为什么有效/为什么失败"）
2. **Step 0.5：读取Wiki知识支撑**：从 `llm-wiki/wiki/` 读取相关文章，获取历史因果链作为提取模式的依据
3. **Step 0.6：读取图谱narrative辅助**：读取 `recent_memory/knowledge_graph.json`，利用关系的narrative字段理解概念间的因果演化
4. **Step 1：回顾本周轨迹**：memory_search回溯本周完成的所有任务
5. **Step 2：双向提取**：
   - 成功轨迹 → 提取Planning/Functional模式（正确路径）
   - 失败轨迹 → 提取/补充Atomic约束（规避规则）
6. **Step 3：Merge**：memory_search检测新patch与现有patch语义相似度，>0.9合并
7. **Step 4：Filter**：按5标准检查质量
   - 领域特异性：补丁必须包含领域特定的工具/场景/约束
   - 无过度封装：不是简单wrapper，必须有实质判断逻辑
   - 可复用：参数抽象而非硬编码具体值
   - 无硬编码：不含特定日期/金额等不可迁移值
   - 非函数式：描述行为规则而非return语句
8. **Step 5：更新index.json**：新增patch记录+merge_log
9. **Step 6：输出蒸馏报告**：写到 `distill_report_YYYYMMDD.md`
10. **Step 7：追踪策略改进（Loop Engineering）**：
    - 扫描包含"追踪反馈"的叙事
    - 提取追踪模板改进规则：格式偏好、推送时机、话题相关性阈值
    - 如有明确改进方向，记录建议到报告（不直接修改技能配置，等主人决策）
11. **Step 8：Skill决策树更新（Loop Engineering）**：
    - 评估新模式是否需要更新Skill决策树
    - 如需更新，修改对应patch的why字段或文件内容
    - 记录更新理由（来自哪条叙事/Wiki文章）
12. **Step 9：监控链完整性检查**：
    - 验证本周期内所有监控类日程是否正常产出（daily_risk_check、forward_test、持仓预警等）
    - 扫描预期产出目录，检查是否有缺失日期
    - 如发现断档，记录到蒸馏报告作为Atomic来源
    - 注意：检查正确的产出路径，避免误判（如`实战投资/每日风控/`而非`akshare-data/`）

## 反模式
- ❌ 只记失败不记成功
- ❌ 只追加不合并
- ❌ 双源真相（patch同时写入其他文件）
- ❌ 跳过Step 0/0.5/0.6直接做双向提取（丢失叙事因果链的洞察）
- ❌ 蒸馏报告只列patch不说明"叙事帮助发现了什么"

## 三重知识支撑（Step 0/0.5/0.6）的核心价值
- **叙事（Step 0）**：提供"发生了什么→为什么→学到什么"的完整因果链
- **Wiki（Step 0.5）**：提供"是什么/为什么"的概念框架和历史演化
- **图谱（Step 0.6）**：提供"概念间关系"的浓缩叙事，快速定位相关概念
- 三者协同：叙事找根因，Wiki找框架，图谱找关联

## 来源
- skill_patches体系建设 2026-06-22
- SkillX论文(arxiv:2604.04804) Merge+Filter机制
- 7/4 蒸馏首次启用v0.4叙事增强
- 7/11 蒸馏正式纳入Step 0/0.5/0.6为强制步骤
- 7/26 蒸馏v0.6：func-narrative-in-distill增加Step 0.7（叙事消费前置验证），来源为func-fact-verification-closure（7/26事实验证🔒首例闭环）
- 8/2 蒸馏v0.7：增加Step 9（监控链完整性检查），来源为plan-monitoring-chain-cross-validation（8/2 T7发现监控链断档误报）