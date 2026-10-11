# Functional: PPT含数据图表的混用方案

## 触发条件
PPT需要数据图表（折线/柱状/饼图等）

## 操作模式
1. create-ppt生图做封面/目录/概念页
2. python-pptx做数据图表页（100%精确渲染）
3. 合并为单个.pptx

## 具体流程
1. create-ppt生成图片页 → 下载图片
2. python-pptx构建全PPT（图片页用add_picture，图表页用精确渲染）
3. 单次pass按序创建，禁止分多次save→load→add（新slide追加到末尾问题）

## 反模式
- ❌ 用AI生图做数据图表（5-10%错误率不可接受）
- ❌ 分多次save→load→add→新slide追加到末尾

## 来源
- 冠脉CTA PPT成功方案 2026-06-20
