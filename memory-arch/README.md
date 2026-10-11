# PlugMem 记忆架构

> PlugMem（Pluggable Memory Architecture）—— 可插拔式记忆架构改造项目，将原始文本检索升级为知识节点化的分层记忆系统。

---

## 目录结构

```
memory-arch/
├── knowledge_index.json          # 概念路由索引（175个概念 → 44个节点）
├── knowledge_nodes/              # 知识节点文件（44个 .json）
│   ├── kn_001_决策日志.json
│   ├── kn_002_决策日志.json
│   └── ...
├── hybrid_retriever.py           # Phase 2 - 混合检索器（概念路由 + 语义兜底）
├── condenser.py                  # Phase 2 - 推理压缩模块（检索结果→guidance）
├── incremental_extractor.py      # Phase 3 - 增量知识节点抽取器 ✨
├── memory_compactor.py           # Phase 3 - MEMORY 容量管理器 ✨
├── integration_test.py           # Phase 3 - 集成测试 ✨
├── generate_nodes.py             # Phase 1 - 节点生成脚本
├── test_memory_pipeline.py       # Phase 2 - 流水线测试
├── phase1_report.md              # Phase 1 执行报告
├── phase2_report.md              # Phase 2 执行报告
├── retrieval_quality_test.md     # 检索质量测试报告
├── phase2_test_results.json      # Phase 2 测试数据
└── README.md                     # 本文档
```

---

## 各模块功能与调用方式

### 1. 混合检索器 (`hybrid_retriever.py`)

两路检索融合：概念路由（高精度快路径）+ 语义搜索兜底（高召回补全）。

**调用方式：**
```python
from hybrid_retriever import hybrid_retrieve

results = hybrid_retrieve("记忆检索的流程是怎样的", max_results=3)
for r in results:
    print(f"[{r['source_type']}|{r['confidence']:.2f}] {r['source_ref']} {r['content']}")
```

**输出结构：**
```python
{
    "content": str,           # 节点命题内容
    "source_type": str,       # "knowledge_node" 或 "semantic"
    "node_id": str,           # 节点ID (如 kn_015)
    "confidence": float,      # 置信度 0-1
    "matched_concepts": list, # 匹配到的概念列表
    "source_ref": str,        # 溯源引用标记，如 [kn_015]
    "source_file": str,       # 源文件路径
    "source_anchor": str      # 源锚点
}
```

### 2. 推理压缩模块 (`condenser.py`)

将检索结果压缩为 3-5 条 task-adaptive actionable guidance，每条附引用标记。

**调用方式：**
```python
from hybrid_retriever import hybrid_retrieve
from condenser import condense, format_guidance_list

results = hybrid_retrieve("高风险操作校验规则")
guidances = condense(results, "高风险操作校验规则")
print(format_guidance_list(guidances))
```

**核心指标：**
- 平均压缩比：33.9%（输入 132.5 tokens → 输出 44.9 tokens）
- 单条 guidance 控制在 30 字以内
- 保留 [kn_xxx] 溯源引用

### 3. 增量知识节点抽取器 (`incremental_extractor.py`) ✨ Phase 3 新增

从新的 decision log / tool experience / wiki 页面中，用规则方法提取知识节点，自动写入并更新索引。

**核心特性：**
- **纯规则抽取**：不依赖 LLM，基于关键词命中 + 段落结构分析
- **幂等设计**：同一源文件不会被重复抽取
- **向后兼容**：只新增文件、更新索引，不修改已有节点
- **自动分配ID**：从现有最大ID递增

**调用方式：**
```python
from incremental_extractor import incremental_extract

# 读取 markdown 文件内容
with open("recent_memory/decision/new_decision.md", "r") as f:
    text = f.read()

result = incremental_extract(
    text=text,
    source_file="recent_memory/decision/new_decision.md"
)

print(f"新增 {result['new_nodes_count']} 个节点: {result['new_node_ids']}")
print(f"跳过原因: {result['reason']}" if result['skipped'] else "抽取成功")
```

**返回结构：**
```python
{
    "success": bool,
    "skipped": bool,           # 是否因为幂等被跳过
    "reason": str,             # 原因说明
    "new_nodes_count": int,    # 新增节点数量
    "new_node_ids": List[str], # 新增节点ID列表
    "nodes": List[Dict],       # 新增的完整节点数据
}
```

**抽取逻辑：**
1. 解析 markdown 文档结构（按标题切分段落）
2. 评估每个段落的知识价值（标题关键词 + 正文关键词密度 + 列表项 + 加粗文本）
3. 从高价值段落中提取候选命题（列表项优先 → 加粗文本 → 关键词句子）
4. 去重 + 评分排序，取 Top 1-5
5. 生成概念标签（固定词库匹配 + 标题短语 + 核心名词短语）

### 4. MEMORY 容量管理器 (`memory_compactor.py`) ✨ Phase 3 新增

扫描 MEMORY.md 的"核心状态锚点"区，识别过期/低优先级条目并压缩，**不直接写文件**，安全返回文本供调用方决定。

**核心特性：**
- **保守策略**：只压缩明确可压缩的条目，规则区（## 长期行为规则）完全不动
- **可读优先**：压缩后保留标题 + 状态 + 关键数据 + 详情指引
- **dry_run 模式**：只报告可压缩条目，不实际修改
- **安全返回**：返回压缩后的全文，调用方决定是否写入

**调用方式：**
```python
from memory_compactor import compact_memory

# 读取 MEMORY.md
with open("MEMORY.md", "r") as f:
    text = f.read()

# 先 dry_run 看看
preview = compact_memory(text, dry_run=True)
print(f"可压缩 {preview['entries_compressed']} 个条目，预计节省 {preview['bytes_saved']} 字节")

# 确认后执行压缩
result = compact_memory(text, dry_run=False)

# 调用方决定是否写入
if result["rule_section_intact"] and result["bytes_saved"] > 0:
    with open("MEMORY.md", "w") as f:
        f.write(result["output_text"])
```

**压缩判定规则：**
| 条件 | 优先级 |
|------|--------|
| 含「已完成/已验证/已结项」等信号 + 有详情链接 | 高（优先压缩） |
| 含「🔒/P0/P1/进行中/开发中」等保留信号 | 不压缩 |
| 无详情指引链接 | 不压缩（无法追溯） |

---

## 使用示例

### 示例1：增量抽取新决策文档

```bash
cd memory-arch
python -c "
from incremental_extractor import incremental_extract

# 假设有一篇新的决策文档
doc = '''
# 关于Wiki消费机制的决策

## 决策内容
- Wiki消费应采用三层评估机制：可用性评分 → 复用收益 → 维护成本
- 消费率递减规律：前2周使用率80%，1个月后降至30%
- 高价值Wiki应编译为知识节点
'''

result = incremental_extract(doc, 'recent_memory/decision/wiki_consumption.md')
print(f'新增节点: {result[\"new_node_ids\"]}')
for n in result['nodes']:
    print(f'  [{n[\"id\"]}] {n[\"proposition\"][:50]}...')
"
```

### 示例2：定期压缩 MEMORY.md

```python
from pathlib import Path
from memory_compactor import compact_memory

memory_path = Path("MEMORY.md")
text = memory_path.read_text()

# dry_run 检查
preview = compact_memory(text, dry_run=True)
print(f"可压缩: {preview['entries_compressed']} 个条目")
for item in preview["compressed_items"]:
    print(f"  - {item['title']}: {item['reason']}")

# 确认压缩
if preview["entries_compressed"] > 0:
    result = compact_memory(text, dry_run=False)
    # 安全校验
    assert result["rule_section_intact"], "规则区被意外修改！"
    
    # 备份后写入
    backup = memory_path.with_suffix(".md.bak")
    backup.write_text(text)
    memory_path.write_text(result["output_text"])
    print(f"压缩完成: 节省 {result['bytes_saved']} 字节 ({(1-result['compression_ratio'])*100:.1f}%)")
```

### 示例3：端到端流水线

```python
from incremental_extractor import incremental_extract
from hybrid_retriever import hybrid_retrieve
from condenser import condense_and_format

# 1. 新文档入库
with open("new_decision.md") as f:
    result = incremental_extract(f.read(), "new_decision.md")
print(f"新增 {result['new_nodes_count']} 个知识节点")

# 2. 检索相关知识
results = hybrid_retrieve("风控校验规则", max_results=3)

# 3. 压缩为可执行指导
guidance = condense_and_format(results, "风控校验规则")
print(guidance)
```

---

## 当前规模统计

| 指标 | 数值 |
|------|------|
| 知识节点总数 | 44 |
| 概念标签总数 | 175 |
| 覆盖源文件 | ~30 个 |
| proposition / prescription | 19 / 25 |
| 概念路由平均命中 | ~2.3 个概念/查询 |
| 混合检索准确率 | 约 80%（概念路由优先） |
| 推理压缩比 | 33.9%（平均） |

---

## Phase 路线图

### ✅ Phase 1: 知识节点化 + 概念路由索引
- 44个知识节点结构化存储
- 概念路由索引（knowledge_index.json）
- 175个概念标签

### ✅ Phase 2: 混合检索 + 推理压缩层
- hybrid_retriever.py：概念路由 + 语义兜底 双路检索
- condenser.py：检索结果 → 3-5条 actionable guidance
- 压缩比 33.9%，保留溯源引用

### ✅ Phase 3: 工作流集成（当前）
- **incremental_extractor.py**：增量知识节点抽取器（规则方法，幂等）
- **memory_compactor.py**：MEMORY 容量管理器（保守压缩，dry_run 安全）
- **integration_test.py**：6个集成测试全部通过
- 将记忆架构能力嵌入实际工作流

### 🔮 Phase 4: Episodic 结构化溯源（规划中）
- 情节记忆结构化（时间线 + 因果链）
- narrative_links 双向链接网络
- 记忆演化追踪（节点版本 + 变更历史）
- 自动记忆健康度报告
