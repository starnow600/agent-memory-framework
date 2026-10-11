"""
PlugMem Phase 2 - MemoryQualityManager 记忆健康度管理器

记忆健康度评分 + 自动升降级机制：
  - 健康度评分：综合价值分、使用频率、时效性、反馈极性
  - L0热缓存升降级：高价值记忆自动进入L0，低价值自动降级
  - low_value 标记：长期低价值记忆在检索时降权
  - superseded 排除：被取代的记忆自动从检索结果中排除（保留文件供溯源）

开关：
  - ENABLE_QUALITY_MANAGER 环境变量控制总开关
  - ENABLE_AUTO_PROMOTE  控制自动升降级
  - ENABLE_LOW_VALUE_DOWNRANK 控制低价值降权
  - ENABLE_SUPERSEDED_EXCLUDE 控制取代排除

正向优势策略保持不变：冷启动保护、只升不降原则延续 Phase 1
"""

import json
import os
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
from copy import deepcopy

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).parent.parent
NODES_DIR = BASE_DIR / "knowledge_nodes"
INDEX_PATH = BASE_DIR / "knowledge_index.json"
FEEDBACK_LOG_PATH = BASE_DIR / "feedback_log.jsonl"
QUALITY_STATE_PATH = BASE_DIR / "quality_state.json"

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
        try:
            return datetime.strptime(ts, "%Y-%m-%d").replace(tzinfo=TZ)
        except (ValueError, TypeError):
            return datetime.now(TZ)


# ---------- 开关配置（环境变量） ----------
ENABLE_QUALITY_MANAGER = os.environ.get("ENABLE_QUALITY_MANAGER", "false").lower() in (
    "true", "1", "yes"
)
ENABLE_AUTO_PROMOTE = os.environ.get("ENABLE_AUTO_PROMOTE", "false").lower() in (
    "true", "1", "yes"
)
ENABLE_LOW_VALUE_DOWNRANK = os.environ.get("ENABLE_LOW_VALUE_DOWNRANK", "false").lower() in (
    "true", "1", "yes"
)
ENABLE_SUPERSEDED_EXCLUDE = os.environ.get("ENABLE_SUPERSEDED_EXCLUDE", "false").lower() in (
    "true", "1", "yes"
)

# ---------- 阈值配置 ----------
# L0热缓存准入条件
L0_PROMOTE_VALUE_THRESHOLD = 0.70      # 价值分 ≥ 此值
L0_PROMOTE_USE_COUNT_7D = 3            # 最近7天使用 ≥ 此次数
L0_PROMOTE_HEALTH_THRESHOLD = 0.65     # 健康度 ≥ 此值

# L0降级条件
L0_DEMOTE_VALUE_THRESHOLD = 0.50       # 价值分 < 此值（持续下降）
L0_DEMOTE_USE_COUNT_14D = 1            # 最近14天使用 ≤ 此次数

# low_value 标记条件
LOW_VALUE_THRESHOLD = 0.30             # 价值分 ≤ 此值
LOW_VALUE_USE_COUNT_30D = 1            # 最近30天使用 ≤ 此次数
LOW_VALUE_DOWNRANK_FACTOR = 0.5        # 低价值降权系数（置信度乘以此系数）

# superseded 检测
SUPERSEDED_SIMILARITY_THRESHOLD = 0.8  # 概念重叠度 ≥ 此值视为可能被取代

# 健康度权重
HEALTH_WEIGHTS = {
    "value_score": 0.35,       # 价值分
    "frequency_trend": 0.25,   # 使用频率趋势（上升/下降）
    "feedback_polarity": 0.25, # 反馈极性（正/负比例）
    "recency": 0.15,           # 时效性
}


# ============================================================
#  工具函数
# ============================================================

def _load_knowledge_node(node_id: str) -> Optional[Dict]:
    """根据 node_id 加载单个知识节点文件（复用 value_estimator 的缓存）。"""
    from .value_estimator import _load_knowledge_node as _ve_load
    return _ve_load(node_id)


def _load_all_node_ids() -> List[str]:
    """加载所有知识节点 ID 列表。"""
    if not NODES_DIR.exists():
        return []
    node_ids = []
    for fname in sorted(os.listdir(NODES_DIR)):
        if fname.startswith("kn_") and fname.endswith(".json"):
            parts = fname.split("_")
            if len(parts) >= 2 and parts[0] == "kn":
                node_ids.append(f"kn_{parts[1]}")
    return node_ids


def _load_feedback_log() -> List[Dict]:
    """加载反馈日志。"""
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


def _save_node(node_id: str, node: Dict):
    """将更新后的节点写回文件（原子写入）。"""
    from .value_estimator import ValueEstimator
    # 借用 ValueEstimator 的 _save_node 方法
    ve = ValueEstimator()
    ve._save_node(node_id, node)


# ============================================================
#  质量状态管理
# ============================================================

_quality_state_cache = None


def _load_quality_state() -> Dict:
    """加载质量状态（持久化升降级决策、健康度历史等）。"""
    global _quality_state_cache
    if _quality_state_cache is not None:
        return _quality_state_cache
    
    if QUALITY_STATE_PATH.exists():
        try:
            with open(QUALITY_STATE_PATH, "r", encoding="utf-8") as f:
                _quality_state_cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            _quality_state_cache = _default_quality_state()
    else:
        _quality_state_cache = _default_quality_state()
    
    return _quality_state_cache


def _default_quality_state() -> Dict:
    return {
        "version": "1.0",
        "updated_at": _now_iso(),
        "l0_cache": [],          # L0热缓存节点ID列表
        "low_value": [],         # low_value标记节点ID列表
        "superseded": [],        # superseded标记节点ID列表（被谁取代）
        "health_scores": {},     # {node_id: {score, computed_at, dimensions}}
        "promotion_log": [],     # 升降级日志
        "weekly_reports": [],    # 周度报告索引
    }


def _save_quality_state(state: Dict):
    """保存质量状态到文件。"""
    global _quality_state_cache
    state["updated_at"] = _now_iso()
    _quality_state_cache = state
    
    # 原子写入
    import tempfile
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=str(BASE_DIR), suffix=".tmp", prefix=".tmp_quality_",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, QUALITY_STATE_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ============================================================
#  使用频率与反馈分析
# ============================================================

def _get_usage_stats(feedback_entries: List[Dict], node_id: str,
                      days: int = 30) -> Dict:
    """
    统计指定节点在最近 N 天内的使用情况。
    
    Returns:
        dict: {
            "use_count": int,
            "positive_count": int,
            "negative_count": int,
            "last_use_time": datetime|None,
            "first_use_time": datetime|None,
            "weekly_counts": [int, ...],  # 最近4周每周使用次数
        }
    """
    now = datetime.now(TZ)
    cutoff = now - timedelta(days=days)
    
    use_count = 0
    positive_count = 0
    negative_count = 0
    last_use = None
    first_use = None
    
    # 按周统计（最近4周）
    weekly_counts = [0, 0, 0, 0]
    
    for entry in feedback_entries:
        if entry.get("memory_id") != node_id:
            continue
        
        ts = _parse_iso(entry.get("timestamp", ""))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=TZ)
        
        if ts < cutoff:
            continue
        
        use_count += 1
        
        if last_use is None or ts > last_use:
            last_use = ts
        if first_use is None or ts < first_use:
            first_use = ts
        
        # 判断正/负反馈
        source = entry.get("source", "")
        if source == "explicit":
            rating = entry.get("rating", 3)
            if rating >= 4:
                positive_count += 1
            elif rating <= 2:
                negative_count += 1
        elif source == "implicit":
            action = entry.get("action", "")
            if action == "referenced":
                positive_count += 1
            elif action == "not_used":
                negative_count += 1
            elif action == "reverse_feedback":
                negative_count += 1
        
        # 周统计
        days_ago = (now - ts).days
        week_idx = min(days_ago // 7, 3)
        if 0 <= week_idx < 4:
            weekly_counts[week_idx] += 1
    
    return {
        "use_count": use_count,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "last_use_time": last_use,
        "first_use_time": first_use,
        "weekly_counts": weekly_counts,
    }


def _compute_frequency_trend(weekly_counts: List[int]) -> float:
    """
    计算使用频率趋势（0-1）。
    - 上升趋势 → 高分
    - 下降趋势 → 低分
    - 平稳 → 0.5 左右
    
    简单线性回归斜率归一化。
    """
    if not weekly_counts or all(c == 0 for c in weekly_counts):
        return 0.3  # 无数据，中等偏下
    
    n = len(weekly_counts)
    if n < 2:
        return 0.5
    
    # 简单斜率：(最后一周 - 第一周) / (n-1)
    # 归一化到 0-1 范围
    max_count = max(weekly_counts) if max(weekly_counts) > 0 else 1
    slope = (weekly_counts[-1] - weekly_counts[0]) / max_count
    # 映射：-1~+1 → 0~1
    trend_score = 0.5 + slope * 0.5
    return max(0.0, min(1.0, trend_score))


def _compute_feedback_polarity(positive: int, negative: int) -> float:
    """
    计算反馈极性评分（0-1）。
    - 全正反馈 → 1.0
    - 全负反馈 → 0.0
    - 无反馈 → 0.5（中性）
    """
    total = positive + negative
    if total == 0:
        return 0.5  # 无反馈，中性
    
    # 正反馈比例，带轻微的先验（倾向中性）
    # 使用拉普拉斯平滑：(pos + 1) / (total + 2)
    smoothed_pos_ratio = (positive + 1) / (total + 2)
    return smoothed_pos_ratio


# ============================================================
#  MemoryQualityManager 类
# ============================================================

class MemoryQualityManager:
    """
    记忆健康度管理器。
    
    功能：
    1. compute_health_score(node_id): 计算单个记忆的健康度评分
    2. check_promotion_criteria(node_id): 检查是否符合升降级条件
    3. run_auto_promotion(): 批量执行自动升降级（写入状态文件）
    4. filter_superseded(results): 从检索结果中排除 superseded 记忆
    5. apply_low_value_downrank(results): 对 low_value 记忆进行降权
    6. generate_health_report(): 生成记忆健康度报告
    
    用法：
        mgr = MemoryQualityManager()
        health = mgr.compute_health_score("kn_001")
        mgr.run_auto_promotion()
        filtered = mgr.filter_superseded(results)
    """
    
    def __init__(
        self,
        health_weights: Optional[Dict[str, float]] = None,
        enable_auto_promote: Optional[bool] = None,
        enable_low_value_downrank: Optional[bool] = None,
        enable_superseded_exclude: Optional[bool] = None,
    ):
        """
        初始化记忆健康度管理器。
        
        Args:
            health_weights: 健康度各维度权重
            enable_auto_promote: 是否启用自动升降级（None则用环境变量）
            enable_low_value_downrank: 是否启用低价值降权
            enable_superseded_exclude: 是否启用取代排除
        """
        self.health_weights = health_weights or HEALTH_WEIGHTS
        self.enable_auto_promote = (
            enable_auto_promote if enable_auto_promote is not None
            else ENABLE_AUTO_PROMOTE
        )
        self.enable_low_value_downrank = (
            enable_low_value_downrank if enable_low_value_downrank is not None
            else ENABLE_LOW_VALUE_DOWNRANK
        )
        self.enable_superseded_exclude = (
            enable_superseded_exclude if enable_superseded_exclude is not None
            else ENABLE_SUPERSEDED_EXCLUDE
        )
        
        # 懒加载
        self._feedback_cache = None
        self._value_estimator = None
        self._state_cache = None
    
    def _get_feedback(self) -> List[Dict]:
        if self._feedback_cache is None:
            self._feedback_cache = _load_feedback_log()
        return self._feedback_cache
    
    def _get_value_estimator(self):
        if self._value_estimator is None:
            from .value_estimator import ValueEstimator
            self._value_estimator = ValueEstimator()
        return self._value_estimator
    
    def _get_state(self) -> Dict:
        if self._state_cache is None:
            self._state_cache = _load_quality_state()
        return self._state_cache
    
    def _save_state(self, state: Dict):
        _save_quality_state(state)
        self._state_cache = state
    
    # --------------------------------------------------------
    #  健康度评分
    # --------------------------------------------------------
    
    def compute_health_score(self, node_id: str, node: Optional[Dict] = None) -> Dict:
        """
        计算记忆的健康度评分。
        
        4 个维度：
        - value_score (35%): 当前价值评分
        - frequency_trend (25%): 使用频率趋势（上升/下降）
        - feedback_polarity (25%): 反馈极性（正反馈比例）
        - recency (15%): 最近使用时间
        
        Args:
            node_id: 节点ID
            node: 可选，已加载的节点字典
        
        Returns:
            dict: {
                "total": float,           # 综合健康度 0-1
                "value_score": float,     # 价值分维度
                "frequency_trend": float, # 频率趋势维度
                "feedback_polarity": float, # 反馈极性维度
                "recency": float,         # 时效性维度
                "computed_at": str,       # 计算时间
            }
        """
        if node is None:
            node = _load_knowledge_node(node_id)
            if node is None:
                return {"total": 0.0, "computed_at": _now_iso()}
        
        feedback_entries = self._get_feedback()
        usage = _get_usage_stats(feedback_entries, node_id, days=30)
        
        # 1. 价值分维度（直接使用节点的 value_score，或调用评估器）
        ve = self._get_value_estimator()
        value_score = node.get("value_score", ve.estimate_value(node_id, node))
        value_score = max(0.0, min(1.0, value_score))
        
        # 2. 频率趋势
        freq_trend = _compute_frequency_trend(usage["weekly_counts"])
        
        # 3. 反馈极性
        polarity = _compute_feedback_polarity(
            usage["positive_count"], usage["negative_count"]
        )
        
        # 4. 时效性
        from .value_estimator import _compute_recency_score
        recency = _compute_recency_score(usage["last_use_time"])
        
        # 加权求和
        w = self.health_weights
        total = (
            w["value_score"] * value_score
            + w["frequency_trend"] * freq_trend
            + w["feedback_polarity"] * polarity
            + w["recency"] * recency
        )
        
        total = round(max(0.0, min(1.0, total)), 4)
        
        result = {
            "total": total,
            "value_score": round(value_score, 4),
            "frequency_trend": round(freq_trend, 4),
            "feedback_polarity": round(polarity, 4),
            "recency": round(recency, 4),
            "computed_at": _now_iso(),
        }
        
        # 缓存到状态
        state = self._get_state()
        state.setdefault("health_scores", {})[node_id] = result
        
        return result
    
    def get_health_score(self, node_id: str) -> float:
        """获取缓存的健康度总分（快速查询）。"""
        state = self._get_state()
        health = state.get("health_scores", {}).get(node_id)
        if health:
            return health.get("total", 0.5)
        # 未计算过则计算一次
        result = self.compute_health_score(node_id)
        return result["total"]
    
    # --------------------------------------------------------
    #  自动升降级
    # --------------------------------------------------------
    
    def check_promotion_criteria(self, node_id: str, node: Optional[Dict] = None) -> Dict:
        """
        检查节点是否符合升降级条件。
        
        Returns:
            dict: {
                "should_promote_l0": bool,    # 是否应该晋升到L0
                "should_demote_l0": bool,     # 是否应该从L0降级
                "should_mark_low_value": bool,# 是否应该标记为low_value
                "should_unmark_low_value": bool, # 是否应该取消low_value标记
                "value_score": float,
                "use_count_7d": int,
                "use_count_30d": int,
                "health_score": float,
                "reasons": List[str],         # 触发条件的原因
            }
        """
        if node is None:
            node = _load_knowledge_node(node_id)
            if node is None:
                return {"should_promote_l0": False, "should_demote_l0": False,
                        "should_mark_low_value": False, "should_unmark_low_value": False,
                        "reasons": ["节点不存在"]}
        
        feedback = self._get_feedback()
        usage_7d = _get_usage_stats(feedback, node_id, days=7)
        usage_30d = _get_usage_stats(feedback, node_id, days=30)
        
        ve = self._get_value_estimator()
        value_score = node.get("value_score", ve.estimate_value(node_id, node))
        health = self.compute_health_score(node_id, node)
        health_score = health["total"]
        
        state = self._get_state()
        in_l0 = node_id in state.get("l0_cache", [])
        is_low_value = node_id in state.get("low_value", [])
        
        reasons = []
        should_promote = False
        should_demote = False
        should_mark_low = False
        should_unmark_low = False
        
        # ---- L0 晋升条件 ----
        if not in_l0:
            promote_ok = True
            if value_score < L0_PROMOTE_VALUE_THRESHOLD:
                promote_ok = False
                reasons.append(f"价值分{value_score:.3f} < {L0_PROMOTE_VALUE_THRESHOLD}")
            if usage_7d["use_count"] < L0_PROMOTE_USE_COUNT_7D:
                promote_ok = False
                reasons.append(f"7天使用{usage_7d['use_count']}次 < {L0_PROMOTE_USE_COUNT_7D}")
            if health_score < L0_PROMOTE_HEALTH_THRESHOLD:
                promote_ok = False
                reasons.append(f"健康度{health_score:.3f} < {L0_PROMOTE_HEALTH_THRESHOLD}")
            
            if promote_ok:
                should_promote = True
                reasons.append("满足L0晋升条件")
        
        # ---- L0 降级条件 ----
        if in_l0:
            demote_reasons = []
            if value_score < L0_DEMOTE_VALUE_THRESHOLD:
                demote_reasons.append(f"价值分{value_score:.3f} < {L0_DEMOTE_VALUE_THRESHOLD}")
            
            usage_14d = _get_usage_stats(feedback, node_id, days=14)
            if usage_14d["use_count"] <= L0_DEMOTE_USE_COUNT_14D:
                demote_reasons.append(
                    f"14天使用{usage_14d['use_count']}次 ≤ {L0_DEMOTE_USE_COUNT_14D}"
                )
            
            if demote_reasons:
                should_demote = True
                reasons.extend(demote_reasons)
        
        # ---- low_value 标记条件 ----
        if not is_low_value:
            low_ok = True
            if value_score > LOW_VALUE_THRESHOLD:
                low_ok = False
                reasons.append(f"价值分{value_score:.3f} > {LOW_VALUE_THRESHOLD}（不触发low_value）")
            if usage_30d["use_count"] > LOW_VALUE_USE_COUNT_30D:
                low_ok = False
                reasons.append(f"30天使用{usage_30d['use_count']}次 > {LOW_VALUE_USE_COUNT_30D}（不触发low_value）")
            
            if low_ok and value_score <= LOW_VALUE_THRESHOLD:
                should_mark_low = True
                reasons.append("满足low_value标记条件")
        
        # ---- 取消 low_value 标记 ----
        if is_low_value:
            if value_score > LOW_VALUE_THRESHOLD + 0.1:  # 回升超过阈值+缓冲
                should_unmark_low = True
                reasons.append("价值分回升，取消low_value标记")
        
        return {
            "should_promote_l0": should_promote,
            "should_demote_l0": should_demote,
            "should_mark_low_value": should_mark_low,
            "should_unmark_low_value": should_unmark_low,
            "value_score": round(value_score, 4),
            "use_count_7d": usage_7d["use_count"],
            "use_count_30d": usage_30d["use_count"],
            "health_score": round(health_score, 4),
            "in_l0": in_l0,
            "is_low_value": is_low_value,
            "reasons": reasons,
        }
    
    def run_auto_promotion(self) -> Dict:
        """
        批量执行自动升降级检查，更新质量状态文件。
        
        Returns:
            dict: {
                "promoted": [node_id, ...],    # 新晋升到L0
                "demoted": [node_id, ...],     # 从L0降级
                "marked_low_value": [...],     # 新标记low_value
                "unmarked_low_value": [...],   # 取消low_value标记
                "total_checked": int,
            }
        """
        if not self.enable_auto_promote:
            return {
                "promoted": [], "demoted": [],
                "marked_low_value": [], "unmarked_low_value": [],
                "total_checked": 0,
                "skipped": "auto_promote disabled",
            }
        
        node_ids = _load_all_node_ids()
        state = deepcopy(self._get_state())
        
        promoted = []
        demoted = []
        marked_low = []
        unmarked_low = []
        
        for nid in node_ids:
            node = _load_knowledge_node(nid)
            if not node:
                continue
            
            criteria = self.check_promotion_criteria(nid, node)
            
            if criteria["should_promote_l0"]:
                if nid not in state["l0_cache"]:
                    state["l0_cache"].append(nid)
                    promoted.append(nid)
                    state.setdefault("promotion_log", []).append({
                        "timestamp": _now_iso(),
                        "node_id": nid,
                        "action": "promote_l0",
                        "value_score": criteria["value_score"],
                        "health_score": criteria["health_score"],
                        "reasons": criteria["reasons"],
                    })
            
            if criteria["should_demote_l0"]:
                if nid in state["l0_cache"]:
                    state["l0_cache"].remove(nid)
                    demoted.append(nid)
                    state.setdefault("promotion_log", []).append({
                        "timestamp": _now_iso(),
                        "node_id": nid,
                        "action": "demote_l0",
                        "value_score": criteria["value_score"],
                        "health_score": criteria["health_score"],
                        "reasons": criteria["reasons"],
                    })
            
            if criteria["should_mark_low_value"]:
                if nid not in state["low_value"]:
                    state["low_value"].append(nid)
                    marked_low.append(nid)
                    # 同步到节点文件
                    node["quality_status"] = "low_value"
                    _save_node(nid, node)
                    state.setdefault("promotion_log", []).append({
                        "timestamp": _now_iso(),
                        "node_id": nid,
                        "action": "mark_low_value",
                        "value_score": criteria["value_score"],
                        "reasons": criteria["reasons"],
                    })
            
            if criteria["should_unmark_low_value"]:
                if nid in state["low_value"]:
                    state["low_value"].remove(nid)
                    unmarked_low.append(nid)
                    # 同步到节点文件
                    if node.get("quality_status") == "low_value":
                        node.pop("quality_status", None)
                        _save_node(nid, node)
                    state.setdefault("promotion_log", []).append({
                        "timestamp": _now_iso(),
                        "node_id": nid,
                        "action": "unmark_low_value",
                        "value_score": criteria["value_score"],
                        "reasons": criteria["reasons"],
                    })
        
        self._save_state(state)
        
        return {
            "promoted": promoted,
            "demoted": demoted,
            "marked_low_value": marked_low,
            "unmarked_low_value": unmarked_low,
            "total_checked": len(node_ids),
        }
    
    # --------------------------------------------------------
    #  superseded 管理
    # --------------------------------------------------------
    
    def detect_superseded(self) -> List[Dict]:
        """
        检测被取代的记忆对。
        
        判定规则：
        - 两个记忆共享 ≥ 80% 的概念
        - 其中一个创建时间更早、价值分更低
        - 高价值的那个可能取代了低价值的那个
        
        Returns:
            list: [{"old": node_id, "new": node_id, "similarity": float}, ...]
        """
        node_ids = _load_all_node_ids()
        nodes = {}
        for nid in node_ids:
            node = _load_knowledge_node(nid)
            if node:
                nodes[nid] = node
        
        superseded_pairs = []
        
        # 两两比较（O(n²)，44个节点完全可接受）
        nids = list(nodes.keys())
        for i in range(len(nids)):
            for j in range(i + 1, len(nids)):
                n1, n2 = nids[i], nids[j]
                concepts1 = set(nodes[n1].get("concepts", []))
                concepts2 = set(nodes[n2].get("concepts", []))
                
                if not concepts1 or not concepts2:
                    continue
                
                # Jaccard 相似度
                intersection = concepts1 & concepts2
                union = concepts1 | concepts2
                similarity = len(intersection) / len(union) if union else 0
                
                if similarity >= SUPERSEDED_SIMILARITY_THRESHOLD:
                    # 比较价值分，低的可能被高的取代
                    v1 = nodes[n1].get("value_score", 0.5)
                    v2 = nodes[n2].get("value_score", 0.5)
                    
                    if v1 >= v2:
                        old_node, new_node = n2, n1
                    else:
                        old_node, new_node = n1, n2
                    
                    superseded_pairs.append({
                        "old": old_node,
                        "new": new_node,
                        "similarity": round(similarity, 4),
                    })
        
        return superseded_pairs
    
    def mark_superseded(self, old_node_id: str, new_node_id: str) -> bool:
        """
        标记一个记忆为已被取代。
        
        Args:
            old_node_id: 被取代的旧节点ID
            new_node_id: 取代它的新节点ID
        
        Returns:
            bool: 是否成功标记
        """
        state = deepcopy(self._get_state())
        
        # 检查是否已标记
        for entry in state.get("superseded", []):
            if entry.get("old") == old_node_id:
                return False  # 已标记
        
        state.setdefault("superseded", []).append({
            "old": old_node_id,
            "new": new_node_id,
            "marked_at": _now_iso(),
        })
        
        # 同步到节点文件
        node = _load_knowledge_node(old_node_id)
        if node:
            node["superseded_by"] = new_node_id
            node["quality_status"] = "superseded"
            _save_node(old_node_id, node)
        
        self._save_state(state)
        return True
    
    # --------------------------------------------------------
    #  检索结果处理
    # --------------------------------------------------------
    
    def filter_superseded(self, results: List[Dict]) -> List[Dict]:
        """
        从检索结果中排除 superseded 标记的记忆（保留文件供溯源）。
        
        Args:
            results: 检索结果列表
        
        Returns:
            过滤后的结果列表
        """
        if not self.enable_superseded_exclude:
            return results
        
        state = self._get_state()
        superseded_ids = {
            entry["old"] for entry in state.get("superseded", [])
        }
        
        if not superseded_ids:
            return results
        
        filtered = [
            r for r in results
            if r.get("node_id") not in superseded_ids
        ]
        
        return filtered
    
    def apply_low_value_downrank(self, results: List[Dict],
                                  factor: float = None) -> List[Dict]:
        """
        对标记为 low_value 的记忆进行降权（降低置信度）。
        
        正向优势策略兼容：只降低low_value的置信度，
        不改变高价值记忆的排序，也不直接排除。
        
        Args:
            results: 检索结果列表
            factor: 降权系数，默认 LOW_VALUE_DOWNRANK_FACTOR
        
        Returns:
            降权后的结果列表（需重新排序）
        """
        if not self.enable_low_value_downrank:
            return results
        
        if factor is None:
            factor = LOW_VALUE_DOWNRANK_FACTOR
        
        state = self._get_state()
        low_value_ids = set(state.get("low_value", []))
        
        if not low_value_ids:
            return results
        
        adjusted = []
        for r in results:
            if r.get("node_id") in low_value_ids:
                new_r = dict(r)
                original_conf = r.get("confidence", 0.5)
                new_r["confidence"] = round(original_conf * factor, 4)
                new_r["low_value_downranked"] = True
                new_r["original_confidence"] = original_conf
                adjusted.append(new_r)
            else:
                adjusted.append(r)
        
        # 降权后需要重新排序
        adjusted.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return adjusted
    
    def apply_quality_filters(self, results: List[Dict]) -> List[Dict]:
        """
        应用所有质量过滤器（按顺序：排除superseded → low_value降权）。
        
        Args:
            results: 检索结果列表
        
        Returns:
            过滤和降权后的结果列表
        """
        # 1. 排除 superseded
        results = self.filter_superseded(results)
        
        # 2. low_value 降权
        results = self.apply_low_value_downrank(results)
        
        return results
    
    # --------------------------------------------------------
    #  L0 热缓存管理
    # --------------------------------------------------------
    
    def get_l0_cache(self) -> List[str]:
        """获取当前L0热缓存中的节点ID列表。"""
        state = self._get_state()
        return list(state.get("l0_cache", []))
    
    def is_in_l0(self, node_id: str) -> bool:
        """检查节点是否在L0热缓存中。"""
        return node_id in self.get_l0_cache()
    
    def boost_l0_results(self, results: List[Dict],
                          boost_factor: float = None) -> List[Dict]:
        """
        对L0热缓存中的记忆给予轻微的排序提升（正向优势策略一致）。
        
        正向优势策略：
        - L0中的记忆在检索时获得轻微加分，但**不跨越置信度梯队**
        - 具体规则：
          1. 只对L0记忆加分，非L0不变
          2. 提升不超过前一名置信度的98%（不越级）
          3. 绝对提升上限由 boost_factor 控制（默认+8%）
          4. 保证高置信度记忆始终排在低置信度前面
        
        这样L0记忆可以在"同梯队"内优先展示，不会把低质量的顶到高质量前面。
        
        Args:
            results: 检索结果列表
            boost_factor: L0提升系数上限（默认1.08，即+8%）
        
        Returns:
            调整后的结果列表
        """
        l0_ids = set(self.get_l0_cache())
        if not l0_ids or not results:
            return results
        
        if boost_factor is None:
            boost_factor = 1.08
        
        # 先复制，不修改原数据
        adjusted = [dict(r) for r in results]
        
        for i, item in enumerate(adjusted):
            if item.get("node_id") not in l0_ids:
                continue
            
            original_conf = item.get("confidence", 0.5)
            
            # 计算最大允许提升：不超过前一名的98%（不越级）
            max_allowed_conf = 1.0
            if i > 0:
                prev_conf = adjusted[i-1].get("confidence", 1.0)
                max_allowed_conf = prev_conf * 0.98
            
            # 绝对提升上限
            absolute_boost_limit = original_conf * boost_factor
            new_conf = min(absolute_boost_limit, max_allowed_conf, 1.0)
            
            if new_conf > original_conf + 0.001:
                item["confidence"] = round(new_conf, 4)
                item["l0_boosted"] = True
                item["original_confidence"] = original_conf
        
        # 重新排序
        adjusted.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return adjusted
    
    # --------------------------------------------------------
    #  健康度报告
    # --------------------------------------------------------
    
    def generate_health_report(self) -> Dict:
        """
        生成记忆健康度报告。
        
        Returns:
            dict: {
                "total_nodes": int,
                "avg_health_score": float,
                "health_distribution": {"excellent": int, "good": int, "fair": int, "poor": int},
                "l0_count": int,
                "low_value_count": int,
                "superseded_count": int,
                "top_health": [{"node_id", "health_score", "value_score"}, ...],
                "bottom_health": [...],
                "recent_promotions": [...],
                "generated_at": str,
            }
        """
        node_ids = _load_all_node_ids()
        health_scores = {}
        
        # 计算所有节点的健康度
        for nid in node_ids:
            node = _load_knowledge_node(nid)
            if node:
                h = self.compute_health_score(nid, node)
                health_scores[nid] = h
        
        # 分布统计
        excellent = sum(1 for h in health_scores.values() if h["total"] >= 0.8)
        good = sum(1 for h in health_scores.values() if 0.6 <= h["total"] < 0.8)
        fair = sum(1 for h in health_scores.values() if 0.4 <= h["total"] < 0.6)
        poor = sum(1 for h in health_scores.values() if h["total"] < 0.4)
        
        avg_health = (
            sum(h["total"] for h in health_scores.values()) / len(health_scores)
            if health_scores else 0.0
        )
        
        # Top/Bottom
        sorted_health = sorted(
            health_scores.items(), key=lambda x: x[1]["total"], reverse=True
        )
        top_10 = [
            {"node_id": nid, "health_score": h["total"], "value_score": h["value_score"]}
            for nid, h in sorted_health[:10]
        ]
        bottom_10 = [
            {"node_id": nid, "health_score": h["total"], "value_score": h["value_score"]}
            for nid, h in sorted_health[-10:]
        ]
        
        state = self._get_state()
        
        # 最近的升降级记录（最近20条）
        recent = state.get("promotion_log", [])[-20:]
        
        report = {
            "generated_at": _now_iso(),
            "total_nodes": len(node_ids),
            "avg_health_score": round(avg_health, 4),
            "health_distribution": {
                "excellent (≥0.8)": excellent,
                "good (0.6-0.8)": good,
                "fair (0.4-0.6)": fair,
                "poor (<0.4)": poor,
            },
            "l0_count": len(state.get("l0_cache", [])),
            "low_value_count": len(state.get("low_value", [])),
            "superseded_count": len(state.get("superseded", [])),
            "top_health": top_10,
            "bottom_health": bottom_10,
            "recent_promotions": recent,
            "coverage_rate": round(len(health_scores) / max(len(node_ids), 1), 4),
        }
        
        # 保存到状态
        state.setdefault("weekly_reports", []).append({
            "generated_at": report["generated_at"],
            "avg_health_score": report["avg_health_score"],
            "total_nodes": report["total_nodes"],
            "l0_count": report["l0_count"],
        })
        self._save_state(state)
        
        return report


# ============================================================
#  模块级快捷函数
# ============================================================

_quality_manager_instance: Optional[MemoryQualityManager] = None


def _get_quality_manager() -> MemoryQualityManager:
    """获取单例质量管理器。"""
    global _quality_manager_instance
    if _quality_manager_instance is None:
        _quality_manager_instance = MemoryQualityManager()
    return _quality_manager_instance


def compute_health_score(node_id: str) -> Dict:
    """快捷函数：计算健康度评分。"""
    return _get_quality_manager().compute_health_score(node_id)


def apply_quality_filters(results: List[Dict]) -> List[Dict]:
    """快捷函数：应用所有质量过滤器。"""
    return _get_quality_manager().apply_quality_filters(results)


def run_auto_promotion() -> Dict:
    """快捷函数：执行自动升降级。"""
    return _get_quality_manager().run_auto_promotion()


# ---------- 独立运行 ----------
if __name__ == "__main__":
    print("=" * 60)
    print("MemoryQualityManager 测试")
    print("=" * 60)
    
    mgr = MemoryQualityManager(
        enable_auto_promote=True,
        enable_low_value_downrank=True,
        enable_superseded_exclude=True,
    )
    
    # 测试几个节点的健康度
    test_nodes = ["kn_001", "kn_005", "kn_020", "kn_039", "kn_040"]
    
    print("\n【健康度评分】")
    for nid in test_nodes:
        h = mgr.compute_health_score(nid)
        print(f"  {nid}: 健康度={h['total']:.4f} "
              f"(价值={h['value_score']:.3f}, "
              f"趋势={h['frequency_trend']:.3f}, "
              f"极性={h['feedback_polarity']:.3f}, "
              f"时效={h['recency']:.3f})")
    
    print("\n【自动升降级检查】")
    for nid in test_nodes:
        c = mgr.check_promotion_criteria(nid)
        status_parts = []
        if c["should_promote_l0"]:
            status_parts.append("→晋升L0")
        if c["should_demote_l0"]:
            status_parts.append("→L0降级")
        if c["should_mark_low_value"]:
            status_parts.append("→标记low_value")
        status = ", ".join(status_parts) if status_parts else "无变化"
        print(f"  {nid}: {status} (价值={c['value_score']:.3f}, "
              f"7天使用={c['use_count_7d']}次, 健康度={c['health_score']:.3f})")
    
    print("\n【生成健康度报告】")
    report = mgr.generate_health_report()
    print(f"  总节点数: {report['total_nodes']}")
    print(f"  平均健康度: {report['avg_health_score']:.4f}")
    print(f"  健康度分布: {report['health_distribution']}")
    print(f"  L0缓存: {report['l0_count']} 个")
    print(f"  Low Value: {report['low_value_count']} 个")
    print(f"  覆盖率: {report['coverage_rate']:.1%}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
