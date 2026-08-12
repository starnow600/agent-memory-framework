"""
PlugMem Phase 2 - 混合检索器 (Hybrid Retriever)

两路检索融合：
  第一路：概念路由检索（高精度快路径，从 knowledge_index.json 匹配概念 → 定位知识节点）
  第二路：语义搜索兜底（高召回，调用 memory_search 或模拟语义匹配）

输出：结构化结果列表，每项含内容、来源类型、置信度、溯源引用
"""

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).parent
INDEX_PATH = BASE_DIR / "knowledge_index.json"
NODES_DIR = BASE_DIR / "knowledge_nodes"


# ---------- 工具函数 ----------
def load_knowledge_index() -> Dict:
    """加载知识节点概念索引。"""
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_knowledge_node(node_id: str) -> Optional[Dict]:
    """根据 node_id 加载单个知识节点文件。"""
    # 模糊匹配文件名
    for fname in os.listdir(NODES_DIR):
        if fname.startswith(f"{node_id}_") and fname.endswith(".json"):
            with open(NODES_DIR / fname, "r", encoding="utf-8") as f:
                return json.load(f)
    return None


def load_all_knowledge_nodes() -> List[Dict]:
    """加载所有知识节点，用于语义兜底匹配。"""
    nodes = []
    for fname in sorted(os.listdir(NODES_DIR)):
        if fname.endswith(".json") and fname.startswith("kn_"):
            with open(NODES_DIR / fname, "r", encoding="utf-8") as f:
                nodes.append(json.load(f))
    return nodes


def tokenize_query(query: str) -> List[str]:
    """
    简单中文分词：提取 query 中的关键词片段。
    用字符 n-gram + 停用词过滤 的方式提取候选概念。
    """
    # 去除标点和空白
    clean = re.sub(r"[，。？！、；：""''（）\s,.!?;:'\"()\[\]【】]", " ", query)
    words = [w for w in clean.split() if w]
    
    # 生成 2-gram ~ 4-gram 候选（中文概念多为2-4字）
    candidates = set(words)
    for w in words:
        for n in range(2, min(5, len(w) + 1)):
            for i in range(len(w) - n + 1):
                candidates.add(w[i:i+n])
    
    # 过滤太短或太长
    candidates = {c for c in candidates if 2 <= len(c) <= 8}
    return list(candidates)


# ---------- 第一路：概念路由检索 ----------
def concept_route_search(query: str, index: Dict, max_results: int = 5) -> List[Dict]:
    """
    概念路由检索：从 query 中提取关键词，匹配 concept_index 中的概念，
    按节点命中概念数排序，返回 Top-N 知识节点。
    
    Args:
        query: 用户查询
        index: knowledge_index.json 加载后的字典
        max_results: 返回最大结果数
    
    Returns:
        列表，每项为 dict: {
            "content": str,           # 节点命题内容
            "source_type": str,       # "knowledge_node"
            "node_id": str,           # 节点ID (如 kn_001)
            "confidence": float,      # 置信度 0-1
            "matched_concepts": list, # 匹配到的概念列表
            "source_ref": str,        # 溯源引用标记
            "source_file": str,       # 源文件路径
            "source_anchor": str      # 源锚点
        }
    """
    concept_index = index.get("concept_index", {})
    query_tokens = tokenize_query(query)
    query_lower = query.lower()
    
    # 记录每个节点命中的概念
    node_hits: Dict[str, List[str]] = {}
    
    # 精确匹配概念
    for concept, node_ids in concept_index.items():
        # 方式1：概念完全出现在 query 中
        if concept in query_lower:
            for nid in node_ids:
                node_hits.setdefault(nid, []).append(concept)
            continue
        
        # 方式2：query 的 n-gram 与概念重叠（模糊匹配）
        concept_lower = concept.lower()
        for token in query_tokens:
            if token and (token in concept_lower or concept_lower in token):
                # 只匹配长度≥2的有效重叠
                if len(token) >= 2 and len(concept_lower) >= 2:
                    for nid in node_ids:
                        if concept not in node_hits.get(nid, []):
                            node_hits.setdefault(nid, []).append(f"{concept}~{token}")
                    break
    
    if not node_hits:
        return []
    
    # 按命中概念数降序排序
    sorted_nodes = sorted(
        node_hits.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    results = []
    for node_id, matched_concepts in sorted_nodes[:max_results]:
        node = load_knowledge_node(node_id)
        if not node:
            continue
        
        # 置信度：基础分 + 命中概念数加权 + 节点自身置信度
        base_conf = 0.5
        concept_bonus = min(len(matched_concepts) * 0.15, 0.3)
        conf_level = {"high": 0.15, "medium": 0.08, "low": 0.0}.get(node.get("confidence", "medium"), 0.08)
        confidence = min(base_conf + concept_bonus + conf_level, 1.0)
        
        results.append({
            "content": node["proposition"],
            "source_type": "knowledge_node",
            "node_id": node_id,
            "confidence": round(confidence, 3),
            "matched_concepts": matched_concepts,
            "source_ref": f"[{node_id}]",
            "source_file": node.get("source_file", ""),
            "source_anchor": node.get("source_anchor", ""),
        })
    
    return results


# ---------- 第二路：语义搜索兜底 ----------
def semantic_fallback_search(query: str, all_nodes: List[Dict], 
                              exclude_ids: List[str] = None,
                              max_results: int = 5) -> List[Dict]:
    """
    语义搜索兜底：当 memory_search 工具不可用时，用关键词重叠度做近似语义匹配。
    
    注意：在真实环境中，这里应调用 memory_search 工具。
    当前实现为本地模拟版，基于 query 与节点 proposition/concepts 的词重叠度评分。
    
    Args:
        query: 用户查询
        all_nodes: 所有知识节点列表
        exclude_ids: 需要排除的节点ID（已在概念路由中返回的）
        max_results: 返回最大结果数
    
    Returns:
        同 concept_route_search 的格式，source_type 为 "semantic"
    """
    if exclude_ids is None:
        exclude_ids = []
    
    query_tokens = set(tokenize_query(query))
    query_lower = query.lower()
    scored = []
    
    for node in all_nodes:
        if node["id"] in exclude_ids:
            continue
        
        # 计算语义相关度分数（词重叠 + 命题包含度）
        prop = node["proposition"].lower()
        concepts = [c.lower() for c in node.get("concepts", [])]
        
        # 1. query 词汇出现在命题中的比例
        prop_hits = sum(1 for t in query_tokens if t in prop)
        prop_score = prop_hits / max(len(query_tokens), 1)
        
        # 2. query 词汇出现在概念标签中的比例
        concept_hits = sum(1 for t in query_tokens if any(t in c for c in concepts))
        concept_score = concept_hits / max(len(query_tokens), 1)
        
        # 3. query 整句包含度（长词匹配加分）
        phrase_bonus = 0.0
        for n in range(min(len(query_lower), 8), 3, -1):
            for i in range(len(query_lower) - n + 1):
                phrase = query_lower[i:i+n]
                if phrase in prop or any(phrase in c for c in concepts):
                    phrase_bonus = n * 0.02
                    break
            if phrase_bonus > 0:
                break
        
        # 综合评分
        total_score = prop_score * 0.5 + concept_score * 0.3 + phrase_bonus
        if total_score <= 0.02:  # 阈值降低，确保兜底时总能返回一些结果
            continue
        
        scored.append((node, total_score))
    
    # 按分数降序
    scored.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for node, score in scored[:max_results]:
        # 置信度：基于相似度分数，但语义兜底天然比概念路由低
        confidence = min(score * 0.8, 0.7)  # 最高0.7，低于概念路由的high
        
        results.append({
            "content": node["proposition"],
            "source_type": "semantic",
            "node_id": node["id"],
            "confidence": round(confidence, 3),
            "matched_concepts": node.get("concepts", []),
            "source_ref": f"[sem_{node['id']}]",
            "source_file": node.get("source_file", ""),
            "source_anchor": node.get("source_anchor", ""),
        })
    
    return results


# ---------- 合并与去重 ----------
def merge_and_rank(route_results: List[Dict], semantic_results: List[Dict],
                    max_results: int = 3) -> List[Dict]:
    """
    合并两路检索结果，去重，按置信度排序。
    
    去重规则：同一 node_id 只保留来源更权威的那条
    （knowledge_node 优先于 semantic）
    """
    merged = {}
    
    # 先加入概念路由结果（优先级高）
    for item in route_results:
        merged[item["node_id"]] = item
    
    # 再加入语义结果（只补充不重复的）
    for item in semantic_results:
        if item["node_id"] not in merged:
            merged[item["node_id"]] = item
    
    # 按置信度降序排序
    sorted_results = sorted(
        merged.values(),
        key=lambda x: x["confidence"],
        reverse=True
    )
    
    return sorted_results[:max_results]


# ---------- 主检索接口 ----------
def hybrid_retrieve(query: str, max_results: int = 3, 
                     use_semantic_fallback: bool = True) -> List[Dict]:
    """
    混合检索主入口：概念路由 + 语义兜底，返回融合排序后的结果。
    
    Args:
        query: 用户查询字符串
        max_results: 返回结果最大数量，默认3
        use_semantic_fallback: 是否启用语义搜索兜底（默认True）
    
    Returns:
        列表，每项为结构化检索结果字典
        
    Example:
        >>> results = hybrid_retrieve("记忆检索的流程是怎样的")
        >>> for r in results:
        ...     print(f"[{r['source_type']}] {r['source_ref']}: {r['content'][:50]}...")
    """
    # 加载索引
    index = load_knowledge_index()
    
    # 第一路：概念路由检索
    route_results = concept_route_search(query, index, max_results=max_results * 2)
    
    # 第二路：语义兜底
    semantic_results = []
    if use_semantic_fallback:
        all_nodes = load_all_knowledge_nodes()
        exclude_ids = [r["node_id"] for r in route_results]
        semantic_results = semantic_fallback_search(
            query, all_nodes, 
            exclude_ids=exclude_ids,
            max_results=max_results * 2
        )
    
    # 合并排序
    final_results = merge_and_rank(route_results, semantic_results, max_results)
    
    # 智能兜底：如果概念路由完全没命中且语义兜底结果也很少/质量低，
    # 降低阈值再做一次宽松匹配，确保总有结果返回
    if len(final_results) < max_results:
        all_nodes = load_all_knowledge_nodes()
        already_ids = {r["node_id"] for r in final_results}
        
        # 用更宽松的关键词重叠（2-gram）
        query_chars = set(query.replace(" ", ""))
        scored = []
        for node in all_nodes:
            if node["id"] in already_ids:
                continue
            prop_chars = set(node["proposition"])
            overlap = len(query_chars & prop_chars)
            if overlap >= 2:  # 至少2个字符重叠
                score = overlap / max(len(query_chars), 1)
                scored.append((node, score * 0.3))  # 宽松匹配置信度低
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        for node, score in scored:
            if len(final_results) >= max_results:
                break
            final_results.append({
                "content": node["proposition"],
                "source_type": "semantic",
                "node_id": node["id"],
                "confidence": round(score, 3),
                "matched_concepts": node.get("concepts", []),
                "source_ref": f"[sem_{node['id']}]",
                "source_file": node.get("source_file", ""),
                "source_anchor": node.get("source_anchor", ""),
            })
    
    return final_results


# ---------- 独立运行 ----------
if __name__ == "__main__":
    # 简单测试
    test_queries = [
        "记忆检索的流程是怎样的",
        "v6.0反转模式L3修正的逻辑是什么",
        "高风险操作校验规则是什么",
    ]
    
    print("=" * 60)
    print("混合检索测试（Hybrid Retriever Demo）")
    print("=" * 60)
    
    for q in test_queries:
        print(f"\n【Query】{q}")
        results = hybrid_retrieve(q, max_results=3)
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['source_type']}|{r['confidence']:.2f}] "
                  f"{r['source_ref']} {r['content'][:60]}...")
        if not results:
            print("  （无结果）")
