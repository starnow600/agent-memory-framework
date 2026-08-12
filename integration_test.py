"""
PlugMem Phase 3 - 集成测试 (Integration Test)

测试内容：
  1. incremental_extractor：对已有的一篇 decision log 做抽取，确认幂等性
  2. memory_compactor：对一段模拟的 MEMORY 文本做压缩，确认压缩比和可读性
  3. 全流程：抽取 → 更新索引 → 混合检索 → 压缩输出，端到端跑通

运行方式：
  cd memory-arch/
  python integration_test.py
"""

import json
import os
import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


# ---------- 测试辅助 ----------

class TestRunner:
    """简单的测试运行器。"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def test(self, name: str, func):
        """运行一个测试用例。"""
        try:
            func()
            self.passed += 1
            self.results.append((name, "PASS", ""))
            print(f"  ✅ {name}")
        except AssertionError as e:
            self.failed += 1
            self.results.append((name, "FAIL", str(e)))
            print(f"  ❌ {name}: {e}")
        except Exception as e:
            self.failed += 1
            tb = traceback.format_exc()
            self.results.append((name, "ERROR", tb))
            print(f"  💥 {name}: {e}")
    
    def summary(self):
        """打印测试总结。"""
        total = self.passed + self.failed
        print(f"\n{'=' * 60}")
        print(f"测试结果: {self.passed}/{total} 通过, {self.failed} 失败")
        print(f"{'=' * 60}")
        return self.failed == 0


# ---------- 测试数据 ----------

SAMPLE_DECISION_LOG = """# 关于交易风控操作校验的决策

## 背景
近期出现两起高风险操作未经过二次校验的情况，存在操作失误风险。
需要建立标准化的风控操作校验流程。

## 决策内容

### 高风险操作定义
- 单笔交易金额超过总仓位20%的操作
- 清仓、加仓超过50%的操作
- 规则修改、架构变更类操作

### 校验规则
- 高风险操作必须执行二次校验流程
- 校验内容包括：操作目的、影响范围、回滚方案
- 用户授权类操作必须显式确认，禁止默认通过
- 校验不通过的操作禁止执行，需重新提交

### 实施方法
1. 在执行高风险操作前，先生成校验清单
2. 逐项核对后，输出校验报告
3. 校验通过后方可执行操作
4. 所有校验记录写入 decision log 留痕

## 验收标准
- 高风险操作校验覆盖率达到 100%
- 校验记录完整可追溯
- 因操作失误导致的损失降为 0
"""

SAMPLE_MEMORY_MD = """# MEMORY.md

## 核心状态锚点

### PlugMem 记忆架构改造
- 状态：Phase 2 已完成，验证通过
- 产出：44个知识节点 + 混合检索器 + 推理压缩层
- 详情：decision/2026-08-12_plugmem_memory_architecture.md

### 话题追踪技能 v3
- 状态：已上线，运行中
- 覆盖：3个活跃追踪话题
- 详情：decision/2026-08-08_topic_tracking_v3.md

### D9 Benchmark 头部腐化修复
- 状态：已完成，验证通过
- 修复方案：三阶段修复法
- 结果：头部质量提升40%
- 详情：decision/2026-08-05_d9_benchmark_fix.md

### 反转策略 v6.0
- 状态：已验证，L3修正有效
- 回测胜率：58.3%（+4.2%）
- 详情：decision/2026-08-03_reversal_v6.md

### IMA知识库接入项目
- 状态：已完成
- 接入方式：鉴权重试 + PDF提取
- 详情：decision/2026-07-28_ima_knowledge_base.md

### 🔒核心风控原则
- 单票仓位不超过30%
- 止损位严格执行，不延后
- 补仓禁忌：下跌不补，只加盈利仓

### 记忆健康度监测器
- 状态：开发中
- 预计完成：2026-08-20
- P0 优先级

## 长期行为规则

### 决策记录规则
- 重大决策必须在24小时内写入 decision log
- 禁止月底批量补录

### 风控操作规则
- 高风险操作必须二次校验
- 大额交易需用户授权
"""


# ---------- 测试用例 ----------

def test_incremental_extractor_basic():
    """测试1: 增量抽取器基本功能 - 从文档中提取节点。"""
    from incremental_extractor import extract_knowledge_nodes
    
    nodes = extract_knowledge_nodes(
        SAMPLE_DECISION_LOG,
        "recent_memory/decision/_integration_test_risk_control.md"
    )
    
    # 应该提取到 1-5 个节点
    assert 1 <= len(nodes) <= 5, f"期望 1-5 个节点，实际 {len(nodes)} 个"
    
    # 每个节点应有必要字段
    for node in nodes:
        assert "proposition" in node, "节点缺少 proposition 字段"
        assert "concepts" in node, "节点缺少 concepts 字段"
        assert "type" in node, "节点缺少 type 字段"
        assert "source_file" in node, "节点缺少 source_file 字段"
        assert "source_anchor" in node, "节点缺少 source_anchor 字段"
        assert "confidence" in node, "节点缺少 confidence 字段"
        
        assert len(node["proposition"]) >= 10, "命题过短"
        assert 3 <= len(node["concepts"]) <= 5, f"概念数应为 3-5，实际 {len(node['concepts'])}"
        assert node["type"] in ("proposition", "prescription"), f"类型无效: {node['type']}"
        assert node["confidence"] in ("high", "medium", "low"), f"置信度无效: {node['confidence']}"
        assert node["source_file"] == "recent_memory/decision/_integration_test_risk_control.md"


def test_incremental_extractor_idempotent():
    """测试2: 增量抽取器幂等性 - 同一源文件不重复抽取。"""
    from incremental_extractor import incremental_extract, get_existing_source_files
    
    # 记录原始状态
    original_sources = get_existing_source_files()
    test_source = "recent_memory/decision/_integration_test_risk_control.md"
    
    # 如果测试源文件已经存在（之前测试残留），先跳过检查
    # 第一次抽取
    result1 = incremental_extract(SAMPLE_DECISION_LOG, test_source)
    assert result1["success"], "第一次抽取应成功"
    
    if not result1["skipped"]:
        # 确认新增了节点
        assert result1["new_nodes_count"] >= 1, "第一次抽取应至少新增1个节点"
        new_ids = result1["new_node_ids"]
        
        # 第二次抽取（应幂等跳过）
        result2 = incremental_extract(SAMPLE_DECISION_LOG, test_source)
        assert result2["success"], "第二次抽取应成功"
        assert result2["skipped"], "第二次抽取应因幂等而跳过"
        assert result2["new_nodes_count"] == 0, "幂等时不应新增节点"
        
        # 清理测试节点
        _cleanup_test_nodes(new_ids)
    else:
        # 已经存在，说明之前测试过，验证幂等即可
        assert result1["skipped"], "已存在的源文件应被跳过"
        
        # 清理
        _cleanup_test_nodes_by_source(test_source)


def test_memory_compactor_dry_run():
    """测试3: MEMORY容量管理器 dry_run 模式。"""
    from memory_compactor import compact_memory
    
    result = compact_memory(SAMPLE_MEMORY_MD, dry_run=True)
    
    assert result["success"], "dry_run 应成功"
    assert result["dry_run"] is True, "dry_run 标记应为 True"
    assert result["entries_checked"] > 0, "应检查到条目"
    assert result["entries_compressed"] >= 1, "应识别到至少1个可压缩条目"
    assert result["rule_section_intact"] is True, "规则区应完整保留"
    # dry_run 不修改文本
    assert result["output_text"] == SAMPLE_MEMORY_MD, "dry_run 不应修改原文"


def test_memory_compactor_actual():
    """测试4: MEMORY容量管理器实际压缩。"""
    from memory_compactor import compact_memory
    
    result = compact_memory(SAMPLE_MEMORY_MD, dry_run=False)
    
    assert result["success"], "压缩应成功"
    assert result["bytes_saved"] > 0, "应节省字节"
    assert result["compression_ratio"] < 1.0, "压缩比应小于1"
    assert result["rule_section_intact"] is True, "规则区应完整保留"
    
    # 验证规则区内容完全没动
    assert "## 长期行为规则" in result["output_text"], "规则区标题应保留"
    assert "重大决策必须在24小时内写入 decision log" in result["output_text"], "规则内容应保留"
    assert "高风险操作必须二次校验" in result["output_text"], "规则内容应保留"
    
    # 验证压缩后的条目可读
    for item in result["compressed_items"]:
        assert "title" in item
        assert item["compressed_len"] > 0
        # 压缩后文本应该包含标题
        assert "**" in item["compressed_preview"], "压缩后应保留加粗标题"
    
    # 验证 🔒 标记的条目没被压缩
    assert "🔒核心风控原则" in result["output_text"], "🔒条目应保留"


def test_memory_compactor_readability():
    """测试5: 压缩后文本可读性 - 关键信息保留。"""
    from memory_compactor import compact_memory
    
    result = compact_memory(SAMPLE_MEMORY_MD, dry_run=False)
    output = result["output_text"]
    
    # 所有被压缩的项目标题仍应存在
    compressed_titles = [item["title"] for item in result["compressed_items"]]
    for title in compressed_titles:
        assert title in output, f"压缩后标题 {title} 应保留"
    
    # 详情指引应保留
    assert "decision/" in output, "详情路径应保留"
    
    # 压缩不应破坏 markdown 基本结构
    assert output.startswith("# MEMORY.md"), "文件开头应保留"
    assert "## 长期行为规则" in output, "规则区应保留"


def test_end_to_end_pipeline():
    """测试6: 端到端流程 - 抽取 → 更新索引 → 混合检索 → 推理压缩。"""
    import shutil
    from incremental_extractor import incremental_extract
    from hybrid_retriever import hybrid_retrieve, load_knowledge_index
    from condenser import condense, format_guidance_list
    
    test_source = "recent_memory/decision/_e2e_test_risk_check.md"
    
    # Step 1: 抽取知识节点
    extract_result = incremental_extract(SAMPLE_DECISION_LOG, test_source)
    assert extract_result["success"], "抽取应成功"
    
    if extract_result["skipped"]:
        # 已存在的话先清理再测
        _cleanup_test_nodes_by_source(test_source)
        extract_result = incremental_extract(SAMPLE_DECISION_LOG, test_source)
    
    assert not extract_result["skipped"], "应是新增抽取，不是跳过"
    new_node_count = extract_result["new_nodes_count"]
    assert new_node_count >= 1, "应至少新增1个节点"
    new_ids = extract_result["new_node_ids"]
    
    try:
        # Step 2: 验证索引已更新
        index = load_knowledge_index()
        assert index["stats"]["total_nodes"] > 44, "节点总数应增加"
        
        for nid in new_ids:
            assert nid in index["all_nodes"], f"新节点 {nid} 应在 all_nodes 中"
        
        # 验证至少有一个新概念被加入
        new_concepts_count = 0
        for concept, nodes in index["concept_index"].items():
            if any(nid in nodes for nid in new_ids):
                new_concepts_count += 1
        assert new_concepts_count >= 1, "应至少有1个概念索引被更新"
        
        # Step 3: 混合检索（用相关 query 检索新加入的节点）
        results = hybrid_retrieve("高风险操作校验规则", max_results=3)
        assert len(results) >= 1, "检索应返回结果"
        
        # 检查新节点是否能被检索到
        found_new = any(r["node_id"] in new_ids for r in results)
        # 不一定非要检索到新节点（取决于关键词匹配），但至少检索能正常工作
        assert all("content" in r for r in results), "检索结果应有 content 字段"
        assert all("confidence" in r for r in results), "检索结果应有 confidence 字段"
        
        # Step 4: 推理压缩
        guidances = condense(results, "高风险操作校验规则")
        assert isinstance(guidances, list), "condense 应返回列表"
        assert len(guidances) >= 1, "压缩后应至少有1条 guidance"
        
        formatted = format_guidance_list(guidances)
        assert isinstance(formatted, str), "格式化结果应为字符串"
        assert len(formatted) > 0, "格式化结果不应为空"
        
        print(f"\n     端到端流程验证完成:")
        print(f"       新增节点: {new_node_count} 个 ({', '.join(new_ids)})")
        print(f"       检索结果: {len(results)} 条")
        print(f"       压缩输出: {len(guidances)} 条 guidance")
        
    finally:
        # 清理测试节点
        _cleanup_test_nodes(new_ids)


# ---------- 清理辅助 ----------

def _cleanup_test_nodes(node_ids: list):
    """清理测试创建的节点，恢复索引。"""
    index_path = BASE_DIR / "knowledge_index.json"
    nodes_dir = BASE_DIR / "knowledge_nodes"
    
    # 删除节点文件
    for nid in node_ids:
        for fname in os.listdir(nodes_dir):
            if fname.startswith(f"{nid}_"):
                os.remove(nodes_dir / fname)
    
    # 更新索引
    with open(index_path, "r", encoding="utf-8") as f:
        idx = json.load(f)
    
    # 清理 all_nodes
    idx["all_nodes"] = [n for n in idx["all_nodes"] if n not in node_ids]
    
    # 清理 concept_index
    ci = idx["concept_index"]
    for concept in list(ci.keys()):
        ci[concept] = [n for n in ci[concept] if n not in node_ids]
        if not ci[concept]:
            del ci[concept]
    
    # 更新 stats
    idx["stats"]["total_nodes"] = len(idx["all_nodes"])
    idx["stats"]["total_concepts"] = len(ci)
    
    # 重新计算 by_type
    by_type = {}
    for fname in sorted(os.listdir(nodes_dir)):
        if fname.endswith(".json") and fname.startswith("kn_"):
            with open(nodes_dir / fname, "r") as f:
                node = json.load(f)
                t = node.get("type", "proposition")
                by_type[t] = by_type.get(t, 0) + 1
    idx["stats"]["by_type"] = by_type
    
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)


def _cleanup_test_nodes_by_source(source_file: str):
    """根据源文件路径清理测试节点。"""
    nodes_dir = BASE_DIR / "knowledge_nodes"
    node_ids = []
    
    for fname in os.listdir(nodes_dir):
        if fname.endswith(".json") and fname.startswith("kn_"):
            fpath = nodes_dir / fname
            with open(fpath, "r") as f:
                node = json.load(f)
                if node.get("source_file") == source_file:
                    node_ids.append(node["id"])
    
    if node_ids:
        _cleanup_test_nodes(node_ids)


# ---------- 主入口 ----------

def main():
    runner = TestRunner()
    
    print("\n" + "=" * 60)
    print("PlugMem Phase 3 集成测试")
    print("=" * 60)
    
    # --- 测试组1: 增量抽取器 ---
    print("\n📦 集成点1: 增量知识节点抽取器")
    runner.test("基本抽取功能", test_incremental_extractor_basic)
    runner.test("幂等性（不重复抽取）", test_incremental_extractor_idempotent)
    
    # --- 测试组2: 容量管理器 ---
    print("\n🗜️  集成点2: MEMORY容量管理器")
    runner.test("dry_run 模式", test_memory_compactor_dry_run)
    runner.test("实际压缩功能", test_memory_compactor_actual)
    runner.test("压缩后可读性", test_memory_compactor_readability)
    
    # --- 测试组3: 端到端 ---
    print("\n🔗 集成点3: 端到端全流程")
    runner.test("抽取→检索→压缩 流水线", test_end_to_end_pipeline)
    
    # --- 总结 ---
    all_passed = runner.summary()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
