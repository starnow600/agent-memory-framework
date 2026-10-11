"""
PlugMem Phase 1 - ValueEstimator V1 价值评估器

多维度记忆价值评分：
  - 使用频率 (20%)：从 feedback_log.jsonl 统计引用次数
  - 最近使用时间 (15%)：指数时间衰减
  - 置信度映射 (25%)：high=0.8 / medium=0.5 / low=0.2
  - 来源可靠性 (15%)：decision > wiki > trace > 其他
  - 人工反馈 (25%)：指数滑动平均，初始为 0

价值优势计算：
  A(m, category) = value_score(m) - avg_value(category)

价值评分更新公式（有新反馈时）：
  value_score_new = alpha * value_score_old + (1 - alpha) * feedback_score
  alpha = 0.7（历史权重高，抗噪）

β 为价值权重系数，用于检索重排序，默认 0.2。
"""

import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Any

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).parent.parent
NODES_DIR = BASE_DIR / "knowledge_nodes"
INDEX_PATH = BASE_DIR / "knowledge_index.json"
FEEDBACK_LOG_PATH = BASE_DIR / "feedback_log.jsonl"

# 时区：东八区
TZ = timezone(timedelta(hours=8))


def _now_iso() -> str:
    """获取当前时间的 ISO 格式字符串（东八区）"""
    return datetime.now(TZ).isoformat()


def _parse_iso(ts: str) -> datetime:
    """解析 ISO 格式时间字符串"""
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        # 兼容只有日期的格式
        try:
            return datetime.strptime(ts, "%Y-%m-%d").replace(tzinfo=TZ)
        except (ValueError, TypeError):
            return datetime.now(TZ)


# ---------- 权重配置 ----------
DEFAULT_WEIGHTS = {
    "frequency": 0.20,      # 使用频率
    "recency": 0.15,        # 最近使用时间
    "confidence": 0.25,     # 置信度映射
    "source_reliability": 0.15,  # 来源可靠性
    "human_feedback": 0.25, # 人工反馈
}

# 置信度 → 分数映射
CONFIDENCE_MAP = {
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2,
}

# 来源可靠性 → 分数映射
SOURCE_RELIABILITY_MAP = {
    "decision": 0.9,
    "wiki": 0.7,
    "trace": 0.4,
    "project": 0.6,
    "narrative": 0.5,
}

# 默认值
DEFAULT_SOURCE_RELIABILITY = 0.5
DEFAULT_CONFIDENCE_SCORE = 0.5

# 时间衰减半衰期（天）：每经过 HALF_LIFE_DAYS 天，recency 分数减半
RECENCY_HALF_LIFE_DAYS = 30

# EMA 更新参数
DEFAULT_ALPHA = 0.7  # 历史权重

# 节点文件缓存
_node_file_cache = None


# ============================================================
#  工具函数
# ============================================================

def _load_knowledge_node(node_id: str) -> Optional[Dict]:
    """根据 node_id 加载单个知识节点文件（带缓存）。"""
    if not NODES_DIR.exists():
        return None
    
    # 使用文件名缓存，避免每次遍历目录
    global _node_file_cache
    if _node_file_cache is None:
        _node_file_cache = {}
        for fname in os.listdir(NODES_DIR):
            if fname.startswith("kn_") and fname.endswith(".json"):
                # 提取 kn_NNN
                parts = fname.split("_")
                if len(parts) >= 2:
                    nid = f"kn_{parts[1]}"
                    _node_file_cache[nid] = fname
    
    fname = _node_file_cache.get(node_id)
    if not fname:
        return None
    
    with open(NODES_DIR / fname, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_knowledge_index() -> Dict:
    """加载知识索引。"""
    if not INDEX_PATH.exists():
        return {}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_feedback_log() -> List[Dict]:
    """加载反馈日志，返回列表。"""
    if not FEEDBACK_LOG_PATH.exists():
        return []
    entries = []
    with open(FEEDBACK_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _get_feedback_stats(feedback_entries: List[Dict], node_id: str) -> Dict:
    """
    从反馈日志中统计指定节点的反馈数据。
    
    Returns:
        dict: {
            "use_count": int,              # 使用/反馈总次数
            "last_use_time": datetime,     # 最近一次使用时间
            "avg_feedback": float,         # 平均反馈分数（归一化到 0-1）
            "explicit_count": int,         # 显式反馈次数
            "implicit_positive_count": int # 隐式正反馈次数
        }
    """
    use_count = 0
    last_use_time = None
    feedback_scores = []
    explicit_count = 0
    implicit_positive = 0
    
    for entry in feedback_entries:
        if entry.get("memory_id") != node_id:
            continue
        
        ts = _parse_iso(entry.get("timestamp", ""))
        if last_use_time is None or ts > last_use_time:
            last_use_time = ts
        
        use_count += 1
        source = entry.get("source", "explicit")
        
        if source == "explicit":
            explicit_count += 1
            # 显式反馈 rating 1-5 → 归一化到 0-1
            rating = entry.get("rating", 3)
            norm_score = (rating - 1) / 4.0  # 1→0, 3→0.5, 5→1
            feedback_scores.append(norm_score)
        elif source == "implicit":
            action = entry.get("action", "")
            if action == "referenced":
                implicit_positive += 1
                # 隐式正反馈给 0.6 分（中等正向）
                feedback_scores.append(0.6)
            elif action == "not_used":
                # 未被使用，不给分但计入使用频率
                pass
    
    avg_feedback = sum(feedback_scores) / len(feedback_scores) if feedback_scores else 0.0
    
    return {
        "use_count": use_count,
        "last_use_time": last_use_time,
        "avg_feedback": avg_feedback,
        "explicit_count": explicit_count,
        "implicit_positive_count": implicit_positive,
    }


def _compute_frequency_score(use_count: int) -> float:
    """
    使用频率评分：对数归一化到 0-1。
    使用次数越多，分数越高，但边际递减。
    
    f(x) = 1 - exp(-x / 5)
    - 0次 → 0
    - 1次 → 0.181
    - 3次 → 0.451
    - 5次 → 0.632
    - 10次 → 0.865
    - 20次 → 0.982
    """
    if use_count <= 0:
        return 0.0
    return 1.0 - math.exp(-use_count / 5.0)


def _compute_recency_score(last_use_time: Optional[datetime]) -> float:
    """
    最近使用时间评分：指数衰减。
    越近使用分数越高，从未使用则给 0.3 的基础分。
    
    半衰期 = RECENCY_HALF_LIFE_DAYS 天
    """
    if last_use_time is None:
        return 0.3  # 从未使用，给基础分
    
    now = datetime.now(TZ)
    # 如果 last_use_time 没有时区，补上 TZ
    if last_use_time.tzinfo is None:
        last_use_time = last_use_time.replace(tzinfo=TZ)
    
    days_ago = (now - last_use_time).total_seconds() / 86400.0
    
    if days_ago <= 0:
        return 1.0
    
    # 指数衰减：score = 0.5^(days / half_life)
    score = math.pow(0.5, days_ago / RECENCY_HALF_LIFE_DAYS)
    return max(0.0, min(1.0, score))


def _infer_source_category(node: Dict) -> str:
    """
    根据知识节点信息推断来源类别，用于可靠性评分。
    
    优先级：
    1. node 中显式的 category / source_type 字段
    2. 根据 source_file 路径推断
    3. 默认 "other"
    """
    # 显式字段
    if node.get("category") in SOURCE_RELIABILITY_MAP:
        return node["category"]
    if node.get("source_type") in SOURCE_RELIABILITY_MAP:
        return node["source_type"]
    
    # 根据 source_file 路径推断
    source_file = node.get("source_file", "").lower()
    if "decision" in source_file:
        return "decision"
    if "wiki" in source_file or "llm-wiki" in source_file:
        return "wiki"
    if "trace" in source_file or "daily_memory" in source_file:
        return "trace"
    if "project" in source_file:
        return "project"
    if "narrative" in source_file:
        return "narrative"
    
    return "other"


# ============================================================
#  ValueEstimator 类
# ============================================================

class ValueEstimator:
    """
    记忆价值评估器 V1。
    
    多维度加权综合评分，支持：
    - estimate_value(memory_id): 计算单个记忆的综合价值分
    - get_advantage(memory_id, category): 计算价值优势（相对同类平均）
    - update_value(memory_id, feedback_score): 用 EMA 更新价值分并写回节点文件
    
    用法：
        estimator = ValueEstimator()
        score = estimator.estimate_value("kn_001")
        advantage = estimator.get_advantage("kn_001", "反转策略")
        estimator.update_value("kn_001", 0.8)
    """
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        alpha: float = DEFAULT_ALPHA,
        beta: float = 0.2,
    ):
        """
        初始化价值评估器。
        
        Args:
            weights: 各维度权重，默认 DEFAULT_WEIGHTS
            alpha: EMA 更新的历史权重，默认 0.7
            beta: 价值重排序权重系数，默认 0.2
        """
        self.weights = weights or DEFAULT_WEIGHTS
        self.alpha = alpha
        self.beta = beta
        
        # 缓存
        self._feedback_cache: Optional[List[Dict]] = None
        self._index_cache: Optional[Dict] = None
    
    def _get_feedback_entries(self) -> List[Dict]:
        """获取反馈日志（带缓存）。"""
        if self._feedback_cache is None:
            self._feedback_cache = _load_feedback_log()
        return self._feedback_cache
    
    def _invalidate_feedback_cache(self):
        """反馈日志有更新时调用。"""
        self._feedback_cache = None
    
    def _get_index(self) -> Dict:
        """获取知识索引（带缓存）。"""
        if self._index_cache is None:
            self._index_cache = _load_knowledge_index()
        return self._index_cache
    
    # --------------------------------------------------------
    #  各维度评分
    # --------------------------------------------------------
    
    def score_frequency(self, node_id: str) -> float:
        """使用频率维度评分 (0-1)。"""
        feedback = self._get_feedback_entries()
        stats = _get_feedback_stats(feedback, node_id)
        return _compute_frequency_score(stats["use_count"])
    
    def score_recency(self, node_id: str) -> float:
        """最近使用时间维度评分 (0-1)。"""
        feedback = self._get_feedback_entries()
        stats = _get_feedback_stats(feedback, node_id)
        return _compute_recency_score(stats["last_use_time"])
    
    def score_confidence(self, node: Dict) -> float:
        """置信度维度评分 (0-1)。"""
        conf = node.get("confidence", "medium")
        return CONFIDENCE_MAP.get(conf, DEFAULT_CONFIDENCE_SCORE)
    
    def score_source_reliability(self, node: Dict) -> float:
        """来源可靠性维度评分 (0-1)。"""
        category = _infer_source_category(node)
        return SOURCE_RELIABILITY_MAP.get(category, DEFAULT_SOURCE_RELIABILITY)
    
    def score_human_feedback(self, node_id: str) -> float:
        """人工反馈维度评分 (0-1)。"""
        feedback = self._get_feedback_entries()
        stats = _get_feedback_stats(feedback, node_id)
        
        total_feedback = stats["explicit_count"] + stats["implicit_positive_count"]
        if total_feedback == 0:
            return 0.0  # 无反馈时为 0
        
        return stats["avg_feedback"]
    
    # --------------------------------------------------------
    #  综合价值评分
    # --------------------------------------------------------
    
    def estimate_value(self, memory_id: str, node: Optional[Dict] = None) -> float:
        """
        计算单个记忆的综合价值评分 (0-1)。
        
        5 个维度加权求和：
            value = Σ(weight_i * score_i)
        
        Args:
            memory_id: 记忆节点 ID（如 "kn_001"）
            node: 可选，已加载的节点字典；为 None 时自动加载
        
        Returns:
            float: 综合价值评分，范围 [0, 1]
        """
        if node is None:
            node = _load_knowledge_node(memory_id)
            if node is None:
                return 0.0
        
        # 各维度评分
        freq_score = self.score_frequency(memory_id)
        recency_score = self.score_recency(memory_id)
        conf_score = self.score_confidence(node)
        source_score = self.score_source_reliability(node)
        feedback_score = self.score_human_feedback(memory_id)
        
        # 加权求和
        total = (
            self.weights["frequency"] * freq_score
            + self.weights["recency"] * recency_score
            + self.weights["confidence"] * conf_score
            + self.weights["source_reliability"] * source_score
            + self.weights["human_feedback"] * feedback_score
        )
        
        return round(max(0.0, min(1.0, total)), 4)
    
    def estimate_value_detail(self, memory_id: str, node: Optional[Dict] = None) -> Dict:
        """
        计算综合价值评分并返回各维度明细。
        
        Returns:
            dict: {
                "total": float,
                "frequency": {"score": float, "weight": float},
                "recency": {"score": float, "weight": float},
                "confidence": {"score": float, "weight": float},
                "source_reliability": {"score": float, "weight": float},
                "human_feedback": {"score": float, "weight": float},
            }
        """
        if node is None:
            node = _load_knowledge_node(memory_id)
            if node is None:
                return {"total": 0.0}
        
        freq_s = self.score_frequency(memory_id)
        recency_s = self.score_recency(memory_id)
        conf_s = self.score_confidence(node)
        source_s = self.score_source_reliability(node)
        feedback_s = self.score_human_feedback(memory_id)
        
        total = (
            self.weights["frequency"] * freq_s
            + self.weights["recency"] * recency_s
            + self.weights["confidence"] * conf_s
            + self.weights["source_reliability"] * source_s
            + self.weights["human_feedback"] * feedback_s
        )
        
        return {
            "total": round(max(0.0, min(1.0, total)), 4),
            "frequency": {"score": round(freq_s, 4), "weight": self.weights["frequency"]},
            "recency": {"score": round(recency_s, 4), "weight": self.weights["recency"]},
            "confidence": {"score": round(conf_s, 4), "weight": self.weights["confidence"]},
            "source_reliability": {"score": round(source_s, 4), "weight": self.weights["source_reliability"]},
            "human_feedback": {"score": round(feedback_s, 4), "weight": self.weights["human_feedback"]},
        }
    
    # --------------------------------------------------------
    #  价值优势
    # --------------------------------------------------------
    
    def get_advantage(self, memory_id: str, category: Optional[str] = None) -> float:
        """
        计算价值优势：A(m, category) = value_score(m) - avg_value(category)
        
        如果 category 为 None 或不存在，则用整体平均价值分。
        
        Args:
            memory_id: 记忆节点 ID
            category: 类别（概念名或类别名），用于找平均值
        
        Returns:
            float: 价值优势，可正可负
        """
        # 计算当前记忆的价值分
        node = _load_knowledge_node(memory_id)
        if node is None:
            return 0.0
        my_value = self.estimate_value(memory_id, node)
        
        # 获取类别平均价值分
        index = self._get_index()
        value_stats = index.get("value_stats", {})
        
        avg_value = None
        
        # 1. 优先从 by_concept 中找
        if category and "by_concept" in value_stats:
            concept_stats = value_stats["by_concept"].get(category)
            if concept_stats:
                avg_value = concept_stats.get("avg_value_score")
        
        # 2. 用节点的 concepts 找第一个匹配的概念
        if avg_value is None and node.get("concepts") and "by_concept" in value_stats:
            for concept in node["concepts"]:
                cs = value_stats["by_concept"].get(concept)
                if cs and cs.get("avg_value_score") is not None:
                    avg_value = cs["avg_value_score"]
                    break
        
        # 3. 整体平均
        if avg_value is None:
            avg_value = value_stats.get("overall_avg_value_score", 0.5)
        
        return round(my_value - avg_value, 4)
    
    # --------------------------------------------------------
    #  价值评分更新（反馈驱动）
    # --------------------------------------------------------
    
    def update_value(self, memory_id: str, feedback_score: float,
                      alpha: Optional[float] = None) -> float:
        """
        用 EMA 更新记忆的 value_score 字段，并写回节点文件。
        
        更新公式：
            new_value = alpha * old_value + (1 - alpha) * feedback_score
        
        Args:
            memory_id: 记忆节点 ID
            feedback_score: 反馈分数，范围 [0, 1]
            alpha: EMA 的历史权重，默认用 self.alpha
        
        Returns:
            float: 更新后的 value_score
        """
        if alpha is None:
            alpha = self.alpha
        
        feedback_score = max(0.0, min(1.0, feedback_score))
        
        # 加载节点
        node = _load_knowledge_node(memory_id)
        if node is None:
            return feedback_score
        
        old_value = node.get("value_score", 0.5)
        
        # EMA 更新
        new_value = alpha * old_value + (1 - alpha) * feedback_score
        new_value = round(max(0.0, min(1.0, new_value)), 4)
        
        # 写回文件
        node["value_score"] = new_value
        self._save_node(memory_id, node)
        
        # 刷新缓存
        self._invalidate_feedback_cache()
        
        return new_value
    
    def _save_node(self, node_id: str, node: Dict):
        """将更新后的节点写回文件（原子写入，避免文件损坏）。"""
        if not NODES_DIR.exists():
            return
        for fname in os.listdir(NODES_DIR):
            if fname.startswith(f"{node_id}_") and fname.endswith(".json"):
                fpath = NODES_DIR / fname
                # 先写临时文件，再重命名，避免写入中途中断导致文件损坏
                import tempfile
                tmp_fd, tmp_path = tempfile.mkstemp(
                    dir=str(NODES_DIR), suffix=".tmp", prefix=".tmp_kn_",
                )
                try:
                    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                        json.dump(node, f, ensure_ascii=False, indent=2)
                    os.replace(tmp_path, fpath)
                except Exception:
                    # 清理临时文件
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise
                return
    
    # --------------------------------------------------------
    #  批量计算
    # --------------------------------------------------------
    
    def estimate_all_values(self) -> Dict[str, float]:
        """
        批量计算所有知识节点的价值评分。
        
        Returns:
            dict: {node_id: value_score}
        """
        if not NODES_DIR.exists():
            return {}
        
        values = {}
        for fname in sorted(os.listdir(NODES_DIR)):
            if not (fname.startswith("kn_") and fname.endswith(".json")):
                continue
            node_id = fname.split("_")[0] + "_" + fname.split("_")[1].rstrip(".json")
            # 更稳健的方式：从文件名中提取 kn_NNN
            parts = fname.split("_")
            if len(parts) >= 2 and parts[0] == "kn":
                node_id = f"kn_{parts[1]}"
            
            node = _load_knowledge_node(node_id)
            if node:
                values[node_id] = self.estimate_value(node_id, node)
        
        return values


# ============================================================
#  方便的快捷函数
# ============================================================

def estimate_value(memory_id: str) -> float:
    """快捷函数：使用默认配置计算价值分。"""
    estimator = ValueEstimator()
    return estimator.estimate_value(memory_id)


def get_advantage(memory_id: str, category: Optional[str] = None) -> float:
    """快捷函数：计算价值优势。"""
    estimator = ValueEstimator()
    return estimator.get_advantage(memory_id, category)


def update_value(memory_id: str, feedback_score: float) -> float:
    """快捷函数：更新价值分。"""
    estimator = ValueEstimator()
    return estimator.update_value(memory_id, feedback_score)


# ---------- 独立运行 ----------
if __name__ == "__main__":
    print("=" * 60)
    print("ValueEstimator V1 测试")
    print("=" * 60)
    
    estimator = ValueEstimator()
    
    # 测试几个节点
    test_nodes = ["kn_001", "kn_005", "kn_020", "kn_039"]
    
    for nid in test_nodes:
        detail = estimator.estimate_value_detail(nid)
        print(f"\n【{nid}】")
        print(f"  综合价值分：{detail['total']:.4f}")
        for dim in ["frequency", "recency", "confidence", "source_reliability", "human_feedback"]:
            d = detail[dim]
            print(f"    {dim}: {d['score']:.4f} (权重 {d['weight']:.0%})")
        
        adv = estimator.get_advantage(nid)
        print(f"  价值优势：{adv:+.4f}")
    
    # 测试更新
    print("\n" + "=" * 60)
    print("价值评分更新测试（kn_001，模拟 5 星反馈）")
    print("=" * 60)
    
    old_val = _load_knowledge_node("kn_001").get("value_score", 0)
    print(f"更新前 value_score: {old_val}")
    
    # 注意：实际运行时会改文件，这里用一个临时节点模拟
    # 为了不影响生产数据，仅打印公式
    print(f"EMA 更新: new = 0.7 * {old_val} + 0.3 * 1.0 = {0.7 * old_val + 0.3:.4f}")
    print("（演示模式，未实际写入文件）")
