"""
PlugMem Phase 3 - 增量知识节点抽取器 (Incremental Knowledge Node Extractor)

功能：
  从一篇新的 decision log / tool experience / wiki 页面的 markdown 文本中，
  用规则方法（关键词命中+段落分析）提取 1-5 个知识节点，写入 knowledge_nodes/
  并更新 knowledge_index.json 的 concept_index、all_nodes、stats。

设计原则：
  - 纯规则抽取，不依赖 LLM
  - 幂等：同一源文件不会被重复抽取
  - 向后兼容：只新增文件、更新索引，不修改已有节点
"""

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).parent
INDEX_PATH = BASE_DIR / "knowledge_index.json"
NODES_DIR = BASE_DIR / "knowledge_nodes"


# ---------- 关键词词库 ----------

# 决策/结论类段落关键词（命中即视为高价值段落）
DECISION_KEYWORDS = [
    "决策", "结论", "决定", "决议", "敲定", "确定", "拍板",
    "结论是", "最终决定", "因此", "所以", "综上", "综上所述",
    "应当", "应该", "必须", "需", "要", "不得", "禁止", "严禁",
    "规则", "原则", "标准", "规范", "流程", "步骤", "方法",
    "验收", "通过", "达成", "共识",
]

# prescription 类关键词（规范/规则/方法类命题）
PRESCRIPTION_KEYWORDS = [
    "应当", "应该", "必须", "需", "要", "不得", "禁止", "严禁",
    "规则", "原则", "标准", "规范", "流程", "步骤", "方法",
    "先", "再", "然后", "首先", "其次", "最后",
    "确保", "保证", "遵循", "遵守", "按照", "依照",
    "验收标准", "交付要求", "执行", "实施",
]

# proposition 类关键词（事实/论断/观察类命题）
PROPOSITION_KEYWORDS = [
    "发现", "观察到", "表明", "显示", "证明", "验证",
    "结论是", "因此", "所以", "原因是", "本质是",
    "核心是", "关键是", "重点是", "主要是",
    "提升了", "下降了", "增加了", "减少了",
    "优于", "低于", "高于",
]

# 固定概念词库（用于给节点打标签，从现有索引中提炼的核心概念簇）
FIXED_CONCEPT_VOCAB = [
    # 记忆系统
    "记忆压缩", "容量管理", "记忆架构", "知识节点", "记忆检索",
    "索引优先", "检索协议", "分层存储", "统一索引", "记忆健康度",
    "上下文压缩", "可恢复性", "记忆捕获", "规则固化", "闭环机制",
    # 决策与风控
    "决策日志", "决策即记录", "风控规则", "止损纪律", "风险控制",
    "交易纪律", "风控原则", "概率思维", "仓位纪律", "风险标注",
    "信息透明度", "事实vs推测", "三级标注体系",
    # 交易策略
    "反转策略", "右侧确认", "MA20", "板块胜率", "高β弹性",
    "L3修正", "板块共振", "行业中性化", "β分层", "残差反转",
    "板块胜率系数法", "回测验证", "胜率提升", "机构调仓",
    "左侧布局", "量化纪律", "建仓门槛", "半导体设备",
    "Regime切换", "3日确认制", "假突破过滤",
    "U型分布", "甜蜜区间", "假反弹陷阱", "L1反常",
    "板块效应", "胜率决定因素", "A股交易", "补仓禁忌", "T+0禁忌",
    # 工具与技能
    "DOCX编辑", "工具分层", "合并单元格", "OfficeCLI", "OOXML",
    "PPT生成", "混合模式", "create-ppt", "python-pptx", "学术PPT",
    "网页抓取", "Crawl4AI", "工具优先级", "反爬绕过", "Markdown提取",
    "IMA知识库", "鉴权重试", "PDF提取", "fitz", "微信文章读取",
    "话题追踪", "交付规则", "verify-run验收", "内容质量", "严格筛选",
    "技能路由", "任务复杂度", "决策脚本", "工具选择",
    # 质量与评测
    "评测持久化", "记忆可追溯", "知识复用", "索引更新",
    "检索准确率", "评测体系", "知识蒸馏", "Wiki编译", "基准化",
    "统一记忆索引", "检索健康度", "narrative_links", "事实型瓶颈",
    "PageIndex", "推理型RAG", "向量RAG局限", "文档树检索", "准确率提升",
    "向量RAG", "语义匹配局限", "推理检索", "查询-知识空间错位",
    # 管理与协作
    "销项机制", "P0管理", "规则化阈值", "三阶段闭环",
    "Wiki消费", "知识消费", "三层评估", "消费率递减",
    "魔鬼代言人", "记忆健壮性", "主动挑战", "质量保证",
    "工具审计", "路由偏差", "选择惯性",
    "子会话", "sessions_spawn", "任务定义", "验收标准",
    "任务退出", "语义退出", "降级标注",
    "规则同步", "一致性检查", "记忆系统联动",
    "三重防御", "探索成本", "资源聚焦", "止损思维",
    "项目终止", "沉没成本", "风控报告", "交付方式",
    "用户体验", "信息触达率", "PlugMem", "GraphRAG局限",
    "头部腐化", "Wiki一致性", "三阶段修复", "D9 Benchmark",
    "质量阈值", "Review机制", "非线性下降",
    "规避损失", "存量vs流量", "指标计算", "风控指标",
    "压缩Checklist", "审计痕迹", "优先级策略", "主动管理",
    "高风险操作", "操作校验", "用户授权",
]


# ---------- 工具函数 ----------

def load_knowledge_index() -> Dict:
    """加载知识节点索引。"""
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_knowledge_index(index: Dict) -> None:
    """保存知识节点索引。"""
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def get_existing_source_files() -> set:
    """获取所有已抽取过的源文件路径集合，用于幂等判断。"""
    existing = set()
    for fname in os.listdir(NODES_DIR):
        if fname.endswith(".json") and fname.startswith("kn_"):
            fpath = NODES_DIR / fname
            with open(fpath, "r", encoding="utf-8") as f:
                node = json.load(f)
                sf = node.get("source_file", "")
                if sf:
                    existing.add(sf)
    return existing


def get_next_node_id(index: Dict) -> str:
    """
    计算下一个节点ID（从现有最大ID递增）。
    
    Returns:
        如 "kn_045"
    """
    all_nodes = index.get("all_nodes", [])
    if not all_nodes:
        return "kn_001"
    
    max_num = 0
    for nid in all_nodes:
        m = re.match(r"kn_(\d+)", nid)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    
    return f"kn_{max_num + 1:03d}"


# ---------- 文档结构解析 ----------

def parse_markdown_sections(text: str) -> List[Dict]:
    """
    解析 markdown 文档，按标题切分为段落块。
    
    Returns:
        列表，每项为 dict: {
            "heading": str,     # 所属标题（完整路径，如 "决策 / 核心内容"）
            "level": int,       # 标题层级（1-6）
            "content": str,     # 该段落正文
            "lines": List[str], # 原始行列表
        }
    """
    lines = text.split("\n")
    sections = []
    heading_stack = []  # [(level, text), ...]
    current_lines = []
    current_heading = "前言"
    current_level = 0
    
    def flush_section():
        if current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                sections.append({
                    "heading": current_heading,
                    "level": current_level,
                    "content": content,
                    "lines": current_lines.copy(),
                })
    
    for line in lines:
        # 匹配标题行
        m = re.match(r'^(#{1,6})\s+(.+?)\s*#*\s*$', line)
        if m:
            # 先 flush 当前段落
            flush_section()
            
            level = len(m.group(1))
            title = m.group(2).strip()
            
            # 更新标题栈
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            
            current_heading = " / ".join(h[1] for h in heading_stack)
            current_level = level
            current_lines = []
        else:
            current_lines.append(line)
    
    # flush 最后一段
    flush_section()
    
    return sections


def extract_bullet_items(content: str) -> List[str]:
    """
    从段落中提取列表项（-、*、数字列表）。
    每个列表项作为一个候选命题。
    """
    items = []
    for line in content.split("\n"):
        line = line.strip()
        # 匹配无序列表
        if re.match(r'^[-*+]\s+', line):
            item = re.sub(r'^[-*+]\s+', '', line).strip()
            if item and len(item) >= 10:
                items.append(item)
        # 匹配有序列表
        elif re.match(r'^\d+[.、]\s+', line):
            item = re.sub(r'^\d+[.、]\s+', '', line).strip()
            if item and len(item) >= 10:
                items.append(item)
    
    return items


def extract_bold_text(content: str) -> List[str]:
    """
    从段落中提取加粗文本（**xxx** 或 __xxx__），作为关键命题候选。
    """
    # 匹配 **加粗**
    bolds = re.findall(r'\*\*(.+?)\*\*', content)
    # 匹配 __加粗__
    bolds += re.findall(r'__(.+?)__', content)
    return [b.strip() for b in bolds if len(b.strip()) >= 8]


# ---------- 命题提取 ----------

def score_paragraph_value(section: Dict) -> float:
    """
    评估一个段落的知识价值分数（0-1）。
    
    评分维度：
      1. 标题关键词（决策、结论、规则等标题权重高）
      2. 正文中决策关键词密度
      3. 列表项数量（结构化内容价值高）
      4. 加粗文本数量（强调内容价值高）
    """
    score = 0.0
    heading = section["heading"]
    content = section["content"]
    
    # 1. 标题关键词
    high_value_headings = [
        "决策", "结论", "规则", "原则", "方法", "流程",
        "验收", "标准", "规范", "方案", "建议",
        "核心内容", "关键发现", "重要结论", "背景与决策",
    ]
    for kw in high_value_headings:
        if kw in heading:
            score += 0.3
            break
    
    # 2. 正文中决策关键词密度
    kw_hits = sum(1 for kw in DECISION_KEYWORDS if kw in content)
    density_score = min(kw_hits * 0.05, 0.3)
    score += density_score
    
    # 3. 列表项数量
    bullets = extract_bullet_items(content)
    if len(bullets) >= 3:
        score += 0.2
    elif len(bullets) >= 1:
        score += 0.1
    
    # 4. 加粗文本
    bolds = extract_bold_text(content)
    if len(bolds) >= 2:
        score += 0.15
    elif len(bolds) >= 1:
        score += 0.08
    
    # 5. 长度惩罚（太短的段落信息量不足）
    if len(content) < 50:
        score *= 0.5
    
    return min(score, 1.0)


def extract_propositions_from_section(section: Dict) -> List[str]:
    """
    从一个高价值段落中提取候选命题句子。
    
    策略：
      1. 优先提取列表项（结构化、明确）
      2. 其次提取加粗文本 + 其所在句子
      3. 最后从正文中提取有关键词的句子
    """
    candidates = []
    content = section["content"]
    
    # 1. 列表项
    bullets = extract_bullet_items(content)
    for b in bullets:
        # 过滤太短的
        if 10 <= len(b) <= 200:
            candidates.append(b)
    
    # 2. 加粗文本 + 上下文
    bolds = extract_bold_text(content)
    # 找到每个加粗文本所在的完整句子
    sentences = re.split(r'(?<=[。！？])\s*', content)
    for bold in bolds:
        for sent in sentences:
            if bold in sent and 15 <= len(sent) <= 200:
                if sent not in candidates:
                    candidates.append(sent.strip())
                break
    
    # 3. 有关键词的句子
    if len(candidates) < 3:
        for sent in sentences:
            sent = sent.strip()
            if 15 <= len(sent) <= 200:
                kw_count = sum(1 for kw in DECISION_KEYWORDS if kw in sent)
                if kw_count >= 2 and sent not in candidates:
                    candidates.append(sent)
    
    return candidates[:5]  # 每个段落最多提取5个候选


def classify_proposition_type(proposition: str) -> str:
    """
    判断命题类型：prescription（规范/规则/方法）或 proposition（事实/论断）。
    
    基于关键词计数判断。
    """
    presc_count = sum(1 for kw in PRESCRIPTION_KEYWORDS if kw in proposition)
    prop_count = sum(1 for kw in PROPOSITION_KEYWORDS if kw in proposition)
    
    if presc_count >= prop_count and presc_count > 0:
        return "prescription"
    elif prop_count > presc_count:
        return "proposition"
    else:
        # 平局时默认 proposition（更保守）
        return "proposition"


def determine_confidence(proposition: str, section: Dict) -> str:
    """
    确定命题的置信度等级。
    
    high: 出现在明确的决策/规则段落，有明确的断言性表述
    medium: 出现在分析/讨论段落，但有明确结论
    low: 出现在背景/介绍段落，或表述不够确定
    """
    heading = section["heading"]
    content = proposition
    
    # 高置信度条件
    high_heading_signals = ["决策", "规则", "原则", "标准", "验收", "规范", "结论", "决定"]
    high_content_signals = ["必须", "应当", "严禁", "禁止", "确保", "结论是", "证明", "验证通过"]
    
    heading_score = sum(1 for s in high_heading_signals if s in heading)
    content_score = sum(1 for s in high_content_signals if s in content)
    
    if heading_score >= 1 and content_score >= 1:
        return "high"
    if heading_score >= 1 or content_score >= 2:
        return "high"
    
    # 中等置信度
    medium_signals = ["应该", "建议", "可以", "推荐", "发现", "观察到", "表明", "显示"]
    if any(s in content for s in medium_signals):
        return "medium"
    
    # 低置信度：可能、也许、似乎等不确定表述
    low_signals = ["可能", "也许", "似乎", "大概", "或许", "有待", "考虑"]
    if any(s in content for s in low_signals):
        return "low"
    
    return "medium"  # 默认中等


def generate_concepts(proposition: str, heading: str, max_concepts: int = 5) -> List[str]:
    """
    为命题生成概念标签（3-5个）。
    
    策略：
      1. 优先从固定词库中匹配命中的概念（精确匹配，高质量标签来源）
      2. 从标题中提取有语义的名词短语（基于边界词切分）
      3. 从命题中提取核心名词短语
      4. 组合去重，取前 max_concepts 个
    """
    concepts = []
    combined_text = proposition + " " + heading
    
    # 1. 固定词库精确匹配（按长度降序，优先匹配更长的精确概念）
    matched_vocab = []
    for concept in FIXED_CONCEPT_VOCAB:
        if concept in combined_text:
            matched_vocab.append(concept)
    # 按长度降序，长的优先（更精确）
    matched_vocab.sort(key=len, reverse=True)
    for c in matched_vocab:
        if c not in concepts:
            concepts.append(c)
    
    # 2. 从标题中提取主题概念（基于"的/与/和/及"等连接词切分）
    heading_kw = extract_noun_phrases_from_heading(heading)
    for kw in heading_kw:
        if kw not in concepts and len(kw) >= 2:
            concepts.append(kw)
    
    # 3. 从命题中提取核心名词短语
    prop_kw = extract_core_phrases(proposition)
    for kw in prop_kw:
        if kw not in concepts and len(kw) >= 2:
            concepts.append(kw)
    
    # 确保 3-5 个
    if len(concepts) < 3:
        # 补足：添加一些通用概念
        generic = ["知识节点", "规则固化", "记忆捕获", "记忆系统", "决策机制"]
        for g in generic:
            if len(concepts) >= 3:
                break
            if g not in concepts:
                concepts.append(g)
    
    # 质量过滤
    stopwords = set("的了是在有和与及也都就被把从对给让使要中上下前后里外这那")
    filtered = []
    for c in concepts:
        # 去掉末尾的"的"字
        if c.endswith('的') and len(c) > 2:
            c = c[:-1]
        # 去掉开头的虚词
        if len(c) >= 2 and c[0] in stopwords:
            c = c[1:]
        # 2字且都是虚词组合的去掉
        if len(c) == 2 and c[0] in stopwords and c[1] in stopwords:
            continue
        # 太短的去掉
        if len(c) < 2:
            continue
        # 太泛的单动作词去掉（纯动词类不适合作为概念标签）
        vague_verbs = {'实施', '验收', '进行', '需要', '使用', '通过', '执行',
                       '完成', '开始', '结束', '建立', '实现', '提升', '提高',
                       '降低', '减少', '增加', '确保', '保证'}
        if c in vague_verbs:
            continue
        filtered.append(c)
    
    # 去重（处理上面裁剪后可能产生的重复）
    seen = set()
    unique = []
    for c in filtered:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    
    return unique[:max_concepts]


def extract_noun_phrases_from_heading(heading: str) -> List[str]:
    """
    从标题中提取名词短语。
    
    策略：
      - 按 / 分隔符拆分多级标题，取每一级核心词
      - 去掉"关于/对于/基于"等前缀
      - 去掉"的决策/的研究/的分析"等后缀
    """
    phrases = []
    
    # 按标题层级分隔符拆分
    parts = re.split(r'\s*/\s*', heading)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # 去掉前缀
        part = re.sub(r'^(关于|对于|基于|针对|一种|一个|一项|的)\s*', '', part)
        
        # 去掉后缀
        part = re.sub(r'\s*(决策|决定|结论|方案|建议|报告|分析|研究|说明|记录|日志|机制|原则|规则|方法|流程|标准)$', '', part)
        
        part = part.strip()
        if len(part) >= 2:
            phrases.append(part)
    
    return phrases


def extract_core_phrases(text: str, top_n: int = 3) -> List[str]:
    """
    从文本中提取核心短语。
    
    策略：基于中文短语边界识别，提取长度 2-8 字、
    不含虚词开头/结尾的有意义短语。
    """
    # 先提取所有连续中文字符段
    cn_segments = re.findall(r'[\u4e00-\u9fff]+', text)
    
    # 常见前缀虚词（短语不以这些开头）
    prefix_stop = {'的', '了', '是', '在', '有', '和', '与', '及', '也', '都', '就',
                   '被', '把', '从', '对', '给', '让', '使', '要', '中', '上', '下',
                   '这', '那', '个', '种', '项', '些', '每', '各', '某'}
    # 常见后缀虚词（短语不以这些结尾）
    suffix_stop = {'的', '了', '是', '在', '和', '与', '及', '也', '都', '就',
                   '被', '把', '从', '对', '给', '让', '使', '要', '中', '上',
                   '下', '这', '那', '个', '种', '项', '些', '等', '及'}
    
    candidates = {}
    
    for seg in cn_segments:
        if len(seg) < 2:
            continue
        # 提取 2~8 字的候选短语
        for n in range(2, min(9, len(seg) + 1)):
            for i in range(len(seg) - n + 1):
                phrase = seg[i:i+n]
                # 过滤：首尾不能是虚词
                if phrase[0] in prefix_stop or phrase[-1] in suffix_stop:
                    continue
                # 过滤：全是虚词
                if all(c in prefix_stop or c in suffix_stop for c in phrase):
                    continue
                # 过滤常见的非名词短语
                if phrase in {'可以', '已经', '不是', '没有', '通过', '进行', '需要',
                               '应该', '必须', '能够', '可能', '应当', '不得',
                               '确保', '保证', '遵循', '遵守', '按照', '依照'}:
                    continue
                candidates[phrase] = candidates.get(phrase, 0) + 1
    
    # 排序：优先长的、频率高的
    sorted_kw = sorted(
        candidates.items(),
        key=lambda x: (x[1], len(x[0])),
        reverse=True
    )
    
    # 去冗余：如果已有更长的短语包含了短的，去掉短的
    result = []
    for kw, _ in sorted_kw:
        # 检查是否已被更长的短语包含
        is_subsumed = False
        for r in result:
            if kw in r and len(r) > len(kw):
                is_subsumed = True
                break
        if not is_subsumed:
            result.append(kw)
            if len(result) >= top_n:
                break
    
    return result


# ---------- 核心抽取函数 ----------

def extract_knowledge_nodes(text: str, source_file: str) -> List[Dict]:
    """
    从一篇 markdown 文档中提取知识节点。
    
    Args:
        text: markdown 文档全文
        source_file: 源文件路径（用于溯源和幂等判断）
    
    Returns:
        知识节点列表（尚未分配ID），每项为 dict:
        {
            "proposition": str,
            "concepts": List[str],
            "type": "proposition" | "prescription",
            "source_file": str,
            "source_anchor": str,
            "confidence": "high" | "medium" | "low",
        }
    """
    # 1. 解析文档结构
    sections = parse_markdown_sections(text)
    
    if not sections:
        return []
    
    # 2. 评估每个段落的价值，筛选高价值段落
    scored_sections = []
    for sec in sections:
        value = score_paragraph_value(sec)
        if value >= 0.2:  # 价值阈值
            scored_sections.append((value, sec))
    
    # 按价值降序
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    
    # 3. 从高价值段落中提取候选命题
    all_candidates = []
    for value, sec in scored_sections[:8]:  # 只看前8个高价值段落
        props = extract_propositions_from_section(sec)
        for prop in props:
            all_candidates.append({
                "proposition": prop,
                "section": sec,
                "section_value": value,
            })
    
    if not all_candidates:
        # 如果没提取到任何候选，从最高价值段落中兜底提取第一句话
        if scored_sections:
            _, top_sec = scored_sections[0]
            first_sent = re.split(r'[。！？]', top_sec["content"])[0].strip()
            if len(first_sent) >= 15:
                all_candidates.append({
                    "proposition": first_sent,
                    "section": top_sec,
                    "section_value": 0.3,
                })
    
    if not all_candidates:
        return []
    
    # 4. 去重（内容相似的只保留一条）
    unique_candidates = deduplicate_candidates(all_candidates)
    
    # 5. 评分排序，取 Top 1-5
    # 综合评分 = 段落价值 * 0.6 + 命题长度适中度 * 0.4
    scored = []
    for c in unique_candidates:
        prop = c["proposition"]
        # 长度适中度：40-120字最佳
        length = len(prop)
        if 40 <= length <= 120:
            length_score = 1.0
        elif 20 <= length < 40:
            length_score = 0.6 + (length - 20) / 20 * 0.4
        elif 120 < length <= 200:
            length_score = 1.0 - (length - 120) / 80 * 0.4
        else:
            length_score = 0.3
        
        total_score = c["section_value"] * 0.6 + length_score * 0.4
        scored.append((total_score, c))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # 取 1-5 个（不少于1个，不多于5个）
    top_n = min(max(1, len(scored)), 5)
    selected = [c for _, c in scored[:top_n]]
    
    # 6. 构建节点对象
    nodes = []
    for c in selected:
        prop_text = c["proposition"].strip()
        sec = c["section"]
        
        # 清理命题文本（去掉列表标记、多余空白）
        prop_text = re.sub(r'^[-*+]\s+', '', prop_text)
        prop_text = re.sub(r'^\d+[.、]\s+', '', prop_text)
        prop_text = re.sub(r'\s+', ' ', prop_text).strip()
        
        node = {
            "proposition": prop_text,
            "concepts": generate_concepts(prop_text, sec["heading"]),
            "type": classify_proposition_type(prop_text),
            "source_file": source_file,
            "source_anchor": sec["heading"],
            "confidence": determine_confidence(prop_text, sec),
        }
        nodes.append(node)
    
    return nodes


def deduplicate_candidates(candidates: List[Dict]) -> List[Dict]:
    """
    对候选命题去重，基于 3-gram Jaccard 相似度。
    """
    if len(candidates) <= 1:
        return candidates
    
    def similarity(a: str, b: str) -> float:
        def ngrams(text, n=3):
            return set(text[i:i+n] for i in range(len(text)-n+1))
        na, nb = ngrams(a), ngrams(b)
        if not na or not nb:
            return 0.0
        return len(na & nb) / len(na | nb)
    
    kept = []
    for c in candidates:
        is_dup = False
        for k in kept:
            if similarity(c["proposition"], k["proposition"]) > 0.5:
                is_dup = True
                break
        if not is_dup:
            kept.append(c)
    
    return kept


# ---------- 索引更新 ----------

def update_index_with_nodes(index: Dict, nodes: List[Dict]) -> Dict:
    """
    将新节点加入索引，返回更新后的 index 字典。
    
    更新内容：
      - all_nodes: 追加新节点ID
      - concept_index: 为每个概念标签添加节点ID
      - stats: 更新总数统计
    """
    new_index = json.loads(json.dumps(index))  # deep copy
    
    for node in nodes:
        node_id = node["id"]
        concepts = node.get("concepts", [])
        node_type = node.get("type", "proposition")
        
        # 更新 all_nodes
        if node_id not in new_index.get("all_nodes", []):
            new_index.setdefault("all_nodes", []).append(node_id)
        
        # 更新 concept_index
        concept_index = new_index.setdefault("concept_index", {})
        for concept in concepts:
            if concept not in concept_index:
                concept_index[concept] = []
            if node_id not in concept_index[concept]:
                concept_index[concept].append(node_id)
        
        # 更新 stats
        stats = new_index.setdefault("stats", {})
        stats["total_nodes"] = len(new_index.get("all_nodes", []))
        stats["total_concepts"] = len(concept_index)
        by_type = stats.setdefault("by_type", {})
        by_type[node_type] = by_type.get(node_type, 0) + 1
    
    return new_index


# ---------- 主入口 ----------

def incremental_extract(text: str, source_file: str) -> Dict:
    """
    增量抽取主入口：从新文档中提取知识节点，写入文件并更新索引。
    
    Args:
        text: markdown 文档全文
        source_file: 源文件路径（用于溯源和幂等判断）
    
    Returns:
        dict: {
            "success": bool,
            "skipped": bool,           # 是否因为幂等被跳过
            "reason": str,             # 原因说明
            "new_nodes_count": int,    # 新增节点数量
            "new_node_ids": List[str], # 新增节点ID列表
            "nodes": List[Dict],       # 新增的完整节点数据
        }
    """
    # 1. 幂等检查
    existing_sources = get_existing_source_files()
    if source_file in existing_sources:
        return {
            "success": True,
            "skipped": True,
            "reason": f"源文件 {source_file} 已被抽取过，跳过（幂等）",
            "new_nodes_count": 0,
            "new_node_ids": [],
            "nodes": [],
        }
    
    # 2. 提取知识节点
    raw_nodes = extract_knowledge_nodes(text, source_file)
    
    if not raw_nodes:
        return {
            "success": True,
            "skipped": False,
            "reason": "未从文档中提取到符合条件的知识节点",
            "new_nodes_count": 0,
            "new_node_ids": [],
            "nodes": [],
        }
    
    # 3. 加载索引，分配ID
    index = load_knowledge_index()
    
    new_nodes = []
    new_node_ids = []
    
    for raw_node in raw_nodes:
        node_id = get_next_node_id(index)
        node = {"id": node_id, **raw_node}
        new_nodes.append(node)
        new_node_ids.append(node_id)
        # 临时更新索引以便下一个ID计算正确
        index["all_nodes"].append(node_id)
    
    # 4. 写入节点文件
    for node in new_nodes:
        # 生成文件名：kn_XXX_概念标签1.json（取第一个概念标签作为文件名提示）
        first_concept = node["concepts"][0] if node["concepts"] else "未分类"
        # 文件名安全化
        safe_concept = re.sub(r'[\\/:*?"<>|]', '_', first_concept)
        fname = f"{node['id']}_{safe_concept}.json"
        fpath = NODES_DIR / fname
        
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(node, f, ensure_ascii=False, indent=2)
    
    # 5. 更新索引文件（完整更新 stats 和 concept_index）
    # 重新加载原始索引（因为上面只更新了 all_nodes 用于ID分配）
    index = load_knowledge_index()
    updated_index = update_index_with_nodes(index, new_nodes)
    save_knowledge_index(updated_index)
    
    return {
        "success": True,
        "skipped": False,
        "reason": f"成功抽取 {len(new_nodes)} 个知识节点",
        "new_nodes_count": len(new_nodes),
        "new_node_ids": new_node_ids,
        "nodes": new_nodes,
    }


# ---------- 独立运行测试 ----------
if __name__ == "__main__":
    # 用一个示例 decision log 做测试
    test_doc = """# 关于记忆系统容量管理的决策

## 背景
近期 MEMORY.md 文件增长迅速，已接近 2000 行，检索效率下降明显。
需要建立主动的容量管理机制。

## 决策内容

### 容量管理原则
- 容量管理应当主动而非被动，不能等文件膨胀后才处理
- 压缩优先级：状态覆盖 > 标题精简 > 条目删除 > 正文压缩
- 三项必查规则：🔒规则不可删、核心数据保留、压缩可追溯

### 实施方法
1. 每周日凌晨自动扫描 MEMORY.md 核心状态锚点区
2. 识别已完成超过 2 周的项目条目，标记为可压缩
3. 将可压缩条目调用 condenser 模块压缩为摘要
4. 压缩后的条目必须保留关键信息 + 详情指引链接

## 验收标准
- 压缩后 MEMORY.md 体积减少 30% 以上
- 🔒规则区内容完全不动
- 所有压缩操作可通过 decision log 追溯
"""
    
    print("=" * 60)
    print("增量知识节点抽取器测试")
    print("=" * 60)
    
    result = incremental_extract(
        text=test_doc,
        source_file="recent_memory/decision/_test_sample_memory_capacity.md"
    )
    
    print(f"\n结果:")
    print(f"  成功: {result['success']}")
    print(f"  跳过: {result['skipped']}")
    print(f"  原因: {result['reason']}")
    print(f"  新增节点数: {result['new_nodes_count']}")
    print(f"  节点ID: {result['new_node_ids']}")
    
    print(f"\n节点详情:")
    for node in result["nodes"]:
        print(f"\n  [{node['id']}] ({node['type']}, {node['confidence']})")
        print(f"  命题: {node['proposition']}")
        print(f"  概念: {', '.join(node['concepts'])}")
        print(f"  来源: {node['source_anchor']}")
