# Patch: ima-no-download

## 触发条件
需要从ima知识库下载原文/全文

## 失败根因
ima订阅知识库API无权下载原文，返回错误码code:220030。只能用搜索API获取文献列表和摘要，无法获取全文PDF。

## 规避规则
- ima知识库仅用于搜索文献列表和摘要
- 需要全文时走其他路径（搜索→官网/PubMed/出版社链接）
- 不要尝试用ima API下载全文，会浪费调用次数

## 来源案例
- 2026-06-20 多次尝试ima下载原文失败
- 影像科知识库(kb_id: eKYSTvekavPmCnJhJCoxjf3Ki7z3SLSRD49f4Bste98=)

## 已合入
✅ MEMORY.md 知识管理区
