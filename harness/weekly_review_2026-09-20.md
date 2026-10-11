# 技能系统周度快览 (T7) - Week 11

> 周期：2026-09-13 ~ 2026-09-20（过去7天）
> 产出时间：2026-09-20 16:41
> 数据源：./harness/route_log.jsonl（430条记录，数据量充足，全量分析）
> 关联：技能系统测试方案 v1.0 §八（T7）
> 上期对比：weekly_review_2026-09-13.md（Week 10，7条记录，🔴 数据量降级）

---

## 1. 数据量统计

**📈 爆发式增长**：本周 430 条 route_log 记录（上周仅 7 条），增长 +6043%。核心驱动：iFinD MCP 路由埋点全面接入（v6.3/v6.4 架构升级后风控链路补齐 hook）。

| 指标 | Week 11 (9/13-9/20) | Week 10 (9/6-9/13) | 变化 | 阈值 | 状态 |
|------|---------------------|---------------------|------|------|------|
| 总记录数 | **430 条** | 7 条 | **+6043%** | ≥10 条/周 | 🟢 大幅达标 |
| 日均记录 | 61.4 条/天 | 1.0 条/天 | +6040% | ≥1.4 条/天 | 🟢 充足 |
| 时间分布 | 5个交易日+2个记忆日 | 7天全覆盖 | 正常 | 7天覆盖 | 🟡 周末仅memory任务（预期内） |
| 涵盖场景 | 10 个 | 1 个 | +9个 | — | 🟢 丰富 |

**记录构成**：
- kline_fetch_ifind_mcp：373条（86.7%，风控+扫描的K线获取主力）
- daily_memory_capture：7条（每日凌晨1次，7天全勤 🟢）
- ifind_data_source_init：6条（风控启动初始化）
- risk_check_run_mode：6条（风控主流程full模式）
- ifind_mcp_health_check：6条（MCP健康检查）
- ifind_health_check：6条（iFinD健康检查）
- market_scan_mode：6条（全市场扫描incremental模式）
- kline_batch_fetch_ifind_mcp：10条（批量K线获取）
- expert_ifind_data_source_init：5条（专家影子测试初始化）
- expert_analysis_entry：5条（专家分析入口6-module-expert）

**数据质量备注**：
- route_log.jsonl 存在 2 处 JSON 粘连（两条记录合并于一行），脚本已容错处理，不影响统计结果。
- 9/19、9/20 仅 1 条/天（周六日无风控/扫描任务），属预期模式。

---

## 2. 异常信号扫描

| 异常类型 | 检测结果 | 状态 | 说明 |
|---------|---------|------|------|
| 未命中技能（chosen=null/空） | 0 条 | 🟢 | 全部记录有明确 chosen 值 |
| Fallback 触发率 | 0%（0/430） | 🟢 | 远低于 15% 异常阈值；3只个股返回空由腾讯/akshare兜底（未记为fallback_used） |
| 用户纠正/重做信号 | 0 条 | 🟢 | note中无用户主动纠正/重做信号（memory记录中的"修复"为系统自身迭代，非用户反馈） |
| 组合管道执行失败 | 15 条（3.5%） | 🟡 | 10条为指数代码skip（设计预期），5条为iFinD MCP实际失败（1.2%） |
| JSON 格式异常 | 2 处粘连 | 🟡 | 不影响统计，脚本已容错 |

### 失败明细（15条，分两类）

**A. skip(index_code) - 设计预期（10条，每天2条）**
- 场景：kline_fetch_ifind_mcp
- 原因：`sh000300` 沪深300指数代码 MCP 直连不支持，标记为 `skip(index_code)`，success=false
- 评估：🔵 **设计预期**。指数K线走独立路径（index_data工具），不在kline_fetch管道内。但 success=false 会拉低整体成功率统计。
- 建议：指数代码跳过应标记为 `success=true` 但加 `skipped=true` 标签，避免污染成功率指标。

**B. iFinD MCP 实际失败（5条，1.2%）**

| 时间 | 场景 | 原因 | 处理 |
|------|------|------|------|
| 09-14 17:10 | kline_fetch | sh600030 返回空 | 走腾讯/akshare兜底 |
| 09-14 17:20 | kline_fetch | sh600398 返回空 | 走腾讯/akshare兜底 |
| 09-14 18:32 | health_check | MCP连接失败（127.0.0.1:9999） | 健康检查告警 |
| 09-14 18:32 | ifind_health | available=False | 健康检查告警 |
| 09-16 17:15 | kline_fetch | sz000600 返回空 | 走腾讯/akshare兜底 |

- 9/14 单日集中出现 4 次失败（含一次 MCP 服务断连），9/15 起恢复稳定
- K线返回空共 3 次（3/373=0.8%），均由三级兜底体系消化，未影响最终风控结果

---

## 3. 风险与盲区

### 🟢 已解决：风控全链路 route_log 脱钩
- **状态**：✅ 已解决（本周正式补齐）
- **证据**：daily_risk_check（6条）、全市场扫描（6条）、风控专家影子测试（5条）全部有 route_log 记录
- **历史**：连续 5 周（W6-W10）脱钩，本周全面恢复

### 🟢 已解决：iFinD MCP 路由监控盲区
- **状态**：✅ 已解决
- **证据**：iFinD MCP 相关记录 396 条（占92%），覆盖kline_fetch、health_check、init等全场景
- 本周新增 MCP 健康检查场景 2 个（ifind_mcp_health_check + ifind_health_check），各6次

### 🟡 中优先级：skip(index_code) 拉低成功率
- 指数代码跳过被记为 success=false，导致整体成功率虚低（96.5% vs 实际99.2%）
- 影响：T7 监控误判风险
- 建议：引入 `skipped` 字段区分"主动跳过"和"真失败"

### 🟡 中优先级：9/14 MCP 服务短暂断连（18:32）
- 17:08 正常 → 18:32 断连 → 之后恢复（后续日均健康检查通过）
- 原因不明：可能是 MCP 服务重启或网络波动
- 未触发告警：健康检查失败后未主动通知（仅记入route_log）
- 建议：健康检查连续失败 ≥2 次时触发主动告警

### 🔵 观察：延迟波动
- iFinD MCP 平均延迟 6506ms，最大 20778ms（~21秒）
- 批量获取（50只约2分钟）在可接受范围内，但峰值延迟需关注

---

## 4. 测试用例补充建议

本周新增 **3 类测试场景**，建议追加到测试方案对应维度：

### T1 单技能召唤 - 新增（金融数据类）
1. **iFinD MCP 直连初始化** → 正确选择 `ifind_data_source_init` → chosen=iFinD MCP
2. **MCP 健康检查** → 正确选择 `ifind_mcp_health_check` → chosen=iFinD MCP
3. **iFinD 可用性检查** → 正确选择 `ifind_health_check` → chosen=iFinD MCP
4. **专家影子测试初始化** → 正确选择 `expert_ifind_data_source_init` → chosen=iFinD MCP

### T6 Fallback链 - 新增
1. **MCP 服务断连降级**：MCP connect failed → 健康检查标记不可用 → 风控流程切换到备选数据源（腾讯/akshare）
2. **个股K线返回空降级**：iFinD MCP 返回空 → 走腾讯/akshare三级兜底
3. **指数代码跳过处理**：sh000300 等指数代码 → skip(index_code) → 走 index_data 独立管道

### T3 组合管道 - 新增
1. **风控全流程管道**：ifind_data_source_init → health_check×2 → risk_check_run_mode=full → kline_fetch×N → kline_batch_fetch×M → 生成分析报告
2. **专家影子测试管道**：expert_ifind_data_source_init → expert_analysis_entry=6-module-expert → kline_fetch×2 → 专家分析输出

---

## 5. 自主决策记录

| # | 决策内容 | 依据 | 替代方案 |
|---|---------|------|---------|
| 1 | 周期界定为 9/13~9/20（以最新记录时间倒推7天） | 上期保持一致，最新记录为9/20 01:53 | 以自然周（周一~周日）划分 |
| 2 | skip(index_code) 10条标记为"设计预期"而非异常 | 指数代码走独立index_data管道是已知设计，非bug | 计入失败率统计并要求修复 |
| 3 | 3只个股返回空不记为fallback_used（route_log中fallback_used=false） | 数据显示fallback_used字段为false，兜底由下游风控代码执行而非路由层降级 | 按fallback统计 |
| 4 | 新增测试用例按T1/T3/T6分类追加 | 场景覆盖单技能召唤、组合管道、降级链三个维度 | 全部归入T7生产回顾 |
| 5 | 9/19-9/20 数据量低标记为"周末预期内" | 周六日不开市，风控/扫描任务不运行 | 标记为数据异常 |

---

## 6. 下周重点

1. **优化 success 字段语义**：skip(index_code) 应记为成功+跳过标签，避免拉低成功率
2. **健康检查告警机制**：连续失败≥2次触发主动通知（当前仅记日志）
3. **延迟监控**：关注 MCP 调用延迟趋势，识别性能退化
4. **测试用例落地**：将本周新增的 iFinD MCP 相关用例正式写入 skill_system_test_plan.md
