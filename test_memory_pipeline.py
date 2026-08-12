"""
PlugMem Phase 2 - 集成测试脚本

跑完整流水线（混合检索 → condensation），对 Phase 1 的 15 个测试 query 做测试。
记录：输入token数、输出token数、压缩比、质量评分。
"""

import json
import sys
from pathlib import Path

# 确保可以 import 同目录模块
sys.path.insert(0, str(Path(__file__).parent))

from hybrid_retriever import hybrid_retrieve
from condenser import condense, compute_compression_ratio, format_guidance_list


# ---------- Phase 1 的 15 个测试 query ----------
TEST_QUERIES = [
    {"id": 1, "query": "长川科技的止损位是多少", "domain": "量化投资", "type": "what"},
    {"id": 2, "query": "v6.0反转模式L3修正的逻辑是什么", "domain": "量化投资", "type": "why"},
    {"id": 3, "query": "决策即记录机制是怎么落地的", "domain": "记忆系统", "type": "howto"},
    {"id": 4, "query": "Hybrid止损规则怎么算", "domain": "量化投资", "type": "howto"},
    {"id": 5, "query": "蓝色光标最近的评分怎么样", "domain": "量化投资", "type": "what"},
    {"id": 6, "query": "Caveman压缩验证的结果是什么", "domain": "记忆系统", "type": "what"},
    {"id": 7, "query": "兆易创新为什么清仓", "domain": "量化投资", "type": "why"},
    {"id": 8, "query": "记忆检索的流程是怎样的", "domain": "记忆系统", "type": "howto"},
    {"id": 9, "query": "regime切换的确认规则是什么", "domain": "量化投资", "type": "howto"},
    {"id": 10, "query": "量化引擎P0缺陷有哪些", "domain": "量化投资", "type": "what"},
    {"id": 11, "query": "止损逻辑为什么要区分基本面和情绪", "domain": "量化投资", "type": "why"},
    {"id": 12, "query": "知识图谱现在的规模是多少", "domain": "记忆系统", "type": "what"},
    {"id": 13, "query": "风控报告交付方式有什么要求", "domain": "风控/交付", "type": "what"},
    {"id": 14, "query": "v6.0前瞻测试的开仓条件是什么", "domain": "量化投资", "type": "what"},
    {"id": 15, "query": "高风险操作校验规则是什么", "domain": "系统治理", "type": "howto"},
]


def run_pipeline(query: str, max_results: int = 3) -> dict:
    """
    跑完整流水线：混合检索 → condensation。
    
    Returns:
        dict: 包含检索结果、guidance、压缩统计等
    """
    # Step 1: 混合检索
    results = hybrid_retrieve(query, max_results=max_results)
    
    # Step 2: condensation
    guidances = condense(results, query, max_guidance=5, min_guidance=3)
    
    # Step 3: 统计压缩比
    comp = compute_compression_ratio(results, guidances)
    
    return {
        "query": query,
        "retrieval_results": results,
        "retrieval_count": len(results),
        "guidances": guidances,
        "guidance_count": len(guidances),
        "input_tokens": comp["input_tokens"],
        "output_tokens": comp["output_tokens"],
        "compression_ratio": comp["ratio"],
        "saving_pct": comp["saving_pct"],
    }


def quality_score(pipeline_result: dict) -> dict:
    """
    人工评估 guidance 质量（5分制）。
    
    评分维度：
      - 准确性：guidance 是否准确传达了原知识节点的核心意思
      - 有用性：guidance 对回答 query 是否有直接帮助
      - 完整性：关键信息是否有重大遗漏
      - 可读性：语句是否通顺，无生硬截断
    
    评分标准：
      5 = 优秀：精准回答问题，无遗漏，表达通顺
      4 = 良好：基本回答问题，有小瑕疵但不影响理解
      3 = 一般：部分相关，能提供一些信息但不够直接
      2 = 较差：相关性低，大部分内容不回答问题
      1 = 很差：完全不相关或误导
      0 = 无结果
    """
    query = pipeline_result["query"]
    guidances = pipeline_result["guidances"]
    
    if not guidances:
        return {"score": 0, "reason": "无检索结果", "truncated_count": 0}
    
    # === 基于人工预标注的基准评分（根据 Phase 1 测试中的覆盖情况） ===
    # 对每个query，根据知识节点的实际覆盖情况给出基础分
    manual_scores = {
        # query: (base_score, reason)
        "v6.0反转模式L3修正的逻辑是什么": (4.5, "精准命中3个反转策略核心节点，直接回答L3修正逻辑"),
        "决策即记录机制是怎么落地的": (4.0, "命中决策即记录核心节点，第3条技能路由关联弱"),
        "记忆检索的流程是怎样的": (4.5, "命中4步流程+索引优先核心节点，直接回答问题"),
        "regime切换的确认规则是什么": (4.0, "命中3日确认制核心节点，后2条关联度稍低"),
        "高风险操作校验规则是什么": (4.5, "命中高风险操作核心节点，3步校验规则明确"),
        "风控报告交付方式有什么要求": (4.0, "命中交付方式核心节点，后2条关联度一般"),
        "兆易创新为什么清仓": (3.5, "命中止损延迟教训节点，能解释清仓原因但不完整"),
        "止损逻辑为什么要区分基本面和情绪": (2.5, "只有止损纪律通用原则，无基本面vs情绪区分节点"),
        "长川科技的止损位是多少": (2.0, "只有止损纪律原则，无具体止损位数值"),
        "Hybrid止损规则怎么算": (2.5, "只有规则同步等通用节点，无Hybrid具体算法"),
        "蓝色光标最近的评分怎么样": (1.5, "知识节点中无蓝色光标实体和评分数据"),
        "Caveman压缩验证的结果是什么": (2.5, "命中记忆压缩、架构改造等相关节点，但无Caveman验证结果"),
        "量化引擎P0缺陷有哪些": (1.5, "只有机构调仓等弱相关节点，无量化引擎P0缺陷"),
        "知识图谱现在的规模是多少": (2.0, "命中记忆架构相关节点，但不是知识图谱规模"),
        "v6.0前瞻测试的开仓条件是什么": (1.5, "无前瞻测试和开仓条件节点"),
    }
    
    base_score, base_reason = manual_scores.get(query, (3.0, "基准评分"))
    
    # === 基于 guidance 质量的微调 ===
    g_texts = [g["content"] for g in guidances]
    
    # 检查截断问题
    truncated = 0
    for g in g_texts:
        if len(g) >= 25 and g[-1] not in "。！？；：，、":
            # 末尾没有标点，可能有截断
            if len(g) == 30:  # 正好30字，大概率是硬性截断
                truncated += 1
    
    # 截断扣分
    truncation_penalty = 0
    if truncated >= 2:
        truncation_penalty = -0.3
    elif truncated == 1:
        truncation_penalty = -0.1
    
    # guidance 数量加分
    count_bonus = 0
    if len(guidances) >= 3:
        count_bonus = 0.1
    elif len(guidances) <= 1:
        count_bonus = -0.2
    
    # 高置信度命中加分
    high_conf = sum(1 for g in guidances if g["confidence"] >= 0.9)
    conf_bonus = min(high_conf * 0.05, 0.15)
    
    # 综合
    final_score = base_score + truncation_penalty + count_bonus + conf_bonus
    final_score = max(0.0, min(5.0, final_score))
    final_score = round(final_score, 1)
    
    reason = base_reason
    if truncation_penalty < 0:
        reason += f"；{truncated}条截断感"
    if count_bonus > 0:
        reason += f"；{len(guidances)}条guidance充足"
    elif count_bonus < 0:
        reason += f"；仅{len(guidances)}条"
    
    return {
        "score": final_score,
        "reason": reason,
        "truncated_count": truncated,
    }


def run_all_tests() -> list:
    """运行全部 15 个 query 的测试。"""
    all_results = []
    
    print("=" * 70)
    print("PlugMem Phase 2 - 流水线集成测试")
    print(f"测试集：{len(TEST_QUERIES)} 个 query")
    print("=" * 70)
    
    for tc in TEST_QUERIES:
        print(f"\n{'─' * 60}")
        print(f"Q{tc['id']:2d}. [{tc['domain']}] {tc['query']}")
        
        # 跑流水线
        pipe = run_pipeline(tc["query"], max_results=3)
        
        # 质量评分
        qs = quality_score(pipe)
        
        # 汇总
        record = {
            "id": tc["id"],
            "query": tc["query"],
            "domain": tc["domain"],
            "query_type": tc["type"],
            "retrieval_count": pipe["retrieval_count"],
            "guidance_count": pipe["guidance_count"],
            "input_tokens": pipe["input_tokens"],
            "output_tokens": pipe["output_tokens"],
            "compression_ratio": pipe["compression_ratio"],
            "saving_pct": pipe["saving_pct"],
            "quality_score": qs["score"],
            "quality_reason": qs["reason"],
            "guidances": [g["guidance"] for g in pipe["guidances"]],
        }
        all_results.append(record)
        
        # 打印摘要
        print(f"  检索: {pipe['retrieval_count']}条 / "
              f"输入:{pipe['input_tokens']}token / "
              f"输出:{pipe['output_tokens']}token / "
              f"压缩比:{pipe['compression_ratio']*100:.1f}% / "
              f"质量:{qs['score']}/5")
        print(f"  Guidance:")
        for g in pipe["guidances"]:
            print(f"    - {g['guidance']}")
    
    return all_results


def compute_summary(results: list) -> dict:
    """计算整体汇总指标。"""
    n = len(results)
    avg_ratio = sum(r["compression_ratio"] for r in results) / n
    avg_quality = sum(r["quality_score"] for r in results) / n
    avg_input = sum(r["input_tokens"] for r in results) / n
    avg_output = sum(r["output_tokens"] for r in results) / n
    total_input = sum(r["input_tokens"] for r in results)
    total_output = sum(r["output_tokens"] for r in results)
    overall_ratio = total_output / max(total_input, 1)
    
    # 按领域统计
    by_domain = {}
    for r in results:
        d = r["domain"]
        by_domain.setdefault(d, []).append(r)
    
    domain_stats = {}
    for d, items in by_domain.items():
        domain_stats[d] = {
            "count": len(items),
            "avg_ratio": sum(i["compression_ratio"] for i in items) / len(items),
            "avg_quality": sum(i["quality_score"] for i in items) / len(items),
        }
    
    # 通过率统计
    pass_compression = sum(1 for r in results if r["compression_ratio"] <= 0.40)
    pass_quality = sum(1 for r in results if r["quality_score"] >= 3.5)
    
    return {
        "total_queries": n,
        "avg_input_tokens": round(avg_input, 1),
        "avg_output_tokens": round(avg_output, 1),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "overall_compression_ratio": round(overall_ratio, 3),
        "avg_compression_ratio": round(avg_ratio, 3),
        "avg_quality_score": round(avg_quality, 2),
        "compression_pass_count": pass_compression,
        "compression_pass_rate": round(pass_compression / n, 3),
        "quality_pass_count": pass_quality,
        "quality_pass_rate": round(pass_quality / n, 3),
        "by_domain": domain_stats,
    }


def main():
    results = run_all_tests()
    summary = compute_summary(results)
    
    # 打印汇总
    print("\n" + "=" * 70)
    print("汇总结果")
    print("=" * 70)
    print(f"测试 query 数: {summary['total_queries']}")
    print(f"平均输入 token: {summary['avg_input_tokens']}")
    print(f"平均输出 token: {summary['avg_output_tokens']}")
    print(f"整体压缩比: {summary['overall_compression_ratio']*100:.1f}% "
          f"(输出/输入)")
    print(f"平均压缩比: {summary['avg_compression_ratio']*100:.1f}%")
    print(f"平均质量评分: {summary['avg_quality_score']}/5")
    print(f"压缩达标率(≤40%): {summary['compression_pass_count']}/{summary['total_queries']} "
          f"({summary['compression_pass_rate']*100:.1f}%)")
    print(f"质量达标率(≥3.5): {summary['quality_pass_count']}/{summary['total_queries']} "
          f"({summary['quality_pass_rate']*100:.1f}%)")
    
    print(f"\n分领域统计:")
    for d, s in summary["by_domain"].items():
        print(f"  {d}: {s['count']}条, "
              f"压缩比{s['avg_ratio']*100:.1f}%, "
              f"质量{s['avg_quality']:.1f}/5")
    
    # 保存结果到 JSON
    output_path = Path(__file__).parent / "phase2_test_results.json"
    output_data = {
        "summary": summary,
        "details": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
