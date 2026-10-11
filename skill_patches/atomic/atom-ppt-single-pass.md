# Atomic: python-pptx增量构建禁止分次save

## 触发条件
用python-pptx构建多页PPT

## 规则
必须单次pass按序创建所有slide。禁止分多次save→load→add（新slide追加到末尾，顺序错乱）。

## 来源
- TOOLS.md python-pptx增量构建规则
