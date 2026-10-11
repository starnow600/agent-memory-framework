# Functional: v5.4前瞻性验证-影子双记录

## 触发条件
每日17:00风控扫描blow-off股票

## 操作模式
对候选池中每只出现surge的股票记录双版本评分：

| 字段 | 说明 |
|------|------|
| date, stock_code, name | 基础标识 |
| daily_change_pct | 当日涨幅 |
| surge_type | blow-off / trend / none |
| v54_score, v54_signal | v5.4实际评分和信号 |
| v53_counterfactual_score | v5.3逻辑下的反事实评分 |
| v53_counterfactual_signal | v5.3逻辑下的反事实信号 |
| bo_override_triggered | 是否触发blow-off override |
| T+1/T+3/T+5 return | 后续收益（回补） |

## 写入位置
- `实战投资/validation_log/v5.4_prospective_log.json`

## 停止条件
- **正常终止**：blow-off事件≥8只（10个交易日）
- **提前终止**：BO_OVERRIDE信号T+3出现≥3次亏损>5%

## 成功标准（测试前锁定）
| 指标 | 达标线 |
|------|--------|
| BO_OVERRIDE T+3 胜率 | ≥60% |
| BO_OVERRIDE T+3 平均收益 | ≥+3% |
| BO_OVERRIDE 最大回撤 | ≤-8% |
| 假阳性率 | ≤30% |

## 来源
- 6/27 v5.4前瞻性验证方案落地
- shadow_v53参数嵌入quant_engine_v4_5.py
