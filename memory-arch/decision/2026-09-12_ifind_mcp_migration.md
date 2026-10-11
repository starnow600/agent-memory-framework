# 2026-09-12 iFinD数据源CLI→MCP直连迁移（风控架构变更）

## 一、决策背景

**触发时间**：2026-09-12 01:11
**决策人**：杨小壶 🧊

### 问题
- iFinD本月（9月）连续5天令牌超限 + 502错误
- 当前风控脚本的 iFinD 数据源通过 CLI 子进程方式调用（`_cli_wrapper.py`）
- CLI 方式封装层厚，错误传播链路长，重试和降级不够灵活
- 月初超限规律已确认（连续5天），影响主风控和专家版稳定性

### 契机
iFinD MCP 工具已可用（`get_stock_performance` 查日K历史，`stock_highfreq_quotes` 查实时快照），可直接替代 CLI 方式。

---

## 二、决策内容

### 迁移方案
- **主脚本**：daily_risk_check.py v6.2 → v6.3
- **专家版**：daily_risk_expert.py v2.0.3 → v2.1.0
- **新增共享模块**：ifind_mcp_adapter.py（约15KB）
- **测试脚本**：ifind_mcp_adapter_test.py（7项测试用例）

### 核心改动
1. `fetch_kline_ifind` / `fetch_klines_batch_ifind` 内部从 subprocess 调 CLI 改为调 `get_stock_performance` MCP
2. 函数签名和返回格式不变，上层评分逻辑不动
3. 三级兜底（iFinD→腾讯→akshare）和 v6.1.2 的容错机制保留
4. `USE_IFIND_MCP=True` 开关，CLI 方式保留可回退

### 测试用例
1. 健康检查
2. 单只K线获取 + 格式验证
3. 批量K线获取
4. 无效股票错误处理
5. 指数代码自动降级
6. 配额错误检测
7. submit_result 兼容性（双SDK不冲突）

---

## 三、影响范围

| 影响项 | 说明 |
|--------|------|
| 主风控脚本 | v6.2 → v6.3，数据源层替换，评分逻辑不变 |
| 专家版脚本 | v2.0.3 → v2.1.0，同上 |
| 三级数据源兜底 | 保留，iFinD 层从 CLI 换成 MCP |
| 幂等性 / 断点续扫 | 不受影响（依赖JSON文件，不依赖数据源实现） |
| 评分口径 | 不变（v6.1 建仓信号口径） |

---

## 四、回滚方案
- 设置 `USE_IFIND_MCP=False` 即可回退到 CLI 方式
- CLI 代码保留，未删除
- 回退验证：切回 CLI 后跑 fast 模式，对比输出一致性

---

## 五、验证要点
1. 冒烟测试：fast 模式持仓 + 大盘，数据对齐
2. 配额超限降级：模拟配额错误，验证降级到腾讯源正常
3. 批量性能：incremental 模式扫描20只，时间开销可接受
4. 专家版：橙色深度分析正常

---

## 六、关联记录

- 前序：v6.1.2 iFinD 容错升级（2026-09-08）
- 前序：风控全市场扫描架构优化 v6.2（2026-09-09）
- 相关脚本：daily_risk_check.py v6.3 / daily_risk_expert.py v2.1.0 / ifind_mcp_adapter.py
- 触发条件：🔒架构变更 / 🔒风控调整

---

*决策人：杨小壶 | 记录时间：2026-09-12 01:47*
