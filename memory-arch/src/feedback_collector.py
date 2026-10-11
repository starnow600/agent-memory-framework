"""
PlugMem Phase 1 - FeedbackCollector 反馈收集模块

提供显式反馈和隐式反馈接口，写入 feedback_log.jsonl（append-only），
并在反馈后自动触发 ValueEstimator 的 value_score 更新。

接口：
  - record_feedback(memory_id, query, rating, source="explicit")
    显式反馈：用户直接对记忆质量打分（1-5星）

  - record_implicit_feedback(memory_id, query, action)
    隐式反馈：从行为推断
    - action="referenced": 记忆被引用到对话中 → 正反馈
    - action="not_used": 检索到但未被使用 → 负向信号（不扣分，仅统计）

反馈后自动调用 ValueEstimator.update_value() 更新节点的 value_score。
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from .value_estimator import ValueEstimator

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).parent.parent
FEEDBACK_LOG_PATH = BASE_DIR / "feedback_log.jsonl"

# 时区：东八区
TZ = timezone(timedelta(hours=8))


def _now_iso() -> str:
    """获取当前时间的 ISO 格式字符串（东八区）"""
    return datetime.now(TZ).isoformat()


def _ensure_log_file():
    """确保反馈日志文件存在，不存在则创建并写入表头。"""
    if not FEEDBACK_LOG_PATH.exists():
        with open(FEEDBACK_LOG_PATH, "w", encoding="utf-8") as f:
            f.write("# feedback_log.jsonl - 反馈日志（append-only）\n")
            f.write("# 格式：{timestamp, memory_id, query, source, rating, action, extra}\n")
            f.write("# source: explicit(显式) / implicit(隐式)\n")
            f.write("# action(referenced/not_used) 仅 implicit 有效\n")
            f.write("\n")


# ============================================================
#  FeedbackCollector 类
# ============================================================

class FeedbackCollector:
    """
    反馈收集器。
    
    负责：
    1. 记录显式/隐式反馈到 feedback_log.jsonl
    2. 反馈后自动更新记忆的 value_score
    
    用法：
        collector = FeedbackCollector()
        collector.record_feedback("kn_001", "这个记忆很有用", rating=5)
        collector.record_implicit_feedback("kn_001", "某查询", action="referenced")
    """
    
    def __init__(self, estimator: Optional[ValueEstimator] = None,
                 auto_update: bool = True):
        """
        初始化反馈收集器。
        
        Args:
            estimator: ValueEstimator 实例，为 None 时自动创建
            auto_update: 是否在记录反馈后自动更新 value_score，默认 True
        """
        self.estimator = estimator or ValueEstimator()
        self.auto_update = auto_update
        _ensure_log_file()
    
    # --------------------------------------------------------
    #  显式反馈
    # --------------------------------------------------------
    
    def record_feedback(
        self,
        memory_id: str,
        query: str,
        rating: int,
        source: str = "explicit",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        记录显式反馈。
        
        Args:
            memory_id: 记忆节点 ID（如 "kn_001"）
            query: 触发反馈的查询文本
            rating: 评分，1-5 星（整数）
            source: 反馈来源，默认 "explicit"
            extra: 额外信息，可选
        
        Returns:
            dict: 写入的反馈条目
        """
        # 校验 rating
        rating = max(1, min(5, int(rating)))
        
        entry = {
            "timestamp": _now_iso(),
            "memory_id": memory_id,
            "query": query,
            "source": source,
            "rating": rating,
            "extra": extra or {},
        }
        
        self._append_entry(entry)
        
        # 自动更新价值评分
        if self.auto_update:
            # rating 1-5 → 归一化到 0-1
            feedback_score = (rating - 1) / 4.0
            self.estimator.update_value(memory_id, feedback_score)
        
        return entry
    
    # --------------------------------------------------------
    #  隐式反馈
    # --------------------------------------------------------
    
    def record_implicit_feedback(
        self,
        memory_id: str,
        query: str,
        action: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        记录隐式反馈。
        
        Args:
            memory_id: 记忆节点 ID
            query: 查询文本
            action: 行为类型
                - "referenced": 记忆被引用（正反馈）
                - "not_used": 检索到但未使用（弱负信号，仅统计不扣分）
            extra: 额外信息，可选
        
        Returns:
            dict: 写入的反馈条目
        """
        valid_actions = {"referenced", "not_used"}
        if action not in valid_actions:
            raise ValueError(f"action 必须是 {valid_actions} 之一，收到: {action}")
        
        entry = {
            "timestamp": _now_iso(),
            "memory_id": memory_id,
            "query": query,
            "source": "implicit",
            "action": action,
            "extra": extra or {},
        }
        
        self._append_entry(entry)
        
        # 自动更新价值评分（只有正反馈才更新）
        if self.auto_update and action == "referenced":
            # 隐式正反馈给 0.6 分（中等正向，弱于显式5星）
            self.estimator.update_value(memory_id, 0.6)
        
        return entry
    
    # --------------------------------------------------------
    #  批量反馈（用于评测/模拟）
    # --------------------------------------------------------
    
    def record_batch_feedback(
        self,
        feedback_list: List[Dict[str, Any]],
    ) -> int:
        """
        批量记录反馈（用于评测脚本注入模拟反馈数据）。
        
        性能优化：批量写入日志 + 批量更新 value_score，避免每条都读写文件。
        
        Args:
            feedback_list: 反馈条目列表，每条格式：
                {
                    "memory_id": str,
                    "query": str,
                    "rating": int,    # 显式反馈用
                    "action": str,    # 隐式反馈用
                    "source": "explicit" / "implicit",
                    "timestamp": str,  # 可选，不填用当前时间
                }
        
        Returns:
            int: 成功写入的条数
        """
        if not feedback_list:
            return 0
        
        # 1. 批量写入日志（一次性 append 所有条目）
        _ensure_log_file()
        now_str = _now_iso()
        with open(FEEDBACK_LOG_PATH, "a", encoding="utf-8") as f:
            for fb in feedback_list:
                source = fb.get("source", "explicit")
                entry = {
                    "timestamp": fb.get("timestamp", now_str),
                    "memory_id": fb["memory_id"],
                    "query": fb.get("query", ""),
                    "source": source,
                    "extra": fb.get("extra") or {},
                }
                if source == "explicit":
                    entry["rating"] = max(1, min(5, int(fb.get("rating", 3))))
                else:
                    entry["action"] = fb.get("action", "referenced")
                
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        # 2. 如果启用自动更新，批量更新 value_score
        if self.auto_update:
            self._batch_update_values(feedback_list)
        
        return len(feedback_list)
    
    def _batch_update_values(self, feedback_list: List[Dict[str, Any]]):
        """
        批量更新多个节点的 value_score。
        
        优化：对每个节点只读取一次文件、计算一次 EMA、写回一次，
        而不是每条反馈都读写一次。
        
        EMA 多步更新等价于：
            new = alpha^n * old + (1-alpha) * Σ(alpha^(n-i-1) * fb_i)
        
        但为了简单且与逐条更新结果一致，这里先统计每个节点的反馈列表，
        再逐条应用 EMA（内存操作，只有最后一次写文件）。
        """
        from .value_estimator import _load_knowledge_node
        
        # 按节点分组
        node_feedbacks: Dict[str, List[float]] = {}
        for fb in feedback_list:
            mid = fb["memory_id"]
            source = fb.get("source", "explicit")
            
            if source == "explicit":
                rating = max(1, min(5, int(fb.get("rating", 3))))
                score = (rating - 1) / 4.0
            else:  # implicit
                action = fb.get("action", "referenced")
                if action != "referenced":
                    continue  # 只有 referenced 才触发正反馈更新
                score = 0.6
            
            node_feedbacks.setdefault(mid, []).append(score)
        
        alpha = self.estimator.alpha
        
        for mid, scores in node_feedbacks.items():
            node = _load_knowledge_node(mid)
            if not node:
                continue
            
            old_value = node.get("value_score", 0.5)
            new_value = old_value
            
            # 逐条应用 EMA
            for s in scores:
                new_value = alpha * new_value + (1 - alpha) * s
            
            new_value = round(max(0.0, min(1.0, new_value)), 4)
            
            if new_value != old_value:
                node["value_score"] = new_value
                self.estimator._save_node(mid, node)
    
    # --------------------------------------------------------
    #  查询反馈统计
    # --------------------------------------------------------
    
    def get_feedback_stats(self, memory_id: Optional[str] = None) -> Dict:
        """
        获取反馈统计。
        
        Args:
            memory_id: 指定节点 ID，为 None 时返回全局统计
        
        Returns:
            dict: 统计信息
        """
        entries = self._load_all_entries()
        
        if memory_id:
            entries = [e for e in entries if e.get("memory_id") == memory_id]
        
        total = len(entries)
        explicit = sum(1 for e in entries if e.get("source") == "explicit")
        implicit = sum(1 for e in entries if e.get("source") == "implicit")
        
        # 显式评分统计
        ratings = [e["rating"] for e in entries if e.get("source") == "explicit" and "rating" in e]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        # 隐式反馈统计
        referenced = sum(1 for e in entries if e.get("action") == "referenced")
        not_used = sum(1 for e in entries if e.get("action") == "not_used")
        
        return {
            "total": total,
            "explicit_count": explicit,
            "implicit_count": implicit,
            "avg_rating": round(avg_rating, 2),
            "rating_distribution": {
                str(r): ratings.count(r) for r in range(1, 6)
            },
            "referenced_count": referenced,
            "not_used_count": not_used,
        }
    
    def get_top_feedback_nodes(self, top_n: int = 10) -> List[Dict]:
        """
        获取反馈最多的 Top-N 节点。
        
        Args:
            top_n: 返回数量
        
        Returns:
            list: [{memory_id, feedback_count, avg_rating}, ...]
        """
        entries = self._load_all_entries()
        node_stats: Dict[str, Dict] = {}
        
        for e in entries:
            mid = e.get("memory_id", "")
            if mid not in node_stats:
                node_stats[mid] = {"count": 0, "ratings": []}
            node_stats[mid]["count"] += 1
            if e.get("source") == "explicit" and "rating" in e:
                node_stats[mid]["ratings"].append(e["rating"])
        
        sorted_nodes = sorted(
            node_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )[:top_n]
        
        return [
            {
                "memory_id": mid,
                "feedback_count": s["count"],
                "avg_rating": round(sum(s["ratings"]) / len(s["ratings"]), 2) if s["ratings"] else 0.0,
            }
            for mid, s in sorted_nodes
        ]
    
    # --------------------------------------------------------
    #  内部工具方法
    # --------------------------------------------------------
    
    def _append_entry(self, entry: Dict[str, Any]):
        """追加一条反馈记录到日志文件。"""
        _ensure_log_file()
        with open(FEEDBACK_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def _load_all_entries(self) -> List[Dict[str, Any]]:
        """加载所有反馈条目。"""
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


# ============================================================
#  模块级快捷函数
# ============================================================

_collector_instance: Optional[FeedbackCollector] = None


def _get_collector() -> FeedbackCollector:
    """获取单例反馈收集器。"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = FeedbackCollector()
    return _collector_instance


def record_feedback(memory_id: str, query: str, rating: int,
                     source: str = "explicit") -> Dict:
    """快捷函数：记录显式反馈。"""
    return _get_collector().record_feedback(memory_id, query, rating, source)


def record_implicit_feedback(memory_id: str, query: str, action: str) -> Dict:
    """快捷函数：记录隐式反馈。"""
    return _get_collector().record_implicit_feedback(memory_id, query, action)


# ---------- 独立运行 ----------
if __name__ == "__main__":
    print("=" * 60)
    print("FeedbackCollector 测试")
    print("=" * 60)
    
    collector = FeedbackCollector(auto_update=False)  # 测试模式不更新文件
    
    # 测试 1：显式反馈
    print("\n[1] 记录显式反馈（5星）")
    entry = collector.record_feedback(
        memory_id="kn_001",
        query="决策日志规则",
        rating=5,
    )
    print(f"  写入: {json.dumps(entry, ensure_ascii=False)}")
    
    # 测试 2：隐式正反馈
    print("\n[2] 记录隐式正反馈（被引用）")
    entry = collector.record_implicit_feedback(
        memory_id="kn_005",
        query="反转策略",
        action="referenced",
    )
    print(f"  写入: {json.dumps(entry, ensure_ascii=False)}")
    
    # 测试 3：统计
    print("\n[3] 反馈统计（全局）")
    stats = collector.get_feedback_stats()
    print(f"  总反馈数: {stats['total']}")
    print(f"  显式: {stats['explicit_count']}")
    print(f"  隐式: {stats['implicit_count']}")
    print(f"  平均评分: {stats['avg_rating']}")
    
    print("\n[4] Top 反馈节点")
    top = collector.get_top_feedback_nodes(top_n=5)
    for t in top:
        print(f"  {t['memory_id']}: {t['feedback_count']} 次反馈, 平均 {t['avg_rating']} 星")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


# ============================================================
#  Phase 2: 反馈通路扩展
# ============================================================
# 新增三种反馈类型（增量添加，不修改 Phase 1 核心逻辑）：
#   1. record_reference_feedback: 引用即反馈（记忆被写入输出→轻微加分）
#   2. record_reverse_feedback: 反向反馈（检索到但未用→轻微降权）
#   3. record_delayed_feedback: 延迟反馈（记忆捕获阶段回溯评估）
#
# 开关：ENABLE_FEEDBACK_EXTENDED 环境变量（默认关闭，可一键回滚）
# ============================================================

import os as _os_ph2

# Phase 2 反馈扩展开关
ENABLE_FEEDBACK_EXTENDED = _os_ph2.environ.get(
    "ENABLE_FEEDBACK_EXTENDED", "false"
).lower() in ("true", "1", "yes")

# 引用即反馈的分数（轻微正向，弱于显式5星和隐式referenced）
REFERENCE_FEEDBACK_SCORE = 0.45

# 反向反馈的分数（轻微负向，仅作统计用，默认不扣value_score）
REVERSE_FEEDBACK_SCORE = 0.15  # 作为"弱负反馈"统计，不直接降分

# 反向反馈是否影响 value_score（默认关闭，更保守）
REVERSE_FEEDBACK_AFFECTS_VALUE = _os_ph2.environ.get(
    "REVERSE_FEEDBACK_AFFECTS_VALUE", "false"
).lower() in ("true", "1", "yes")

# 延迟反馈的权重系数（相对于即时反馈的折扣）
DELAYED_FEEDBACK_DISCOUNT = 0.8


def _ph2_record_extension(collector, entry: Dict):
    """
    Phase 2 扩展：根据反馈类型自动更新 value_score。
    
    这是一个钩子函数，在记录扩展反馈类型后调用。
    独立于 Phase 1 的 auto_update 逻辑，互不干扰。
    """
    if not ENABLE_FEEDBACK_EXTENDED or not collector.auto_update:
        return
    
    action = entry.get("action", "")
    source = entry.get("source", "")
    
    if source == "reference":
        # 引用即反馈：轻微正向
        collector.estimator.update_value(
            entry["memory_id"], REFERENCE_FEEDBACK_SCORE
        )
    elif source == "reverse":
        # 反向反馈：仅当开关打开时才扣分
        if REVERSE_FEEDBACK_AFFECTS_VALUE:
            # 轻微降权：用一个低分数做 EMA 更新
            collector.estimator.update_value(
                entry["memory_id"], REVERSE_FEEDBACK_SCORE
            )


# ---- 扩展 FeedbackCollector 类的方法（monkey patch 式扩展）----

def _record_reference_feedback(
    self,
    memory_id: str,
    query: str,
    output_context: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    【Phase 2】引用即反馈：记忆被写入输出内容时自动记录正反馈。
    
    与 record_implicit_feedback(action="referenced") 的区别：
    - referenced 表示"被检索到且被使用"（较强信号）
    - reference 表示"被引用到输出中"（更轻量的信号，可批量触发）
    
    评分：0.45（弱于显式5星和referenced，表示"被用到了但不确定多有用"）
    
    Args:
        memory_id: 记忆节点ID
        query: 触发的查询
        output_context: 引用出现在什么输出上下文中（可选，用于追溯）
        extra: 额外信息
    
    Returns:
        dict: 写入的反馈条目
    """
    if not ENABLE_FEEDBACK_EXTENDED:
        # 开关关闭时，降级为隐式referenced反馈
        return self.record_implicit_feedback(memory_id, query, "referenced", extra)
    
    entry = {
        "timestamp": _now_iso(),
        "memory_id": memory_id,
        "query": query,
        "source": "reference",
        "action": "cited_in_output",
        "output_context": output_context[:200] if output_context else "",
        "extra": extra or {},
    }
    
    self._append_entry(entry)
    _ph2_record_extension(self, entry)
    
    return entry


def _record_reverse_feedback(
    self,
    memory_id: str,
    query: str,
    reason: str = "not_used_after_retrieval",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    【Phase 2】反向反馈：检索到但完全未被使用 → 轻微降权信号。
    
    设计原则：
    - 只做统计记录，默认不影响 value_score（保守策略）
    - 可通过 REVERSE_FEEDBACK_AFFECTS_VALUE=true 开启扣分
    - 扣分很轻微（0.15 分），避免噪声误杀
    - 与 not_used 的区别：not_used 是"展示了但用户没点"，
      reverse_feedback 是"检索结果中出现了但最终回答完全没用到"
    
    Args:
        memory_id: 记忆节点ID
        query: 查询文本
        reason: 未使用原因
        extra: 额外信息
    
    Returns:
        dict: 写入的反馈条目
    """
    if not ENABLE_FEEDBACK_EXTENDED:
        # 开关关闭时，降级为隐式 not_used 反馈（仅统计）
        return self.record_implicit_feedback(memory_id, query, "not_used", extra)
    
    entry = {
        "timestamp": _now_iso(),
        "memory_id": memory_id,
        "query": query,
        "source": "reverse",
        "action": "not_used",
        "reason": reason,
        "extra": extra or {},
    }
    
    self._append_entry(entry)
    _ph2_record_extension(self, entry)
    
    return entry


def _record_delayed_feedback(
    self,
    memory_id: str,
    query: str,
    rating: int,
    capture_session_id: str = "",
    reflection: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    【Phase 2】延迟反馈：任务完成后（记忆捕获阶段）回溯评估本次用到的记忆。
    
    与即时显式反馈的区别：
    - 即时反馈：检索/使用时立即打分
    - 延迟反馈：任务完成后回顾时重新评估，往往更准确
    - 延迟反馈权重打 8 折（DELAYED_FEEDBACK_DISCOUNT），
      因为时间间隔越长，记忆对结果的贡献越难精确归因
    
    Args:
        memory_id: 记忆节点ID
        query: 原始查询
        rating: 评分 1-5
        capture_session_id: 记忆捕获会话ID（用于关联一批延迟反馈）
        reflection: 回顾反思内容（可选）
        extra: 额外信息
    
    Returns:
        dict: 写入的反馈条目
    """
    if not ENABLE_FEEDBACK_EXTENDED:
        # 开关关闭时，降级为普通显式反馈
        return self.record_feedback(memory_id, query, rating, "explicit", extra)
    
    rating = max(1, min(5, int(rating)))
    
    entry = {
        "timestamp": _now_iso(),
        "memory_id": memory_id,
        "query": query,
        "source": "delayed",
        "rating": rating,
        "capture_session_id": capture_session_id,
        "reflection": reflection[:500] if reflection else "",
        "discount": DELAYED_FEEDBACK_DISCOUNT,
        "extra": extra or {},
    }
    
    self._append_entry(entry)
    
    # 自动更新价值分（打折扣的反馈分）
    if self.auto_update:
        feedback_score = (rating - 1) / 4.0
        # 延迟反馈权重打折扣
        adjusted_score = 0.5 + (feedback_score - 0.5) * DELAYED_FEEDBACK_DISCOUNT
        adjusted_score = max(0.0, min(1.0, adjusted_score))
        self.estimator.update_value(memory_id, adjusted_score)
    
    return entry


def _record_batch_delayed_feedback(
    self,
    memory_ids: List[str],
    query: str,
    ratings: Dict[str, int],
    capture_session_id: str = "",
    reflections: Optional[Dict[str, str]] = None,
) -> int:
    """
    【Phase 2】批量延迟反馈：记忆捕获阶段对一批记忆进行回溯评估。
    
    典型场景：每日记忆捕获时，对当天用到的所有记忆统一打延迟反馈。
    
    Args:
        memory_ids: 记忆节点ID列表
        query: 关联的查询/任务描述
        ratings: {memory_id: rating} 评分映射
        capture_session_id: 捕获会话ID
        reflections: {memory_id: reflection} 反思内容映射
    
    Returns:
        int: 成功记录的条数
    """
    if not memory_ids:
        return 0
    
    reflections = reflections or {}
    count = 0
    
    for mid in memory_ids:
        rating = ratings.get(mid, 3)
        reflection = reflections.get(mid, "")
        self.record_delayed_feedback(
            memory_id=mid,
            query=query,
            rating=rating,
            capture_session_id=capture_session_id,
            reflection=reflection,
        )
        count += 1
    
    return count


def _get_extended_feedback_stats(
    self, memory_id: Optional[str] = None
) -> Dict:
    """
    【Phase 2】获取扩展反馈统计（含引用反馈、反向反馈、延迟反馈）。
    
    Returns:
        dict: 在原有统计基础上新增：
            reference_count: 引用反馈次数
            reverse_count: 反向反馈次数
            delayed_count: 延迟反馈次数
            delayed_avg_rating: 延迟反馈平均评分
    """
    base_stats = self.get_feedback_stats(memory_id)
    
    entries = self._load_all_entries()
    if memory_id:
        entries = [e for e in entries if e.get("memory_id") == memory_id]
    
    reference_count = sum(1 for e in entries if e.get("source") == "reference")
    reverse_count = sum(1 for e in entries if e.get("source") == "reverse")
    delayed_entries = [e for e in entries if e.get("source") == "delayed"]
    delayed_count = len(delayed_entries)
    
    delayed_ratings = [e["rating"] for e in delayed_entries if "rating" in e]
    delayed_avg = (
        sum(delayed_ratings) / len(delayed_ratings)
        if delayed_ratings else 0.0
    )
    
    base_stats.update({
        "reference_count": reference_count,
        "reverse_count": reverse_count,
        "delayed_count": delayed_count,
        "delayed_avg_rating": round(delayed_avg, 2),
    })
    
    return base_stats


# 绑定新方法到 FeedbackCollector 类
FeedbackCollector.record_reference_feedback = _record_reference_feedback
FeedbackCollector.record_reverse_feedback = _record_reverse_feedback
FeedbackCollector.record_delayed_feedback = _record_delayed_feedback
FeedbackCollector.record_batch_delayed_feedback = _record_batch_delayed_feedback
FeedbackCollector.get_extended_feedback_stats = _get_extended_feedback_stats


# ============================================================
#  Phase 2 模块级快捷函数
# ============================================================

def record_reference_feedback(memory_id: str, query: str,
                               output_context: str = "") -> Dict:
    """【Phase 2】快捷函数：记录引用即反馈。"""
    return _get_collector().record_reference_feedback(memory_id, query, output_context)


def record_reverse_feedback(memory_id: str, query: str,
                             reason: str = "not_used_after_retrieval") -> Dict:
    """【Phase 2】快捷函数：记录反向反馈。"""
    return _get_collector().record_reverse_feedback(memory_id, query, reason)


def record_delayed_feedback(memory_id: str, query: str, rating: int,
                             capture_session_id: str = "") -> Dict:
    """【Phase 2】快捷函数：记录延迟反馈。"""
    return _get_collector().record_delayed_feedback(
        memory_id, query, rating, capture_session_id
    )
