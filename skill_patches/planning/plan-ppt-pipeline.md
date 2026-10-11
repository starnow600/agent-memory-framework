# Planning: PPT制作全流程

## 触发条件
收到PPT制作需求

## 步骤
1. **确认需求层级**：纯排版 / 风格迁移 / 内容结构化 / 整体重设计 — 先确认再动手
2. **确认输出格式**：HTML在线展示 / PPTX可编辑 / 混用方案（未确认前不可动手）
3. **选工具**（路由决策树PPT分支）：
   - 有数据图表 → python-pptx（混用方案）
   - 纯视觉概念页 → create-ppt
   - 已有文章 → article-to-ppt
4. **制作**：按选定工具链执行
5. **全量样式检查**：改字体/配色等样式时，检查所有图表页而非只改提到的页
6. **迭代检查点**：≥2轮修改主动停，前3页确认再推进

## 依赖关系
- Step1→Step2：需求层级决定格式
- Step2→Step3：格式决定工具选择
- Step3→Step4：工具决定制作流程
- Step4→Step5：制作完成后必须全量检查

## 关联Functional
- func-ppt-data-charts：含数据图表时的混用方案

## 关联Atomic
- atom-ppt-format-first：格式必须先确认
- atom-ppt-chart-no-ai：数据图表禁止AI生图
- atom-ppt-full-style-check：样式修改全量检查
- atom-ppt-tool-selection：工具选型规则

## 来源
- 冠脉CTA PPT成功经验（混用方案）2026-06-20
- 多次PPT返工失败教训
