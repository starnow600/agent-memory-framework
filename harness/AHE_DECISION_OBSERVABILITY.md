# AHE决策可观测性规范（2026-05-28落地）

来源：复旦AHE论文（arxiv:2604.25850）的Decision Observability启发
核心思路：每次变更必须写"变更契约"，下一轮运行验证预测

## 变更记录模板

每次Evolver运行后，在evolution_narrative.md中使用以下格式记录变更：

```
### [YYYY-MM-DD HH:MM] {STRATEGY} - {status}
- Gene: {gene_id} | Score: {score} | Scope: {scope}
- Signals: [{signals}]
- **变更契约**:
  - 修改内容: {具体改了什么文件/规则}
  - 失败证据: {基于什么失败证据做此修改}
  - 根因推断: {为什么认为这个修改能解决问题}
  - 预测修复: {预计修好哪些场景/问题}
  - 预测风险: {可能弄坏哪些场景}
- **验证结果**: (下一轮运行后填写)
  - 实际修复: {哪些预测修复被验证}
  - 实际回归: {哪些预测风险发生了，或出现了未预见的问题}
  - 契约判定: ✅预测准确 / ⚠️部分准确 / ❌预测失败
```

## 执行方式

由于Evolver源码是混淆的，无法直接修改其内部逻辑，采用"后处理"方式：
1. Evolver运行完成后，读取其输出的evolution_narrative.md
2. 对照实际运行结果，补充"验证结果"部分
3. 如果上一轮有未验证的变更契约，先验证再记录新变更

## 文件位置
- Evolver叙事：~/evolver/workspace/memory/evolution/evolution_narrative.md
- 本规范：./harness/AHE_DECISION_OBSERVABILITY.md
