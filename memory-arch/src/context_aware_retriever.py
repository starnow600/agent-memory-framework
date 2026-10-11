"""
PlugMem Phase 2 - ContextAwareRetriever 上下文感知检索器

上下文维度权重调整：
  - 时间维度：工作日/周末/凌晨/白天/晚间
  - 任务类型维度：投资/架构/工具/日常/学习研究/系统维护
  - 自动上下文检测：从当前时间 + query 关键词推断

不同上下文下的类别权重调整：
  - 工作日白天：投资类 ×1.3
  - 工作日晚间：学习研究类 ×1.2
  - 周末：学习/研究类 ×1.2，日常类 ×1.1
  - 凌晨：系统维护类 ×1.3
  - 紧急任务：高置信度记忆 ×1.2

开关：
  - ENABLE_CONTEXT_AWARE 环境变量控制总开关
  - 子开关：ENABLE_TIME_CONTEXT / ENABLE_TASK_CONTEXT

正向优势策略保持不变：
  - 只提升匹配上下文的记忆，不降低不匹配的
  - 冷启动保护：上下文检测不确定时跳过
  - β 控制强度，上限可调
"""

import json
import os
import re
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).parent.parent
NODES_DIR = BASE_DIR / "knowledge_nodes"

# 时区：东八区
TZ = timezone(timedelta(hours=8))


def _now() -> datetime:
    return datetime.now(TZ)


# ---------- 开关配置 ----------
ENABLE_CONTEXT_AWARE = os.environ.get("ENABLE_CONTEXT_AWARE", "false").lower() in (
    "true", "1", "yes"
)
ENABLE_TIME_CONTEXT = os.environ.get("ENABLE_TIME_CONTEXT", "true").lower() in (
    "true", "1", "yes"
)
ENABLE_TASK_CONTEXT = os.environ.get("ENABLE_TASK_CONTEXT", "true").lower() in (
    "true", "1", "yes"
)

# 上下文权重强度（类似 β，控制最大提升幅度）
CONTEXT_BETA = float(os.environ.get("CONTEXT_BETA", "0.15"))

# ---------- 任务类型定义 ----------
# 任务类型 → 关键词模式（用于从query自动检测任务类型）
TASK_TYPE_PATTERNS = {
    "投资": [
        r"反转", r"策略", r"止损", r"建仓", r"清仓", r"买入", r"卖出",
        r"A股", r"股票", r"机构调仓", r"MA20", r"RSI", r"布林带",
        r"板块", r"β", r"beta", r"行业中性", r"回测", r"胜率",
        r"风控", r"仓位", r"交易", r"抄底", r"逃顶", r"规避损失",
        r"Regime", r"regime", r"L3修正", r"v6\.0",
    ],
    "架构": [
        r"记忆", r"检索", r"索引", r"架构", r"节点", r"压缩", r"知识图谱",
        r"PlugMem", r"plugmem", r"RAG", r"向量", r"语义", r"流水线",
        r"数据结构", r"存储", r"缓存", r"L0", r"L1", r"L2",
    ],
    "工具": [
        r"PPT", r"ppt", r"DOCX", r"docx", r"网页抓取", r"爬虫", r"工具",
        r"技能", r"skill", r"路由", r"生成", r"导出", r"转换",
        r"图表", r"可视化", r"PDF", r"pdf", r"Excel", r"excel",
    ],
    "日常": [
        r"决策", r"规则", r"TODO", r"todo", r"任务", r"日程",
        r"每日", r"每周", r"话题追踪", r"风险标注", r"记忆捕获",
        r"同步", r"更新", r"检查",
    ],
    "学习研究": [
        r"学习", r"研究", r"论文", r"调研", r"分析", r"深度",
        r"原理", r"机制", r"理论", r"模型", r"算法", r"优化",
        r"对比", r"评估", r"评测",
    ],
    "系统维护": [
        r"修复", r"bug", r"错误", r"故障", r"维护", r"升级",
        r"迁移", r"备份", r"恢复", r"兼容", r"性能", r"优化",
        r"重构", r"清理", r"索引同步",
    ],
}

# 预编译正则表达式（性能优化）
_TASK_TYPE_REGEX_CACHE = {}


def _get_task_regex(task_type: str):
    """获取任务类型的预编译正则。"""
    if task_type in _TASK_TYPE_REGEX_CACHE:
        return _TASK_TYPE_REGEX_CACHE[task_type]
    
    patterns = TASK_TYPE_PATTERNS.get(task_type, [])
    # 合并成一个正则，用 | 分隔，单次匹配比多次循环快
    combined = "|".join(f"(?:{p})" for p in patterns)
    regex = re.compile(combined, re.IGNORECASE)
    _TASK_TYPE_REGEX_CACHE[task_type] = regex
    return regex

# 任务类型 → 节点类别匹配（用于判断节点是否属于该任务类型）
TASK_TO_NODE_CATEGORIES = {
    "投资": ["反转策略", "止损纪律", "机构调仓", "风控", "A股交易", "Regime切换"],
    "架构": ["记忆检索", "记忆架构", "记忆压缩", "知识节点", "索引", "评测体系"],
    "工具": ["PPT生成", "DOCX编辑", "网页抓取", "技能路由", "工具审计"],
    "日常": ["决策日志", "规则", "话题追踪", "风险标注", "记忆捕获"],
    "学习研究": ["探索成本", "深度解读", "理论研究"],
    "系统维护": ["索引同步", "规则同步", "销项机制", "上下文压缩"],
}

# ---------- 时间场景权重 ----------
# 格式：时间场景 → {任务类型: 权重乘数}
TIME_CONTEXT_WEIGHTS = {
    "workday_day": {      # 工作日白天 (9:00-18:00)
        "投资": 1.3,
        "日常": 1.1,
    },
    "workday_evening": {  # 工作日晚间 (18:00-23:00)
        "学习研究": 1.25,
        "架构": 1.15,
        "工具": 1.1,
    },
    "workday_night": {    # 工作日凌晨 (0:00-6:00)
        "系统维护": 1.3,
        "架构": 1.1,
    },
    "weekend_day": {      # 周末白天 (9:00-18:00)
        "学习研究": 1.3,
        "工具": 1.2,
        "日常": 1.15,
    },
    "weekend_evening": {  # 周末晚间 (18:00-23:00)
        "学习研究": 1.2,
        "架构": 1.15,
        "投资": 1.05,  # 周末复盘
    },
    "weekend_night": {    # 周末凌晨
        "系统维护": 1.2,
    },
}


# ============================================================
#  上下文检测
# ============================================================

def detect_time_context(now: Optional[datetime] = None) -> str:
    """
    根据当前时间检测时间场景。
    
    Returns:
        str: workday_day / workday_evening / workday_night /
             weekend_day / weekend_evening / weekend_night
    """
    if now is None:
        now = _now()
    
    is_weekend = now.weekday() >= 5  # 5=周六, 6=周日
    hour = now.hour
    
    if 6 <= hour < 9:
        period = "day"  # 早晨归入白天
    elif 9 <= hour < 18:
        period = "day"
    elif 18 <= hour < 23:
        period = "evening"
    else:
        period = "night"
    
    prefix = "weekend" if is_weekend else "workday"
    return f"{prefix}_{period}"


def detect_task_type(query: str) -> Tuple[str, float]:
    """
    从查询文本中自动检测任务类型。
    
    Args:
        query: 查询文本
    
    Returns:
        (task_type, confidence): 任务类型名称 + 置信度 0-1
    """
    if not query:
        return ("日常", 0.3)
    
    query_lower = query.lower()
    scores = {}
    
    for task_type in TASK_TYPE_PATTERNS:
        regex = _get_task_regex(task_type)
        matches = regex.findall(query_lower)
        hit_count = len(matches)
        
        if hit_count > 0:
            # 置信度：命中数，对数平滑
            # 命中1个 → ~0.33，命中3个 → ~0.70，命中5个 → ~0.86
            score = 1.0 - math.exp(-hit_count / 2.5)
            scores[task_type] = score
    
    if not scores:
        return ("日常", 0.2)  # 默认日常，低置信度
    
    # 返回得分最高的
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    
    # 检查是否有多个类型得分接近（模糊场景）
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) >= 2 and sorted_scores[0] - sorted_scores[1] < 0.1:
        best_score *= 0.8  # 降低置信度
    
    return (best_type, round(min(best_score, 1.0), 4))


def detect_context(query: str = "", now: Optional[datetime] = None) -> Dict:
    """
    综合检测当前上下文。
    
    Args:
        query: 查询文本（用于任务类型检测）
        now: 当前时间（用于时间场景检测）
    
    Returns:
        dict: {
            "time_context": str,
            "task_type": str,
            "task_confidence": float,
            "is_weekend": bool,
            "hour": int,
            "weights": {task_type: multiplier},  # 综合权重
            "confidence": float,  # 整体上下文置信度
        }
    """
    if now is None:
        now = _now()
    
    time_ctx = detect_time_context(now)
    task_type, task_conf = detect_task_type(query)
    
    # 时间场景对应的权重
    time_weights = TIME_CONTEXT_WEIGHTS.get(time_ctx, {})
    
    # 综合权重：时间权重 + 任务类型权重（如果任务类型置信度高）
    combined_weights = dict(time_weights)
    
    # 如果检测到明确的任务类型，额外加强
    if task_conf > 0.5 and task_type not in combined_weights:
        combined_weights[task_type] = 1.0 + task_conf * 0.2
    
    overall_confidence = min(1.0, 0.5 + task_conf * 0.5)
    
    # 提取查询中的细粒度概念关键词（用于概念级匹配）
    query_concepts = extract_query_concepts(query)
    
    return {
        "time_context": time_ctx,
        "task_type": task_type,
        "task_confidence": task_conf,
        "is_weekend": now.weekday() >= 5,
        "hour": now.hour,
        "weights": combined_weights,
        "confidence": round(overall_confidence, 4),
        "query_concepts": query_concepts,
        "query_text": query,
    }


# ============================================================
#  查询概念提取（细粒度匹配用）
# ============================================================

def extract_query_concepts(query: str) -> List[str]:
    """
    从查询文本中提取细粒度概念关键词。
    
    匹配策略：
    1. 遍历所有已知的节点concept，找出在query中出现的
    2. 加上TASK_TYPE_PATTERNS中匹配到的关键词
    3. 去重返回
    
    Args:
        query: 查询文本
    
    Returns:
        list: 概念关键词列表
    """
    if not query:
        return []
    
    query_lower = query.lower()
    concepts = []
    
    # 1. 从节点概念库中匹配（懒加载）
    try:
        all_concepts = _get_all_node_concepts()
        for concept in all_concepts:
            # 完整匹配或核心词匹配（长度>=2的概念才匹配，避免单字噪声）
            if len(concept) >= 2 and concept.lower() in query_lower:
                concepts.append(concept)
    except Exception:
        pass
    
    # 2. 从任务类型模式中提取匹配到的关键词
    for task_type, patterns in TASK_TYPE_PATTERNS.items():
        for pattern in patterns:
            try:
                if re.search(pattern, query, re.IGNORECASE):
                    # 从正则模式中提取有意义的关键词（去掉转义）
                    keyword = pattern.replace(r'\.', '.').strip('^$')
                    if len(keyword) >= 2:
                        concepts.append(keyword)
            except re.error:
                pass
    
    # 去重并返回
    return list(dict.fromkeys(concepts))


_all_concepts_cache = None

def _get_all_node_concepts() -> List[str]:
    """获取所有节点的概念集合（懒加载+缓存）。"""
    global _all_concepts_cache
    if _all_concepts_cache is not None:
        return _all_concepts_cache
    
    concepts = set()
    try:
        if NODES_DIR.exists():
            for f in NODES_DIR.glob('*.json'):
                try:
                    with open(f, 'r', encoding='utf-8') as fh:
                        node = json.load(fh)
                    for c in node.get('concepts', []):
                        concepts.add(c)
                except Exception:
                    continue
    except Exception:
        pass
    
    _all_concepts_cache = list(concepts)
    return _all_concepts_cache


# ============================================================
#  节点任务类型推断
# ============================================================

def infer_node_task_type(node: Dict) -> List[str]:
    """
    推断知识节点的任务类型标签。
    
    根据节点的 concepts 和 proposition 内容推断。
    返回可能的任务类型列表（按匹配度降序）。
    
    Args:
        node: 知识节点字典
    
    Returns:
        list: ["投资", "架构", ...]
    """
    concepts = [c.lower() for c in node.get("concepts", [])]
    proposition = node.get("proposition", "").lower()
    all_text = " ".join(concepts) + " " + proposition
    
    scores = {}
    
    for task_type, categories in TASK_TO_NODE_CATEGORIES.items():
        hit_count = 0
        for cat in categories:
            cat_lower = cat.lower()
            # 检查概念中是否包含类别关键词
            for concept in concepts:
                if cat_lower in concept or concept in cat_lower:
                    hit_count += 1
                    break
            # 检查命题中是否包含
            if cat_lower in proposition:
                hit_count += 0.5
        
        if hit_count > 0:
            scores[task_type] = hit_count
    
    # 也用 TASK_TYPE_PATTERNS 匹配一次（更细粒度）
    for task_type, patterns in TASK_TYPE_PATTERNS.items():
        pattern_hits = sum(
            1 for p in patterns
            if re.search(p, all_text, re.IGNORECASE)
        )
        if pattern_hits > 0:
            scores[task_type] = scores.get(task_type, 0) + pattern_hits * 0.3
    
    sorted_types = sorted(scores.keys(), key=lambda t: scores[t], reverse=True)
    return sorted_types


def get_context_weight_for_node(node: Dict, context: Dict) -> float:
    """
    计算节点在当前上下文中的权重乘数。
    
    正向优势策略：
    - 匹配上下文的节点获得权重提升（>1.0）
    - 不匹配的节点权重不变（=1.0）
    - 上下文置信度低时，提升幅度打折
    
    Args:
        node: 知识节点字典
        context: detect_context() 返回的上下文字典
    
    Returns:
        float: 权重乘数（≥1.0，正向优势）
    """
    ctx_confidence = context.get("confidence", 0.5)
    
    # 冷启动保护：上下文置信度太低时不调整
    if ctx_confidence < 0.3:
        return 1.0
    
    node_task_types = infer_node_task_type(node)
    if not node_task_types:
        return 1.0
    
    weights = context.get("weights", {})
    
    # 找节点最强匹配的任务类型的权重
    max_multiplier = 1.0
    for nt in node_task_types:
        if nt in weights:
            mult = weights[nt]
            if mult > max_multiplier:
                max_multiplier = mult
    
    if max_multiplier <= 1.0:
        return 1.0
    
    # 上下文置信度折扣：置信度越低，提升越小
    # 当 confidence=1.0 时，全额提升
    # 当 confidence=0.3 时，几乎不提升（刚过冷启动阈值）
    discount = (ctx_confidence - 0.3) / 0.7
    discount = max(0.0, min(1.0, discount))
    
    # 实际乘数 = 1.0 + (max_multiplier - 1.0) * discount * beta_strength
    # beta_strength 由 CONTEXT_BETA 控制
    boost = (max_multiplier - 1.0) * discount * CONTEXT_BETA / 0.15
    boost = max(0.0, min(boost, max_multiplier - 1.0))
    
    return round(1.0 + boost, 4)


# ============================================================
#  ContextAwareRetriever 类
# ============================================================

class ContextAwareRetriever:
    """
    上下文感知检索器。
    
    包装 hybrid_retriever，在检索结果上叠加上下文感知的权重调整。
    
    功能：
    1. detect_context(query): 检测当前上下文
    2. apply_context_boost(results, context): 对结果应用上下文权重
    3. retrieve(query, ...): 完整的上下文感知检索
    
    正向优势策略一致：
    - 只提升匹配上下文的记忆，不降低其他记忆
    - 上下文置信度不足时跳过（冷启动保护）
    - 可配置强度 β
    
    用法：
        car = ContextAwareRetriever()
        results = car.retrieve("v6.0反转模式L3修正", max_results=3)
    """
    
    def __init__(
        self,
        enable: Optional[bool] = None,
        beta: Optional[float] = None,
    ):
        """
        初始化上下文感知检索器。
        
        Args:
            enable: 是否启用（None则用环境变量）
            beta: 上下文权重强度
        """
        self.enable = enable if enable is not None else ENABLE_CONTEXT_AWARE
        self.beta = beta if beta is not None else CONTEXT_BETA
        self._node_cache = {}
        self._node_task_type_cache = {}  # node_id -> task_types 列表缓存
    
    def _load_node(self, node_id: str) -> Optional[Dict]:
        """加载知识节点（带内存缓存）。"""
        if node_id in self._node_cache:
            return self._node_cache[node_id]
        
        from .value_estimator import _load_knowledge_node
        node = _load_knowledge_node(node_id)
        self._node_cache[node_id] = node
        return node
    
    def detect_context(self, query: str = "",
                       now: Optional[datetime] = None) -> Dict:
        """检测当前上下文。"""
        return detect_context(query, now)
    
    def _infer_node_task_type_cached(self, node_id: str, node: Dict) -> List[str]:
        """带缓存的节点任务类型推断。"""
        if node_id in self._node_task_type_cache:
            return self._node_task_type_cache[node_id]
        
        result = infer_node_task_type(node)
        self._node_task_type_cache[node_id] = result
        return result
    
    def apply_context_boost(self, results: List[Dict],
                             context: Dict) -> List[Dict]:
        """
        对检索结果应用上下文感知权重提升。
        
        正向优势策略（与价值重排序一致）：
        - 只向前提升排名，不向后拉低
        - 上下文置信度低时跳过（冷启动保护）
        - 提升幅度受 beta 控制（最多前移 β*N 个位置）
        - 不修改 confidence 值，只调整排序位置
        
        Args:
            results: hybrid_retrieve 返回的结果列表
            context: detect_context() 返回的上下文
        
        Returns:
            调整后的结果列表
        """
        if not self.enable or not results:
            return results
        
        n = len(results)
        if n < 2:
            return results
        
        # 冷启动保护：上下文置信度不足
        if context.get("confidence", 0) < 0.3:
            return results
        
        weights = context.get("weights", {})
        ctx_confidence = context.get("confidence", 0.5)
        ctx_task_type = context.get("task_type", "")
        query_concepts = context.get("query_concepts", [])
        query_text = context.get("query_text", "")
        
        # 第一步：计算每条结果的上下文匹配强度（两级匹配：任务类型 + 细粒度概念）
        match_scores = []
        for r in results:
            node = self._load_node(r.get("node_id", ""))
            if not node:
                match_scores.append(0.0)
                continue
            
            node_task_types = self._infer_node_task_type_cached(r.get("node_id", ""), node)
            node_concepts = set(node.get("concepts", []))
            
            # Level 1: 任务类型匹配（粗粒度）
            type_score = 0.0
            if weights and node_task_types:
                max_mult = max(
                    (weights.get(nt, 1.0) for nt in node_task_types),
                    default=1.0
                )
                max_weight = max(weights.values()) if weights else 1.0
                if max_weight > 1.0:
                    type_score = (max_mult - 1.0) / (max_weight - 1.0)
            
            # Level 2: 细粒度概念匹配（查询概念 vs 节点概念）
            concept_score = 0.0
            if query_concepts and node_concepts:
                # Jaccard相似度：交集/并集
                intersection = len(set(query_concepts) & node_concepts)
                union = len(set(query_concepts) | node_concepts)
                if union > 0:
                    concept_score = intersection / union
            
            # Level 3: 关键词字面匹配（兜底，query文本 vs 节点concept关键词）
            keyword_score = 0.0
            if query_text and node_concepts:
                query_lower = query_text.lower()
                matched = sum(
                    1 for concept in node_concepts
                    if concept.lower() in query_lower or query_lower in concept.lower()
                )
                if node_concepts:
                    keyword_score = min(1.0, matched / 2.0)  # 匹配2个以上概念=满分
            
            # 综合匹配分（概念匹配权重最高，任务类型作基础分）
            # concept_score 范围 [0,1]，type_score 范围 [0,1]，keyword_score [0,1]
            combined = (
                concept_score * 0.6 +   # 细粒度概念匹配是核心信号
                keyword_score * 0.25 +   # 关键词字面匹配作补充
                type_score * 0.15        # 粗粒度任务类型打底
            )
            
            # 上下文置信度折扣
            discount = (ctx_confidence - 0.3) / 0.7
            discount = max(0.0, min(1.0, discount))
            
            match_scores.append(combined * discount)
        
        # 第二步：冷启动保护——区分度不足时跳过
        max_match = max(match_scores) if match_scores else 0
        if max_match < 0.15:
            return results
        
        # 额外保护：最好和次好差异太小（<0.1），不调整（避免边界误判）
        sorted_scores = sorted(match_scores, reverse=True)
        if len(sorted_scores) >= 2 and sorted_scores[0] - sorted_scores[1] < 0.1:
            return results
        
        # 第三步：正向优势排序调整（相对优势归一化）
        # 与value_adjust策略一致：只有相对优势为正的才提升
        # 优势 = match_score - avg(match_scores)
        avg_match = sum(match_scores) / len(match_scores)
        advantages = [s - avg_match for s in match_scores]
        
        max_pos_adv = max(0.001, max(0, max(advantages)))
        
        boosts = []
        max_boost_steps = int(round(self.beta * n))
        max_boost_steps = max(1, min(max_boost_steps, n - 1))
        
        for i, (score, adv) in enumerate(zip(match_scores, advantages)):
            if adv <= 0:
                boosts.append(0)
            else:
                # 优势归一化到 [0, max_boost_steps]
                boost = int(round((adv / max_pos_adv) * max_boost_steps))
                boost = min(boost, i)
                boosts.append(boost)
        
        # 第四步：按boost重新放置元素
        # 从前往后，boost大的往前放；同boost的保持原顺序
        final_items = []
        for i, r in enumerate(results):
            target_pos = max(0, i - boosts[i])
            final_items.append((target_pos, i, r, boosts[i]))
        
        final_items.sort(key=lambda x: (x[0], x[1]))
        
        # 第五步：平票决胜
        # 在confidence相近（差异<0.05）的连续节点组内，按match_score重新排序
        # 这是细粒度匹配的核心价值：打破基础检索的平局
        adjusted_pre = []
        for target_pos, orig_idx, r, boost in final_items:
            new_r = dict(r)
            if boost > 0:
                new_r["context_boosted"] = True
                new_r["context_boost_steps"] = boost
            new_r["_orig_idx"] = orig_idx
            new_r["_match_score"] = match_scores[orig_idx]
            new_r["context_type"] = ctx_task_type
            new_r["context_match_score"] = round(match_scores[orig_idx], 4)
            adjusted_pre.append(new_r)
        
        # 分组：confidence差<0.05的连续节点算一组
        if adjusted_pre:
            groups = []
            current_group = [adjusted_pre[0]]
            for i in range(1, len(adjusted_pre)):
                prev_conf = adjusted_pre[i-1].get('confidence', 0)
                curr_conf = adjusted_pre[i].get('confidence', 0)
                if abs(prev_conf - curr_conf) < 0.05:
                    current_group.append(adjusted_pre[i])
                else:
                    groups.append(current_group)
                    current_group = [adjusted_pre[i]]
            groups.append(current_group)
            
            # 每组内按match_score降序重排（match_score相同则保持原顺序）
            adjusted = []
            for group in groups:
                if len(group) > 1:
                    group.sort(key=lambda x: (-x['_match_score'], x['_orig_idx']))
                adjusted.extend(group)
        else:
            adjusted = adjusted_pre
        
        # 清理临时字段
        for r in adjusted:
            r.pop('_orig_idx', None)
            r.pop('_match_score', None)
        
        return adjusted
    
    def retrieve(self, query: str, max_results: int = 3,
                 use_semantic_fallback: bool = True,
                 enable_value_rerank: bool = None,
                 value_beta: float = None,
                 context: Optional[Dict] = None) -> List[Dict]:
        """
        上下文感知检索主入口。
        
        流水线：
        1. hybrid_retrieve（概念路由 + 语义兜底 + 价值重排序）
        2. 上下文感知权重提升
        3. 返回最终结果
        
        Args:
            query: 查询文本
            max_results: 返回最大结果数
            use_semantic_fallback: 是否启用语义兜底
            enable_value_rerank: 是否启用价值重排序
            value_beta: 价值重排序 β
            context: 可选，手动指定上下文；为None时自动检测
        
        Returns:
            结构化检索结果列表
        """
        # 第一步：基础混合检索
        import sys
        sys.path.insert(0, str(BASE_DIR))
        from hybrid_retriever import hybrid_retrieve
        
        # 基础检索返回更多候选，便于上下文调整
        base_results = hybrid_retrieve(
            query,
            max_results=max_results * 2,  # 多拿一些候选
            use_semantic_fallback=use_semantic_fallback,
            enable_value_rerank=enable_value_rerank,
            value_beta=value_beta,
        )
        
        if not self.enable:
            # 未启用，直接截断返回
            return base_results[:max_results]
        
        # 第二步：检测上下文
        if context is None:
            context = self.detect_context(query)
        
        # 第三步：上下文权重提升
        boosted = self.apply_context_boost(base_results, context)
        
        # 截断返回
        final = boosted[:max_results]
        
        # 添加上下文信息到第一条（便于调试）
        if final:
            final[0]["_context"] = {
                "time_context": context.get("time_context"),
                "task_type": context.get("task_type"),
                "confidence": context.get("confidence"),
            }
        
        return final


# ============================================================
#  模块级快捷函数
# ============================================================

_car_instance: Optional[ContextAwareRetriever] = None


def _get_car() -> ContextAwareRetriever:
    """获取单例上下文感知检索器。"""
    global _car_instance
    if _car_instance is None:
        _car_instance = ContextAwareRetriever()
    return _car_instance


def context_aware_retrieve(query: str, max_results: int = 3, **kwargs) -> List[Dict]:
    """快捷函数：上下文感知检索。"""
    return _get_car().retrieve(query, max_results, **kwargs)


def detect_context_from_query(query: str) -> Dict:
    """快捷函数：从查询检测上下文。"""
    return detect_context(query)


# ---------- 独立运行 ----------
if __name__ == "__main__":
    print("=" * 60)
    print("ContextAwareRetriever 测试")
    print("=" * 60)
    
    car = ContextAwareRetriever(enable=True, beta=0.2)
    
    # 测试上下文检测
    test_queries = [
        "v6.0反转模式L3修正的核心逻辑是什么",
        "记忆检索的标准流程是怎样的",
        "高风险操作校验规则是什么",
        "DOCX文档怎么批量处理",
    ]
    
    print("\n【上下文检测】")
    for q in test_queries:
        ctx = car.detect_context(q)
        print(f"  Query: {q[:30]}...")
        print(f"    时间场景: {ctx['time_context']}, "
              f"任务类型: {ctx['task_type']} "
              f"(置信度: {ctx['task_confidence']:.2f})")
        print(f"    权重: {ctx['weights']}")
    
    # 测试上下文感知检索
    print("\n【上下文感知检索对比】")
    query = "反转策略的U型分布是什么意思"
    
    from hybrid_retriever import hybrid_retrieve
    base_results = hybrid_retrieve(query, max_results=3, enable_value_rerank=True)
    
    # 模拟工作日白天（投资类加成）
    ctx_workday = {
        "time_context": "workday_day",
        "task_type": "投资",
        "task_confidence": 0.8,
        "confidence": 0.9,
        "weights": {"投资": 1.3},
    }
    
    # 模拟周末（学习研究类加成）
    ctx_weekend = {
        "time_context": "weekend_day",
        "task_type": "学习研究",
        "task_confidence": 0.7,
        "confidence": 0.85,
        "weights": {"学习研究": 1.3, "工具": 1.2},
    }
    
    print(f"  Query: {query}")
    print(f"  基线排序:")
    for i, r in enumerate(base_results, 1):
        print(f"    {i}. {r['node_id']} (conf={r['confidence']:.3f}) - {r['content'][:40]}...")
    
    print(f"\n  工作日白天下（投资加成）:")
    results_workday = car.apply_context_boost(base_results, ctx_workday)
    for i, r in enumerate(results_workday[:3], 1):
        boosted = " ⬆" if r.get("context_boosted") else ""
        print(f"    {i}. {r['node_id']} (conf={r['confidence']:.3f}){boosted} - {r['content'][:40]}...")
    
    print(f"\n  周末下（学习研究加成）:")
    results_weekend = car.apply_context_boost(base_results, ctx_weekend)
    for i, r in enumerate(results_weekend[:3], 1):
        boosted = " ⬆" if r.get("context_boosted") else ""
        print(f"    {i}. {r['node_id']} (conf={r['confidence']:.3f}){boosted} - {r['content'][:40]}...")
    
    # 计算排序差异
    base_ids = [r['node_id'] for r in base_results[:3]]
    workday_ids = [r['node_id'] for r in results_workday[:3]]
    diff = sum(1 for a, b in zip(base_ids, workday_ids) if a != b)
    print(f"\n  工作日白天下 Top-3 排序差异: {diff}/3 ({diff/3*100:.0f}%)")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
