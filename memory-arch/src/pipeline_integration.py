"""
PlugMem Phase 2 - Pipeline Integration 流水线集成

将 Phase 2 新模块与现有流水线集成：
  1. 索引同步：knowledge_index.json 和 recent_index.json 含 value_score 同步
  2. 图谱更新：价值分变化触发概念图谱权重更新
  3. L0热缓存管理：价值驱动的自动升降级 + 预取

开关：
  - ENABLE_PIPELINE_PHASE2 环境变量控制总开关
  - 各子模块有独立开关

所有集成均为增量添加，不修改 Phase 1 已有逻辑，关闭开关即完全回滚。
"""

import json
import os
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).parent.parent
NODES_DIR = BASE_DIR / "knowledge_nodes"
INDEX_PATH = BASE_DIR / "knowledge_index.json"
RECENT_INDEX_PATH = BASE_DIR / "recent_index.json"
QUALITY_STATE_PATH = BASE_DIR / "quality_state.json"

# 时区
TZ = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(TZ).isoformat()


# ---------- 开关 ----------
ENABLE_PIPELINE_PHASE2 = os.environ.get("ENABLE_PIPELINE_PHASE2", "false").lower() in (
    "true", "1", "yes"
)

# L0 预取大小（节点数量）
L0_PREFETCH_MAX = 20

# 图谱价值权重上限
GRAPH_VALUE_WEIGHT_MAX = 2.0


# ============================================================
#  1. 索引同步：value_score 同步
# ============================================================

def sync_value_scores_to_index() -> Dict:
    """
    将所有知识节点的 value_score 同步到 knowledge_index.json 和 recent_index.json。
    
    1. knowledge_index.json:
       - 新增 value_stats 段（各概念平均价值分、整体平均）
       - all_nodes 增加 value_score 信息
    
    2. recent_index.json:
       - 每条 entry 更新 value_score（如果有对应知识节点）
    
    这是索引同步脚本的 Phase 2 增量逻辑。
    开关关闭时，函数直接返回空结果，不修改任何文件。
    
    Returns:
        dict: {
            "knowledge_index_updated": bool,
            "recent_index_updated": bool,
            "nodes_updated": int,
            "value_stats": {...},
        }
    """
    if not ENABLE_PIPELINE_PHASE2:
        return {
            "knowledge_index_updated": False,
            "recent_index_updated": False,
            "nodes_updated": 0,
            "reason": "ENABLE_PIPELINE_PHASE2 disabled",
        }
    
    from .value_estimator import ValueEstimator, _load_knowledge_node
    ve = ValueEstimator()
    
    nodes_updated = 0
    node_values = {}
    
    # 收集所有节点的价值分
    if NODES_DIR.exists():
        for fname in sorted(os.listdir(NODES_DIR)):
            if not (fname.startswith("kn_") and fname.endswith(".json")):
                continue
            parts = fname.split("_")
            if len(parts) < 2 or parts[0] != "kn":
                continue
            node_id = f"kn_{parts[1]}"
            
            node = _load_knowledge_node(node_id)
            if node:
                vs = node.get("value_score", ve.estimate_value(node_id, node))
                node_values[node_id] = vs
                nodes_updated += 1
    
    if not node_values:
        return {
            "knowledge_index_updated": False,
            "recent_index_updated": False,
            "nodes_updated": 0,
        }
    
    # ---- 1. 更新 knowledge_index.json ----
    knowledge_index_updated = False
    if INDEX_PATH.exists():
        try:
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            
            # 计算各概念的价值统计
            concept_index = index_data.get("concept_index", {})
            value_by_concept = {}
            
            for concept, node_ids in concept_index.items():
                values = [node_values[nid] for nid in node_ids if nid in node_values]
                if values:
                    value_by_concept[concept] = {
                        "avg_value_score": round(sum(values) / len(values), 4),
                        "max_value_score": round(max(values), 4),
                        "min_value_score": round(min(values), 4),
                        "count": len(values),
                    }
            
            # 整体统计
            all_values = list(node_values.values())
            overall_avg = sum(all_values) / len(all_values) if all_values else 0.5
            
            # 价值分分布
            high = sum(1 for v in all_values if v >= 0.7)
            medium = sum(1 for v in all_values if 0.4 <= v < 0.7)
            low = sum(1 for v in all_values if v < 0.4)
            
            index_data["value_stats"] = {
                "overall_avg_value_score": round(overall_avg, 4),
                "overall_max_value_score": round(max(all_values), 4) if all_values else 0,
                "overall_min_value_score": round(min(all_values), 4) if all_values else 0,
                "distribution": {
                    "high (≥0.7)": high,
                    "medium (0.4-0.7)": medium,
                    "low (<0.4)": low,
                },
                "by_concept": value_by_concept,
                "synced_at": _now_iso(),
            }
            
            # all_nodes 增加 value_score 信息（如果 all_nodes 是dict结构）
            if isinstance(index_data.get("all_nodes"), dict):
                for nid, vs in node_values.items():
                    if nid in index_data["all_nodes"]:
                        if isinstance(index_data["all_nodes"][nid], dict):
                            index_data["all_nodes"][nid]["value_score"] = vs
            
            # 写回
            import tempfile
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=str(BASE_DIR), suffix=".tmp", prefix=".tmp_idx_"
            )
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, INDEX_PATH)
            knowledge_index_updated = True
        except (json.JSONDecodeError, IOError) as e:
            print(f"[pipeline] 更新 knowledge_index.json 失败: {e}")
    
    # ---- 2. 更新 recent_index.json ----
    recent_index_updated = False
    if RECENT_INDEX_PATH.exists():
        try:
            with open(RECENT_INDEX_PATH, "r", encoding="utf-8") as f:
                recent_data = json.load(f)
            
            entries = recent_data.get("entries", [])
            updated_count = 0
            
            # 预加载所有知识节点，避免重复迭代
            all_nodes_dict = dict(_iter_knowledge_nodes())
            
            # 建立concept到节点的倒排索引，加速匹配
            concept_to_nodes: Dict[str, List[str]] = {}
            for nid, node in all_nodes_dict.items():
                for concept in node.get("concepts", []):
                    concept_to_nodes.setdefault(concept, []).append(nid)
            
            for entry in entries:
                eid = entry.get("id", "")
                tags = entry.get("tags", [])
                summary = entry.get("summary", "")
                
                # 快速匹配：用 tags 匹配知识节点的 concepts
                # 先找出所有可能的候选节点
                candidate_ids = set()
                for tag in tags:
                    if tag in concept_to_nodes:
                        candidate_ids.update(concept_to_nodes[tag])
                
                best_match = None
                best_score = 0
                
                if candidate_ids:
                    # 在候选中做精确匹配
                    entry_text = (eid + " " + summary).lower()
                    for nid in candidate_ids:
                        node = all_nodes_dict.get(nid)
                        if not node:
                            continue
                        concepts = node.get("concepts", [])
                        # 计算 tag 命中数
                        hits = sum(1 for t in tags if any(
                            t.lower() in c.lower() or c.lower() in t.lower()
                            for c in concepts
                        ))
                        score = hits / max(len(tags), 1)
                        if score > best_score:
                            best_score = score
                            best_match = (nid, node)
                
                # 如果 tag 匹配没找到，用 category 做粗略匹配
                if not best_match:
                    category = entry.get("category", "")
                    if category == "decision":
                        # decision 类匹配高价值决策节点
                        decision_nodes = [
                            (nid, n) for nid, n in all_nodes_dict.items()
                            if "决策" in " ".join(n.get("concepts", []))
                            or "决策日志" in " ".join(n.get("concepts", []))
                        ]
                        if decision_nodes:
                            # 取价值分最高的
                            decision_nodes.sort(key=lambda x: x[1].get("value_score", 0), reverse=True)
                            best_match = decision_nodes[0]
                            best_score = 0.3
                
                if best_match and best_score >= 0.3:
                    nid, node = best_match
                    vs = node.get("value_score", 0.5)
                    entry["value_score"] = round(vs, 4)
                    entry["linked_node_id"] = nid
                    updated_count += 1
            
            recent_data["value_stats"] = {
                "updated_count": updated_count,
                "total_entries": len(entries),
                "synced_at": _now_iso(),
            }
            
            # 写回
            import tempfile
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=str(BASE_DIR), suffix=".tmp", prefix=".tmp_ridx_"
            )
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(recent_data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, RECENT_INDEX_PATH)
            recent_index_updated = True
        except (json.JSONDecodeError, IOError) as e:
            print(f"[pipeline] 更新 recent_index.json 失败: {e}")
    
    return {
        "knowledge_index_updated": knowledge_index_updated,
        "recent_index_updated": recent_index_updated,
        "nodes_updated": nodes_updated,
        "value_stats": {
            "overall_avg": round(sum(node_values.values()) / len(node_values), 4),
            "count": len(node_values),
        },
    }


def _iter_knowledge_nodes():
    """迭代所有知识节点（生成器）。"""
    from .value_estimator import _load_knowledge_node
    
    if not NODES_DIR.exists():
        return
    
    for fname in sorted(os.listdir(NODES_DIR)):
        if not (fname.startswith("kn_") and fname.endswith(".json")):
            continue
        parts = fname.split("_")
        if len(parts) < 2 or parts[0] != "kn":
            continue
        node_id = f"kn_{parts[1]}"
        node = _load_knowledge_node(node_id)
        if node:
            yield (node_id, node)


# ============================================================
#  2. 图谱更新：价值分驱动的图谱权重更新
# ============================================================

def update_graph_value_weights() -> Dict:
    """
    根据价值分更新知识图谱的边权重。
    
    规则：
    - 两个节点共享概念 → 有边
    - 边权重 = (value_a + value_b) / 2 * concept_overlap_ratio
    - 高价值节点的边权重更高，便于后续的图检索/推荐
    
    结果写入 quality_state.json 的 graph_weights 段。
    
    Returns:
        dict: {
            "edges_updated": int,
            "node_count": int,
            "avg_edge_weight": float,
        }
    """
    if not ENABLE_PIPELINE_PHASE2:
        return {"edges_updated": 0, "node_count": 0, "avg_edge_weight": 0.0,
                "reason": "pipeline phase2 disabled"}
    
    from .memory_quality_manager import _load_quality_state, _save_quality_state
    
    nodes = list(_iter_knowledge_nodes())
    node_count = len(nodes)
    
    edges = {}
    
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            nid1, node1 = nodes[i]
            nid2, node2 = nodes[j]
            
            concepts1 = set(node1.get("concepts", []))
            concepts2 = set(node2.get("concepts", []))
            
            intersection = concepts1 & concepts2
            if not intersection:
                continue
            
            union = concepts1 | concepts2
            overlap_ratio = len(intersection) / len(union) if union else 0
            
            v1 = node1.get("value_score", 0.5)
            v2 = node2.get("value_score", 0.5)
            
            # 边权重 = 平均价值分 × 概念重叠比 × 2（放大）
            weight = round((v1 + v2) / 2 * overlap_ratio * 2, 4)
            weight = min(weight, GRAPH_VALUE_WEIGHT_MAX)
            
            edge_key = tuple(sorted([nid1, nid2]))
            edges[edge_key] = {
                "weight": weight,
                "shared_concepts": list(intersection),
                "overlap_ratio": round(overlap_ratio, 4),
                "value_a": v1,
                "value_b": v2,
            }
    
    # 保存到质量状态
    state = _load_quality_state()
    state["graph_weights"] = {
        "version": "1.0",
        "updated_at": _now_iso(),
        "node_count": node_count,
        "edge_count": len(edges),
        "edges": {
            f"{a}-{b}": w for (a, b), w in edges.items()
        },
    }
    _save_quality_state(state)
    
    avg_weight = (
        sum(e["weight"] for e in edges.values()) / len(edges)
        if edges else 0.0
    )
    
    return {
        "edges_updated": len(edges),
        "node_count": node_count,
        "avg_edge_weight": round(avg_weight, 4),
    }


# ============================================================
#  3. L0热缓存管理：价值驱动的自动升降级 + 预取
# ============================================================

def run_l0_management() -> Dict:
    """
    执行 L0 热缓存管理的完整流程：
    1. 运行 MemoryQualityManager 的自动升降级
    2. 对 L0 中的节点执行预取（加载到内存缓存）
    3. 更新 L0 统计
    
    Returns:
        dict: {
            "l0_count": int,
            "promoted": list,
            "demoted": list,
            "prefetched": list,
            "avg_value": float,
        }
    """
    if not ENABLE_PIPELINE_PHASE2:
        return {"l0_count": 0, "promoted": [], "demoted": [],
                "prefetched": [], "avg_value": 0.0,
                "reason": "pipeline phase2 disabled"}
    
    from .memory_quality_manager import MemoryQualityManager
    from .value_estimator import _load_knowledge_node
    
    mgr = MemoryQualityManager(
        enable_auto_promote=True,
        enable_low_value_downrank=True,
        enable_superseded_exclude=True,
    )
    
    # 1. 执行自动升降级
    promotion_result = mgr.run_auto_promotion()
    
    # 2. 获取当前 L0 缓存
    l0_nodes = mgr.get_l0_cache()
    
    # 3. 控制 L0 大小（不超过上限），按健康度排序保留前N个
    l0_with_health = []
    for nid in l0_nodes:
        health = mgr.get_health_score(nid)
        node = _load_knowledge_node(nid)
        vs = node.get("value_score", 0.5) if node else 0.5
        l0_with_health.append((nid, health, vs))
    
    # 按健康度降序，保留最多 L0_PREFETCH_MAX 个
    l0_with_health.sort(key=lambda x: x[1], reverse=True)
    trimmed = l0_with_health[:L0_PREFETCH_MAX]
    
    # 如果有被裁剪的，从L0中移除
    if len(trimmed) < len(l0_with_health):
        state = _get_quality_state_for_update()
        trimmed_ids = set(t[0] for t in trimmed)
        removed = [nid for nid in l0_nodes if nid not in trimmed_ids]
        for nid in removed:
            if nid in state["l0_cache"]:
                state["l0_cache"].remove(nid)
        from .memory_quality_manager import _save_quality_state
        _save_quality_state(state)
        l0_nodes = [t[0] for t in trimmed]
    
    # 4. 预取（加载到内存缓存）
    prefetched = []
    for nid in l0_nodes:
        node = _load_knowledge_node(nid)
        if node:
            prefetched.append(nid)
    
    # 5. 计算 L0 平均价值分
    avg_value = (
        sum(t[2] for t in trimmed) / len(trimmed)
        if trimmed else 0.0
    )
    
    return {
        "l0_count": len(l0_nodes),
        "l0_max": L0_PREFETCH_MAX,
        "promoted": promotion_result.get("promoted", []),
        "demoted": promotion_result.get("demoted", []),
        "marked_low_value": promotion_result.get("marked_low_value", []),
        "prefetched": prefetched,
        "avg_value": round(avg_value, 4),
        "avg_health": round(sum(t[1] for t in trimmed) / len(trimmed), 4) if trimmed else 0.0,
    }


def _get_quality_state_for_update() -> Dict:
    """获取可修改的质量状态副本。"""
    from .memory_quality_manager import _load_quality_state
    from copy import deepcopy
    return deepcopy(_load_quality_state())


# ============================================================
#  4. 完整流水线入口
# ============================================================

def run_full_pipeline() -> Dict:
    """
    执行 Phase 2 完整流水线：
    1. 索引同步（value_score 同步）
    2. 图谱更新（价值权重更新）
    3. L0 管理（自动升降级 + 预取）
    
    Returns:
        dict: {
            "value_sync": {...},
            "graph_update": {...},
            "l0_management": {...},
            "total_time_ms": float,
            "success": bool,
        }
    """
    import time
    start = time.time()
    
    results = {
        "value_sync": {},
        "graph_update": {},
        "l0_management": {},
        "success": True,
    }
    
    try:
        # 1. 索引同步
        results["value_sync"] = sync_value_scores_to_index()
    except Exception as e:
        results["value_sync"] = {"error": str(e)}
        results["success"] = False
    
    try:
        # 2. 图谱更新
        results["graph_update"] = update_graph_value_weights()
    except Exception as e:
        results["graph_update"] = {"error": str(e)}
        results["success"] = False
    
    try:
        # 3. L0 管理
        results["l0_management"] = run_l0_management()
    except Exception as e:
        results["l0_management"] = {"error": str(e)}
        results["success"] = False
    
    elapsed_ms = round((time.time() - start) * 1000, 2)
    results["total_time_ms"] = elapsed_ms
    results["pipeline_version"] = "phase2_v1"
    results["ran_at"] = _now_iso()
    
    return results


# ============================================================
#  模块级快捷函数
# ============================================================

def sync_value_scores() -> Dict:
    """快捷函数：同步价值分到索引。"""
    return sync_value_scores_to_index()


def update_graph_weights() -> Dict:
    """快捷函数：更新图谱价值权重。"""
    return update_graph_value_weights()


def manage_l0() -> Dict:
    """快捷函数：管理L0热缓存。"""
    return run_l0_management()


# ---------- 独立运行 ----------
if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2 Pipeline Integration 测试")
    print("=" * 60)
    
    # 临时开启开关
    os.environ["ENABLE_PIPELINE_PHASE2"] = "true"
    
    print("\n【1. 索引同步（value_score）】")
    sync_result = sync_value_scores_to_index()
    print(f"  knowledge_index 更新: {sync_result.get('knowledge_index_updated')}")
    print(f"  recent_index 更新: {sync_result.get('recent_index_updated')}")
    print(f"  节点数: {sync_result.get('nodes_updated')}")
    if sync_result.get('value_stats'):
        print(f"  平均价值分: {sync_result['value_stats'].get('overall_avg'):.4f}")
    
    print("\n【2. 图谱价值权重更新】")
    graph_result = update_graph_value_weights()
    print(f"  边数: {graph_result.get('edges_updated')}")
    print(f"  节点数: {graph_result.get('node_count')}")
    print(f"  平均边权重: {graph_result.get('avg_edge_weight'):.4f}")
    
    print("\n【3. L0 热缓存管理】")
    l0_result = run_l0_management()
    print(f"  L0 数量: {l0_result.get('l0_count')}/{l0_result.get('l0_max')}")
    print(f"  新晋升: {l0_result.get('promoted')}")
    print(f"  降级: {l0_result.get('demoted')}")
    print(f"  低价值标记: {l0_result.get('marked_low_value')}")
    print(f"  平均价值分: {l0_result.get('avg_value'):.4f}")
    print(f"  平均健康度: {l0_result.get('avg_health'):.4f}")
    
    print("\n" + "=" * 60)
    print("流水线测试完成")
    print("=" * 60)
