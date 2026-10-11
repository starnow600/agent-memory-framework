# Planning: 量化建仓全流程

## 触发条件
扫描结果出高评分标的

## 步骤
1. **全量扫描** → stock_scanner_v5.py评分
2. **详细分析**：技术面（K线/ATR/止损）+ 基本面（搜索最新驱动）
3. **仓位计算**：约束检查（评分≥55标准仓/45-54试探仓/单只≤30%/本金≤10万/整手约束）
4. **用户确认** → PauseChain机制，决策权在用户
5. **设止损+冻结期**：Hybrid止损 + 3交易日冻结

## 依赖关系
- Step1→Step2：扫描筛选出候选
- Step3→Step4：仓位计算结果需用户确认
- Step4→Step5：建仓后立即设止损

## 关联Functional
- func-quant-stop-loss：Hybrid动态止损计算
- func-quant-position-score：持仓评分与动作映射

## 关联Atomic
- atom-quant-trading-days：持仓天数必须用K线计数
- atom-quant-lot-constraint：1手整手约束
- atom-quant-tencent-price：收盘价取row[2]
- atom-quant-regime-reversal：Reversal模式不追低MOM防御股

## 来源
- 6/18-22多次建仓经验
