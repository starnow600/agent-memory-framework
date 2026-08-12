#!/usr/bin/env python3
"""
PlugMem Phase 1: 知识节点化 + 路由索引
从decision logs / tool experience / wiki key claims 提取知识节点
"""

import json
import os
from datetime import datetime

OUTPUT_DIR = "/Coze/Drive/杨小壶/所有对话/主对话/memory-arch"
KN_DIR = os.path.join(OUTPUT_DIR, "knowledge_nodes")

# ============================================================
# 知识节点定义
# ============================================================
# 类型: proposition=事实/结论, prescription=方法/流程/操作指南
# concepts: 3-5个精准概念标签
# source_file: 原文档路径
# source_anchor: 原文档中的章节/锚点
# confidence: high/medium/low

knowledge_nodes = [
    # ========== Decision Logs 来源 ==========
    # 1. 决策即记录机制
    {
        "id": "kn_001",
        "type": "prescription",
        "proposition": "重大决策（建仓清仓止损、架构变更、规则修改、任务启动终止、≥5分钟大任务）必须在24小时内写入decision log，禁止月底批量补录。",
        "concepts": ["决策日志", "决策即记录", "记忆捕获机制", "规则固化"],
        "source_file": "recent_memory/decision/2026-08-10_decision_on_record_mechanism.md",
        "source_anchor": "决策内容 / MEMORY.md新增🔒规则",
        "confidence": "high"
    },
    {
        "id": "kn_002",
        "type": "prescription",
        "proposition": "决策即记录机制采用三管齐下闭环：MEMORY规则+每日记忆捕获日程的决策检测步骤+TOOLS.md锚点同步。",
        "concepts": ["决策日志", "闭环机制", "三重防御", "记忆捕获"],
        "source_file": "recent_memory/decision/2026-08-10_decision_on_record_mechanism.md",
        "source_anchor": "决策内容 / 三管齐下",
        "confidence": "high"
    },
    # 2. v6.0 L3右侧反转惩罚减弱
    {
        "id": "kn_003",
        "type": "proposition",
        "proposition": "反转策略中，死亡板块左侧（股价<MA20）抄底胜率仅18-25%，右侧（股价≥MA20）确认后胜率可达65-75%，右侧高β=弹性优势。",
        "concepts": ["反转策略", "右侧确认", "MA20", "板块胜率", "高β弹性"],
        "source_file": "recent_memory/decision/2026-08-10_v60_l3_right_side_fix.md",
        "source_anchor": "背景 / 业界数据",
        "confidence": "high"
    },
    {
        "id": "kn_004",
        "type": "prescription",
        "proposition": "反转模式L3板块惩罚应区分左右侧：左侧全额惩罚，右侧惩罚减弱70%，为死亡板块右侧反转开绿灯。",
        "concepts": ["反转策略", "L3修正", "右侧确认", "MA20", "板块共振"],
        "source_file": "recent_memory/decision/2026-08-10_v60_l3_right_side_fix.md",
        "source_anchor": "决策 / 右侧判定分支",
        "confidence": "high"
    },
    # 3. v6.0 L3板块共振逻辑修正
    {
        "id": "kn_005",
        "type": "proposition",
        "proposition": "反转模式下，板块齐跌≠加分信号——高β成长板块齐跌往往是趋势性杀跌加速段，行业内反转效应远强于行业间。",
        "concepts": ["反转策略", "板块共振", "行业中性化", "β分层", "残差反转"],
        "source_file": "recent_memory/decision/2026-08-10_v60_l3_sector_fix.md",
        "source_anchor": "发现链 / L3逻辑错误",
        "confidence": "high"
    },
    {
        "id": "kn_006",
        "type": "proposition",
        "proposition": "反转L3从\"齐跌加分\"改为\"板块历史胜率系数法\"后，回测胜率从47.7%提升至84.7%，T5收益从-3.64%提升至+2.68%。",
        "concepts": ["反转策略", "L3修正", "板块胜率系数法", "回测验证", "胜率提升"],
        "source_file": "recent_memory/decision/2026-08-10_v60_l3_sector_fix.md",
        "source_anchor": "回测验证 / 596只反转样本",
        "confidence": "high"
    },
    # 4. 半导体周末加扫
    {
        "id": "kn_007",
        "type": "prescription",
        "proposition": "机构调仓是信号不是命令——头部机构方向切换值得跟踪观察，但左侧抄底必须满足评分门槛和纪律约束。",
        "concepts": ["机构调仓", "左侧布局", "量化纪律", "建仓门槛", "半导体设备"],
        "source_file": "recent_memory/decision/2026-08-09_semiconductor_weekend_scan.md",
        "source_anchor": "风险与替代方案 / 核心原则",
        "confidence": "high"
    },
    # 5. Regime切换首日不动作
    {
        "id": "kn_008",
        "type": "prescription",
        "proposition": "BEAR市场MA20首次突破假突破率约50%，Regime切换必须执行3日确认制：Day1信号不动/Day2观察强度/Day3确认后操作。",
        "concepts": ["Regime切换", "3日确认制", "MA20", "假突破过滤", "风控规则"],
        "source_file": "recent_memory/decision/2026-08-07_regime_switch_no_action.md",
        "source_anchor": "决策内容 / 3日确认制",
        "confidence": "high"
    },
    # 6. MEMORY 1B危机
    {
        "id": "kn_009",
        "type": "prescription",
        "proposition": "MEMORY.md容量管理应主动而非被动——按优先级压缩（状态覆盖>标题精简>条目删除>正文压缩），遵守3项必查：🔒规则不可删/核心数据保留/压缩可追溯。",
        "concepts": ["记忆压缩", "容量管理", "优先级策略", "记忆健康度", "主动管理"],
        "source_file": "recent_memory/decision/2026-08-06_memory_1b_crisis.md",
        "source_anchor": "决策内容 / 优先级主动压缩",
        "confidence": "high"
    },
    # 7. smevals终止
    {
        "id": "kn_010",
        "type": "prescription",
        "proposition": "探索性项目应独立核算成本，当投入产出比过低时主动终止，不因沉没成本硬推——失败数据点本身有价值。",
        "concepts": ["探索成本", "资源聚焦", "止损思维", "项目终止", "沉没成本"],
        "source_file": "recent_memory/decision/2026-08-05_smevals_termination.md",
        "source_anchor": "决策依据 / 核心原则",
        "confidence": "high"
    },
    # 8. 风控报告交付方式
    {
        "id": "kn_011",
        "type": "prescription",
        "proposition": "风控报告交付应采用\"完整内容+文件链接\"模式——内容直接呈现降低阅读摩擦，文件链接作为存档附件方便回溯分享。",
        "concepts": ["风控报告", "交付方式", "用户体验", "信息触达率", "规则固化"],
        "source_file": "recent_memory/decision/2026-08-05_risk_report_delivery_change.md",
        "source_anchor": "决策内容 / 完整内容+附带文件链接",
        "confidence": "high"
    },
    # 9. 兆易创新清仓
    {
        "id": "kn_012",
        "type": "proposition",
        "proposition": "止损触发后侥幸心理延迟执行代价极大——兆易创新止损信号触发后延迟8日清仓，多亏约12000元，总亏损扩大至-29.47%。",
        "concepts": ["止损纪律", "延迟执行", "侥幸心理", "风控失败", "兆易创新"],
        "source_file": "recent_memory/decision/2026-08-03_zhaoyi_clear_position.md",
        "source_anchor": "决策依据 / 核心教训",
        "confidence": "high"
    },
    {
        "id": "kn_013",
        "type": "prescription",
        "proposition": "止损正确与卖飞风险是两回事——止损是纪律，卖飞是概率事件；触发止损必须无条件执行，不可因怕卖飞而不止损。",
        "concepts": ["止损纪律", "概率思维", "风控原则", "交易纪律"],
        "source_file": "recent_memory/decision/2026-08-03_zhaoyi_clear_position.md",
        "source_anchor": "自主决策记录 / 区分止损正确与卖飞风险",
        "confidence": "high"
    },
    # 10. PlugMem记忆架构改造
    {
        "id": "kn_014",
        "type": "prescription",
        "proposition": "记忆系统应从原始文本检索升级为知识节点化架构——参照PlugMem分三阶段：知识节点化+路由索引 → 推理压缩层 → Episodic结构化溯源。",
        "concepts": ["记忆架构", "PlugMem", "知识节点", "推理压缩", "GraphRAG局限"],
        "source_file": "recent_memory/decision/2026-08-12_plugmem_memory_architecture.md",
        "source_anchor": "决策 / 三阶段渐进改造",
        "confidence": "high"
    },

    # ========== Tool Experience 来源 ==========
    # 11. 记忆检索协议v0.5
    {
        "id": "kn_015",
        "type": "prescription",
        "proposition": "记忆检索应遵循4步优先级流程：索引分析→查询构造→执行搜索+直接读取→答案合成；索引优先于语义搜索，冲突时以索引元数据为准。",
        "concepts": ["记忆检索", "索引优先", "检索协议", "4步流程", "优先级排序"],
        "source_file": "基础设定/experience/memory_retrieval_protocol_v05.md",
        "source_anchor": "标准4步流程 / 优先级",
        "confidence": "high"
    },
    # 12. DOCX编辑分层规则
    {
        "id": "kn_016",
        "type": "prescription",
        "proposition": "DOCX编辑应按复杂度分层选择工具：新建→docx skill；无合并单元格→OfficeCLI优先；有合并单元格→OfficeCLI语义→DOM→XML三层；复杂嵌套→OOXML手动改；python-docx仅作最后兜底。",
        "concepts": ["DOCX编辑", "工具分层", "合并单元格", "OfficeCLI", "OOXML"],
        "source_file": "基础设定/experience/docx_editing_rules.md",
        "source_anchor": "不同场景选择 / 5条分层规则",
        "confidence": "high"
    },
    # 13. 规则同步协议
    {
        "id": "kn_017",
        "type": "prescription",
        "proposition": "🔒规则修改必须三层同步：TOOLS.md标记系统+SOUL.md兜底强制执行+记忆系统联动（实时同步+凌晨一致性检查+月度审计）。",
        "concepts": ["规则同步", "三重防御", "一致性检查", "🔒规则", "记忆系统联动"],
        "source_file": "基础设定/experience/rule_sync_protocol.md",
        "source_anchor": "三层防御架构",
        "confidence": "high"
    },
    # 14. 评测持久化协议
    {
        "id": "kn_018",
        "type": "prescription",
        "proposition": "所有Review/评估必须产出持久化文件并加入索引，禁止仅存在于对话上下文——不落盘的评测等于没做。",
        "concepts": ["评测持久化", "记忆可追溯", "知识复用", "索引更新"],
        "source_file": "基础设定/experience/review_persistence_protocol.md",
        "source_anchor": "核心原则 / 元规则",
        "confidence": "high"
    },
    # 15. 风险标注协议
    {
        "id": "kn_019",
        "type": "prescription",
        "proposition": "信息输出必须显式标注风险归属：[事实]=已验证数据、[决策]=需主人判断的选项、[推测]=基于有限信息的推断；禁止将不确定性伪装成确定性。",
        "concepts": ["风险标注", "信息透明度", "事实vs推测", "三级标注体系"],
        "source_file": "基础设定/experience/risk_annotation_protocol.md",
        "source_anchor": "三级标注体系 / 使用规则",
        "confidence": "high"
    },
    # 16. Crawl4AI爬虫优先级
    {
        "id": "kn_020",
        "type": "prescription",
        "proposition": "网页内容获取工具选择有明确优先级：Crawl4AI（Markdown/去噪/结构化最高优先）> scrapling（强反爬降级）> fetch_web（纯静态最轻量）> agent-browser（需交互）。",
        "concepts": ["网页抓取", "Crawl4AI", "工具优先级", "反爬绕过", "Markdown提取"],
        "source_file": "基础设定/experience/crawl4ai_web_scraping.md",
        "source_anchor": "决策树 / 优先级",
        "confidence": "high"
    },
    # 17. 规避损失计算规则
    {
        "id": "kn_021",
        "type": "proposition",
        "proposition": "规避损失是时点数（snapshot）不是流量数（flow），公式为Σ(卖出价-当日收盘价)×持股数，每日直接重新计算即可，禁止逐日累加。",
        "concepts": ["规避损失", "存量vs流量", "指标计算", "风控指标"],
        "source_file": "基础设定/experience/avoided_loss_calculation_rule.md",
        "source_anchor": "正确算法 / 错误模式对比",
        "confidence": "high"
    },
    # 18. PPT混合模式生成
    {
        "id": "kn_022",
        "type": "prescription",
        "proposition": "学术PPT混合模式应采用\"全页图做背景+真实素材叠加\"方案——直接合并pptx或操作XML都会丢失元素和图片二进制数据。",
        "concepts": ["PPT生成", "混合模式", "create-ppt", "python-pptx", "学术PPT"],
        "source_file": "基础设定/experience/hybrid_ppt_generation.md",
        "source_anchor": "正确实现方案 / 5步流程",
        "confidence": "high"
    },
    # 19. 话题追踪日报交付
    {
        "id": "kn_023",
        "type": "prescription",
        "proposition": "话题追踪日报必须以日程/子会话verify-run验证后的产物为准，主会话严禁自行补搜、重写事实或放宽标准凑数量。",
        "concepts": ["话题追踪", "交付规则", "verify-run验收", "内容质量", "严格筛选"],
        "source_file": "基础设定/experience/topic_tracking_delivery_rules.md",
        "source_anchor": "交付规则 / 主会话验收标准",
        "confidence": "high"
    },
    # 20. 路由决策技能映射
    {
        "id": "kn_024",
        "type": "proposition",
        "proposition": "复杂任务（>3步/工具选择歧义/数据采集分析生成）开始前必须运行路由脚本做技能选择决策，简单任务（纯对话/单步操作）可跳过但需记skip日志。",
        "concepts": ["技能路由", "任务复杂度", "决策脚本", "工具选择"],
        "source_file": "基础设定/experience/skill_scenario_map.json",
        "source_anchor": "L3_constraints / route_log自动写入规则",
        "confidence": "high"
    },
    # 21. 上下文压缩规则
    {
        "id": "kn_025",
        "type": "prescription",
        "proposition": "上下文压缩前必须过3步Checklist：未来3天是否需此信息做决策？降级后是否可恢复？是否属于rigid硬规则？所有压缩动作必须留审计痕迹。",
        "concepts": ["上下文压缩", "压缩Checklist", "可恢复性", "审计痕迹"],
        "source_file": "基础设定/experience/compression_v1_rules.md",
        "source_anchor": "压缩前3步Checklist",
        "confidence": "high"
    },
    # 22. IMA知识库操作
    {
        "id": "kn_026",
        "type": "prescription",
        "proposition": "IMA API返回code:200002鉴权失败为平台已知现象，非密钥失效，遇到时立即重试1-2次大概率恢复；PDF内容可用fitz直接提取，不依赖解析服务。",
        "concepts": ["IMA知识库", "鉴权重试", "PDF提取", "fitz", "微信文章读取"],
        "source_file": "基础设定/experience/ima_skill_usage_tips.md",
        "source_anchor": "鉴权特征与重试策略 / PDF读取流程",
        "confidence": "medium"
    },

    # ========== Wiki Key Claims 来源 ==========
    # 23. 分层记忆架构
    {
        "id": "kn_027",
        "type": "proposition",
        "proposition": "记忆系统采用L0即时层/L1近中期层/L2长期层三级分层持久化架构，统一索引v0.5管理54条目9种category。",
        "concepts": ["记忆架构", "分层存储", "统一索引", "L0/L1/L2"],
        "source_file": "llm-wiki/wiki/concepts/memory-system.md",
        "source_anchor": "Key Claims / KC-早期-01",
        "confidence": "high"
    },
    # 24. 头部腐化修复模型
    {
        "id": "kn_028",
        "type": "proposition",
        "proposition": "Wiki头部腐化遵循三阶段修复模型：发现腐化→数字版修正→语义版对齐，7/12首次完成完整闭环（D9 Benchmark触发）。",
        "concepts": ["头部腐化", "Wiki一致性", "三阶段修复", "D9 Benchmark"],
        "source_file": "llm-wiki/wiki/concepts/memory-system.md",
        "source_anchor": "Key Claims / KC-早期-02",
        "confidence": "high"
    },
    # 25. 任务复杂度边界假说
    {
        "id": "kn_029",
        "type": "proposition",
        "proposition": "AI任务存在复杂度阈值，超过阈值后产出质量呈非线性下降——这是review机制存在的理论基础。",
        "concepts": ["任务复杂度", "质量阈值", "Review机制", "非线性下降"],
        "source_file": "llm-wiki/wiki/concepts/memory-system.md",
        "source_anchor": "Key Claims / KC-早期-03",
        "confidence": "medium"
    },
    # 26. 销项机制闭环
    {
        "id": "kn_030",
        "type": "proposition",
        "proposition": "P0销项机制遵循24h三阶段闭环（建立→实战→Review识别缺口→规则化），等价销项3/3即达到规则化阈值。",
        "concepts": ["销项机制", "P0管理", "规则化阈值", "三阶段闭环"],
        "source_file": "llm-wiki/wiki/concepts/memory-system.md",
        "source_anchor": "Key Claims / KC-早期-04",
        "confidence": "high"
    },
    # 27. Wiki消费三层评估
    {
        "id": "kn_031",
        "type": "proposition",
        "proposition": "Wiki消费率呈三层递减：L1=85.7%/L2=71%/L3=0%，L3深度消费层存在结构性gap。",
        "concepts": ["Wiki消费", "知识消费", "三层评估", "消费率递减"],
        "source_file": "llm-wiki/wiki/concepts/memory-system.md",
        "source_anchor": "Key Claims / KC-早期-06",
        "confidence": "medium"
    },
    # 28. 索引优先检索准确率
    {
        "id": "kn_032",
        "type": "proposition",
        "proposition": "索引优先检索v0.5（索引→直接读取→语义检索三层召回）回测准确率77.8%，18个用例验证达标。",
        "concepts": ["记忆检索", "索引优先", "检索准确率", "回测验证"],
        "source_file": "llm-wiki/wiki/concepts/memory-system.md",
        "source_anchor": "Key Claims / KC-早期-12",
        "confidence": "high"
    },
    # 29. 评测体系三级跃迁
    {
        "id": "kn_033",
        "type": "proposition",
        "proposition": "评测体系经历三级跃迁：持久化（落盘文件）→ Wiki化（编译入知识图谱）→ 基准化（D9 Benchmark为标志）。",
        "concepts": ["评测体系", "知识蒸馏", "Wiki编译", "基准化"],
        "source_file": "llm-wiki/wiki/concepts/memory-system.md",
        "source_anchor": "Key Claims / KC-早期-10",
        "confidence": "high"
    },
    # 30. 统一记忆索引v0.4评估
    {
        "id": "kn_034",
        "type": "proposition",
        "proposition": "统一记忆索引v0.4健康度7.0/10（vs v0.3 5.0），关系型命中率100%、因果型完整度100%，但事实型命中率仅67%，narrative_links覆盖率仅22%是最大短板。",
        "concepts": ["统一记忆索引", "检索健康度", "narrative_links", "事实型瓶颈"],
        "source_file": "recent_memory/project/统一记忆索引_v0.4_Phase3终评_20260720.md",
        "source_anchor": "核心结论 / 关键发现",
        "confidence": "high"
    },
    # 31. PageIndex推理型RAG
    {
        "id": "kn_035",
        "type": "proposition",
        "proposition": "PageIndex用文档目录树替代向量数据库，让LLM像人类翻目录一样推理定位信息，FinanceBench准确率98.7%远超向量RAG的30-50%，但代价是慢（30-120秒/query）和token消耗大。",
        "concepts": ["PageIndex", "推理型RAG", "向量RAG局限", "文档树检索", "准确率提升"],
        "source_file": "recent_memory/project/PageIndex_学习笔记_20260624.md",
        "source_anchor": "性能数据 / 优势与代价",
        "confidence": "high"
    },
    # 32. 相似≠相关
    {
        "id": "kn_036",
        "type": "proposition",
        "proposition": "传统向量RAG的核心缺陷是\"相似≠相关\"——查询表达意图，答案表达内容，两者语义空间不同；相关性需要推理而非余弦距离匹配。",
        "concepts": ["向量RAG", "语义匹配局限", "推理检索", "查询-知识空间错位"],
        "source_file": "recent_memory/project/PageIndex_学习笔记_20260624.md",
        "source_anchor": "核心问题 / PageIndex方案核心洞察",
        "confidence": "high"
    },
    # 33. 魔鬼代言人机制
    {
        "id": "kn_037",
        "type": "prescription",
        "proposition": "记忆系统应主动引入魔鬼代言人外部挑战机制——主动构造反例验证记忆系统健壮性，而非仅被动应对发现的问题。",
        "concepts": ["魔鬼代言人", "记忆健壮性", "主动挑战", "质量保证"],
        "source_file": "llm-wiki/wiki/concepts/memory-system.md",
        "source_anchor": "Key Claims / KC-早期-11",
        "confidence": "medium"
    },
    # 34. 工具系统审计路由失灵
    {
        "id": "kn_038",
        "type": "proposition",
        "proposition": "工具选择存在惯性偏差（P0-019 Type B）——路由决策树会失灵，需定期工具系统审计校准。",
        "concepts": ["工具审计", "路由偏差", "选择惯性", "P0-019"],
        "source_file": "llm-wiki/wiki/concepts/memory-system.md",
        "source_anchor": "Key Claims / KC-早期-09",
        "confidence": "high"
    },
    # 35. A股交易硬约束
    {
        "id": "kn_039",
        "type": "prescription",
        "proposition": "A股交易必须遵守硬约束：建仓整手100股，禁止亏损补仓和T-trading。",
        "concepts": ["A股交易", "仓位纪律", "补仓禁忌", "T+0禁忌"],
        "source_file": "基础设定/TOOLS.md",
        "source_anchor": "最高频必触发规则 / A股交易硬约束",
        "confidence": "high"
    },
    # 36. 高风险操作控制
    {
        "id": "kn_040",
        "type": "prescription",
        "proposition": "高风险操作（docx编辑/邮件发送/资金操作/删文件/改核心配置）必须过3步校验，用户明确授权可例外。",
        "concepts": ["风险控制", "操作校验", "高风险操作", "用户授权"],
        "source_file": "基础设定/TOOLS.md",
        "source_anchor": "最高频必触发规则 / 高风险操作Control Policy",
        "confidence": "high"
    },
    # 37. v6.0反转U型分布
    {
        "id": "kn_041",
        "type": "proposition",
        "proposition": "反转策略得分呈U型分布：30-40分是甜蜜区（+1.07%/72%胜率），40分以上是假反弹陷阱（-3.08%/49%胜率），信号越强可能=杀跌越猛=左侧加速段。",
        "concepts": ["反转策略", "U型分布", "甜蜜区间", "假反弹陷阱", "L1反常"],
        "source_file": "recent_memory/decision/2026-08-10_v60_l3_sector_fix.md",
        "source_anchor": "发现链 / U型分布+L1反常",
        "confidence": "high"
    },
    # 38. 板块差异大于β差异
    {
        "id": "kn_042",
        "type": "proposition",
        "proposition": "反转策略中，板块差异（观察池82.7% vs 半导体7.7%）远大于β分层差异（高β-5.76% vs 低β+2.79%），板块因素是反转胜率的首要决定因素。",
        "concepts": ["反转策略", "板块效应", "β分层", "行业中性化", "胜率决定因素"],
        "source_file": "recent_memory/decision/2026-08-10_v60_l3_sector_fix.md",
        "source_anchor": "发现链 / β分层+板块断层",
        "confidence": "high"
    },
    # 39. sessions_spawn三重自检
    {
        "id": "kn_043",
        "type": "prescription",
        "proposition": "调用sessions_spawn前必须过3条自检：显式指定skill名、task包含目标/约束/输入/验收/禁止5字段、验收标准可客观判断。",
        "concepts": ["子会话", "sessions_spawn", "任务定义", "验收标准"],
        "source_file": "基础设定/TOOLS.md",
        "source_anchor": "最高频必触发规则 / sessions_spawn派发",
        "confidence": "high"
    },
    # 40. 语义退出条件
    {
        "id": "kn_044",
        "type": "prescription",
        "proposition": "所有执行型任务必须满足三类语义退出之一：✅完成/⏸️降级并标注[PARTIAL]/🛑中止回报，禁止静默降级。",
        "concepts": ["任务退出", "语义退出", "降级标注", "质量保证"],
        "source_file": "基础设定/TOOLS.md",
        "source_anchor": "最高频必触发规则 / 语义退出条件",
        "confidence": "high"
    }
]


def main():
    # 1. 写入所有知识节点文件
    for node in knowledge_nodes:
        fname = f"kn_{node['id'][3:]}_{node['concepts'][0]}.json"
        # 确保文件名安全
        safe_fname = fname.replace('/', '_').replace(' ', '_')
        fpath = os.path.join(KN_DIR, safe_fname)
        
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(node, f, ensure_ascii=False, indent=2)
    
    print(f"已生成 {len(knowledge_nodes)} 个知识节点文件")
    
    # 2. 构建概念路由索引
    concept_index = {}
    by_type = {"proposition": 0, "prescription": 0}
    all_node_ids = []
    
    for node in knowledge_nodes:
        nid = node["id"]
        all_node_ids.append(nid)
        by_type[node["type"]] += 1
        
        for concept in node["concepts"]:
            if concept not in concept_index:
                concept_index[concept] = []
            if nid not in concept_index[concept]:
                concept_index[concept].append(nid)
    
    # 3. 写入索引文件
    index_data = {
        "version": "1.0",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "stats": {
            "total_nodes": len(knowledge_nodes),
            "total_concepts": len(concept_index),
            "by_type": by_type
        },
        "concept_index": concept_index,
        "all_nodes": all_node_ids
    }
    
    index_path = os.path.join(OUTPUT_DIR, "knowledge_index.json")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"已生成概念路由索引：{len(concept_index)}个概念，{len(knowledge_nodes)}个节点")
    
    # 4. 统计Top 20概念
    sorted_concepts = sorted(concept_index.items(), key=lambda x: len(x[1]), reverse=True)
    print("\n=== Top 20 概念 ===")
    for i, (concept, nodes) in enumerate(sorted_concepts[:20]):
        print(f"{i+1}. {concept}: {len(nodes)}个节点")
    
    # 5. 源文件覆盖统计
    source_files = set()
    for node in knowledge_nodes:
        source_files.add(node["source_file"])
    print(f"\n覆盖源文件数: {len(source_files)}")
    
    decision_count = sum(1 for n in knowledge_nodes if 'decision/' in n['source_file'])
    experience_count = sum(1 for n in knowledge_nodes if 'experience/' in n['source_file'] or 'TOOLS.md' in n['source_file'])
    wiki_count = sum(1 for n in knowledge_nodes if 'wiki/' in n['source_file'])
    project_count = sum(1 for n in knowledge_nodes if 'project/' in n['source_file'])
    
    print(f"  - Decision logs: {decision_count}个节点")
    print(f"  - Tool experience: {experience_count}个节点")
    print(f"  - Wiki key claims: {wiki_count}个节点")
    print(f"  - Project reports: {project_count}个节点")


if __name__ == "__main__":
    main()
