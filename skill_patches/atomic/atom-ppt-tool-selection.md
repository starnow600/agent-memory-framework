# Patch: ppt-tool-selection

## 触发条件
PPT制作需选择create-ppt vs python-pptx vs 混用方案

## 失败根因
不同PPT制作工具各有盲区：
- create-ppt：擅长视觉设计，数据图表不可靠
- python-pptx：数据图表精确，视觉设计能力弱
- 单一工具无法同时满足"好看"和"数据准确"

## 规避规则
- 先确认PPT内容类型：纯视觉 vs 含数据图表 vs 混合
- 含数据图表 → 必须用python-pptx生成数据页
- 需要精美视觉 → 用create-ppt生成封面/概念页
- 混合内容 → 混用方案，最后合并为单个.pptx
- 选择前必须过路由，检查技能指纹索引

## 来源案例
- 冠脉CTA质量控制PPT 2026-06-20
- 最终采用混用方案成功

## 已合入
✅ 基础设定/TOOLS.md PPT五守则第2条
