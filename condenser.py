"""
PlugMem Phase 2 - 推理压缩模块 (Condensation Module)

功能：
  输入检索到的多条记忆片段（混合检索结果）+ 当前任务/query
  输出 3-5 条 task-adaptive actionable guidance，每条附引用标记

设计说明：
  - 本模块采用 "规则蒸馏 + 自适应裁剪" 的策略，从检索结果中提取核心要点
  - 每条 guidance 控制在 30 字以内，保留溯源引用
  - 可被其他脚本 import 调用：from condenser import condense
  - 如有 LLM 接入条件，可调用 _condense_with_llm 替换为真正的推理压缩
"""

import re
from typing import List, Dict
from collections import Counter


# ---------- 辅助函数 ----------
def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文 1 字 ≈ 1 token，英文 1 词 ≈ 1 token。"""
    # 中文字符数 + 英文单词数
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    en_words = len(re.findall(r'[a-zA-Z]+', text))
    return cn_chars + en_words


def classify_query_type(query: str) -> str:
    """
    简单分类 query 类型，用于适配 guidance 风格。
    
    Returns:
        "howto"   - 怎么做（流程/方法/规则）
        "why"     - 为什么（原因/原理）
        "what"    - 是什么（定义/状态/数值）
        "general" - 通用查询
    """
    q = query.lower()
    if any(k in q for k in ["怎么", "如何", "流程", "步骤", "方法", "规则", "怎样", "怎么算"]):
        return "howto"
    if any(k in q for k in ["为什么", "原因", "原理", "为何", "逻辑"]):
        return "why"
    if any(k in q for k in ["是什么", "多少", "哪些", "有什么", "状态", "数值", "评分", "止损位"]):
        return "what"
    return "general"


def extract_key_sentence(proposition: str, query: str, max_len: int = 30) -> str:
    """
    从命题中提取最关键的句子/片段，裁剪到 max_len 字以内。
    
    策略：
      1. 优先提取破折号/冒号前的核心论断
      2. 优先保留与 query 相关的关键词附近的内容
      3. 超过长度时智能裁剪（找最近的自然断点）
      4. 括号类内容优先裁剪（补充信息通常在括号里）
    """
    # 去除换行，归一化
    text = proposition.strip().replace("\n", " ")
    
    # 如果总长度就不长，直接返回
    if len(text) <= max_len:
        return text
    
    # Step 1: 提取核心论断部分
    # 破折号/冒号/分号前的内容通常是核心结论
    core = text
    for sep in ["——", "——", ":", "："]:
        if sep in text:
            parts = text.split(sep, 1)
            first_part = parts[0].strip()
            # 前半部分足够完整且不太短
            if 6 <= len(first_part) <= max_len + 10:
                core = first_part
                break
    
    # Step 2: 如果还是太长，尝试去掉括号内的补充说明
    if len(core) > max_len:
        # 去掉括号及其中内容（括号通常是举例/补充）
        no_paren = re.sub(r'[（(][^）)]*[）)]', '', core)
        if len(no_paren) >= 6 and len(no_paren) < len(core):
            core = no_paren.strip()
            # 去掉括号后可能出现多余空格
            core = re.sub(r'\s+', '', core)
    
    # Step 3: 按标点分句，找最关键的一句
    if len(core) > max_len:
        sentences = re.split(r'[。；;，、]', core)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences and len(sentences) > 1:
            # 计算每句与 query 的相关度
            q_words = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', query.lower()))
            best_idx = 0
            best_score = 0
            
            for i, s in enumerate(sentences):
                s_words = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', s.lower()))
                overlap = len(q_words & s_words)
                # 第一句天然有加权（核心结论通常在首句）
                score = overlap + (0.5 if i == 0 else 0)
                if score > best_score:
                    best_score = score
                    best_idx = i
            
            core = sentences[best_idx]
    
    # Step 4: 最终裁剪，找自然断点
    if len(core) > max_len:
        # 先尝试在 max_len 附近找标点截断
        truncated = core[:max_len]
        best_pos = max_len
        
        # 向前找最近的标点（确保截断处语义相对完整）
        for pos in range(max_len, max(8, max_len - 10), -1):
            if truncated[pos-1] in "，。、；：,.!? ":
                best_pos = pos - 1
                break
        
        core = truncated[:best_pos].strip()
        
        # 如果末尾是不成对的括号或引号，去掉
        for ch in ['（', '(', '"', "'", '“', '‘']:
            if core.endswith(ch):
                core = core[:-1].strip()
    
    # 最终兜底：太短的guidance没有信息量，尝试扩充
    if len(core) < 8:
        # 用原文本的前半部分，宁可长一点也不要太短
        core = text[:max_len].strip()
    
    return core


def deduplicate_guidances(guidances: List[Dict]) -> List[Dict]:
    """
    去重：内容高度相似的 guidance 只保留一条（保留置信度高的）。
    用字符 n-gram 相似度判断。
    """
    if len(guidances) <= 1:
        return guidances
    
    def similarity(a: str, b: str) -> float:
        """3-gram Jaccard 相似度。"""
        def ngrams(text, n=3):
            return set(text[i:i+n] for i in range(len(text)-n+1))
        na, nb = ngrams(a), ngrams(b)
        if not na or not nb:
            return 0.0
        return len(na & nb) / len(na | nb)
    
    kept = []
    for g in guidances:
        is_dup = False
        for k in kept:
            if similarity(g["content"], k["content"]) > 0.5:  # 超过50%相似视为重复
                is_dup = True
                # 保留置信度高的
                if g["confidence"] > k["confidence"]:
                    kept.remove(k)
                    kept.append(g)
                break
        if not is_dup:
            kept.append(g)
    
    return kept


# ---------- 核心压缩函数 ----------
def condense(results: List[Dict], query: str, 
             max_guidance: int = 5,
             min_guidance: int = 3,
             max_chars_per: int = 30) -> List[Dict]:
    """
    将检索结果 condense 为 3-5 条 task-adaptive actionable guidance。
    
    Args:
        results: 混合检索结果列表，每项为 dict（含 content/source_type/confidence/source_ref 等）
        query: 当前任务/查询，用于适配 guidance 风格
        max_guidance: 最大输出 guidance 条数，默认5
        min_guidance: 最小输出 guidance 条数，默认3
        max_chars_per: 单条 guidance 最大字数，默认30
    
    Returns:
        列表，每项为 dict: {
            "guidance": str,     # 压缩后的指导语句（含引用标记）
            "content": str,      # guidance 纯文本（不含引用，便于统计）
            "source_ref": str,   # 溯源引用标记，如 [kn_015]
            "node_id": str,      # 来源节点ID
            "confidence": float  # 置信度
        }
    
    Example:
        >>> from hybrid_retriever import hybrid_retrieve
        >>> from condenser import condense
        >>> results = hybrid_retrieve("记忆检索的流程是怎样的")
        >>> guidance_list = condense(results, "记忆检索的流程是怎样的")
        >>> for g in guidance_list:
        ...     print(g["guidance"])
    """
    if not results:
        return []
    
    query_type = classify_query_type(query)
    
    # Step 1: 从每条检索结果中提取关键句
    raw_guidances = []
    for r in results:
        key_sent = extract_key_sentence(r["content"], query, max_len=max_chars_per)
        
        # 根据 query 类型微调表达
        if query_type == "howto" and not re.match(r'^(应|须|需|要|必须|应当)', key_sent):
            # howto 类查询，guidance 尽量用祈使/规则语气
            pass  # 保持原文，不强行改写，保留准确度
        
        raw_guidances.append({
            "content": key_sent,
            "source_ref": r["source_ref"],
            "node_id": r["node_id"],
            "confidence": r["confidence"],
            "source_type": r["source_type"],
        })
    
    # Step 2: 按置信度排序
    raw_guidances.sort(key=lambda x: x["confidence"], reverse=True)
    
    # Step 3: 去重
    raw_guidances = deduplicate_guidances(raw_guidances)
    
    # Step 4: 选择 3-5 条
    # 优先选择 knowledge_node 来源的（精度高），再补充 semantic 来源的
    kn_guidances = [g for g in raw_guidances if g["source_type"] == "knowledge_node"]
    sem_guidances = [g for g in raw_guidances if g["source_type"] == "semantic"]
    
    final_guidances = kn_guidances + sem_guidances
    
    # 过滤掉过短的guidance（<8字信息量不足）
    final_guidances = [g for g in final_guidances if len(g["content"]) >= 8]
    
    # 保证至少 min_guidance 条，不超过 max_guidance 条
    # 如果不足 min_guidance，从原结果中再提取句子
    if len(final_guidances) < min_guidance and len(results) > 0:
        # 尝试从已有结果中提取更多子句
        for r in results:
            if len(final_guidances) >= min_guidance:
                break
            # 检查是否已用了这个节点的主guidance
            used_ids = {g["node_id"] for g in final_guidances if g["source_type"] == r["source_type"]}
            if r["node_id"] in used_ids:
                # 从同一条命题中提取第二个分句
                prop = r["content"]
                # 用分号/句号分句
                parts = re.split(r'[；;。]', prop)
                if len(parts) > 1:
                    for p in parts[1:]:
                        p = p.strip()
                        if len(p) >= 10 and len(p) <= max_chars_per:
                            final_guidances.append({
                                "content": p[:max_chars_per],
                                "source_ref": r["source_ref"],
                                "node_id": r["node_id"],
                                "confidence": round(r["confidence"] * 0.85, 3),  # 次要点稍低
                                "source_type": r["source_type"],
                            })
                            if len(final_guidances) >= min_guidance:
                                break
    
    # 再次过滤过短的
    final_guidances = [g for g in final_guidances if len(g["content"]) >= 8]
    
    # 截取到 max_guidance
    final_guidances = final_guidances[:max_guidance]
    
    # Step 5: 组装最终输出（guidance + 引用）
    output = []
    for g in final_guidances:
        guidance_text = f"{g['content']}{g['source_ref']}"
        output.append({
            "guidance": guidance_text,
            "content": g["content"],
            "source_ref": g["source_ref"],
            "node_id": g["node_id"],
            "confidence": g["confidence"],
        })
    
    return output


def format_guidance_list(guidances: List[Dict]) -> str:
    """将 guidance 列表格式化为易读的多行字符串。"""
    if not guidances:
        return "（无相关指导）"
    lines = []
    for i, g in enumerate(guidances, 1):
        lines.append(f"{i}. {g['guidance']}")
    return "\n".join(lines)


def condense_and_format(results: List[Dict], query: str, **kwargs) -> str:
    """便捷函数：压缩 + 格式化一步到位。"""
    guidances = condense(results, query, **kwargs)
    return format_guidance_list(guidances)


# ---------- 统计辅助 ----------
def compute_compression_ratio(results: List[Dict], guidances: List[Dict]) -> Dict:
    """
    计算压缩比相关指标。
    
    Returns:
        dict: {
            "input_tokens": int,      # 输入 token 数（检索结果总字数）
            "output_tokens": int,     # 输出 token 数（guidance 总字数）
            "ratio": float,           # 压缩比 = output / input
            "saving_pct": float       # 节省比例 = 1 - ratio
        }
    """
    input_text = " ".join(r["content"] for r in results)
    output_text = " ".join(g["content"] for g in guidances)
    
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(output_text)
    
    ratio = output_tokens / max(input_tokens, 1)
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "ratio": round(ratio, 3),
        "saving_pct": round(1 - ratio, 3),
    }


# ---------- 独立运行测试 ----------
if __name__ == "__main__":
    from hybrid_retriever import hybrid_retrieve
    
    test_queries = [
        "记忆检索的流程是怎样的",
        "v6.0反转模式L3修正的逻辑是什么",
        "高风险操作校验规则是什么",
        "决策即记录机制是怎么落地的",
        "regime切换的确认规则是什么",
    ]
    
    print("=" * 60)
    print("Condenser 推理压缩测试")
    print("=" * 60)
    
    for q in test_queries:
        print(f"\n{'─' * 50}")
        print(f"【Query】{q}")
        print(f"【类型】{classify_query_type(q)}")
        
        results = hybrid_retrieve(q, max_results=3)
        guidances = condense(results, q)
        comp = compute_compression_ratio(results, guidances)
        
        print(f"\n【检索结果】({len(results)}条, 约{comp['input_tokens']}tokens)")
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['source_type']}|{r['confidence']:.2f}] {r['content'][:50]}...")
        
        print(f"\n【Guidance】({len(guidances)}条, 约{comp['output_tokens']}tokens, "
              f"压缩比{comp['ratio']*100:.1f}%)")
        print(format_guidance_list(guidances))
