"""
PlugMem Phase 3 - MEMORY 容量管理器 (Memory Compactor)

功能：
  扫描 MEMORY.md 的"核心状态锚点"区，识别过期/低优先级条目，
  调用 condenser 的压缩逻辑将其压缩，返回压缩后的全文。
  不直接写文件，安全返回文本供调用方决定是否写入。

设计原则：
  - 保守策略：只压缩明确可压缩的条目，不碰规则区
  - 可读优先：压缩后保留关键信息 + 详情指引
  - dry_run 模式：只报告，不修改
"""

import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path


# ---------- 配置 ----------

# 条目过期阈值（天）
EXPIRED_DAYS = 14

# 可压缩的信号词（出现在条目中则视为可压缩候选）
COMPRESS_SIGNALS = [
    "已完成", "完成于", "已于", "已结项", "已关闭", "已归档",
    "已验证", "验证通过", "已确认", "已上线", "已发布",
    "已废弃", "已淘汰", "已替换", "已升级", "已迁移",
    "已停止", "已终止", "已结束", "已收尾",
    "Phase 2 已完成", "Phase 1 已完成",
]

# 高价值/应保留的信号词（出现则降低压缩优先级或不压缩）
KEEP_SIGNALS = [
    "🔒", "永久", "长期", "核心", "基线", "基准",
    "进行中", "活跃", "跟踪中", "开发中", "待", "计划",
    "P0", "P1", "紧急", "重要", "运行中",
]

# 规则区标题（这些区完全不动）
RULE_SECTION_TITLES = [
    "长期行为规则",
    "行为规则",
    "规则",
    "🔒规则",
    "核心规则",
]


# ---------- 工具函数 ----------

def split_memory_sections(text: str) -> List[Dict]:
    """
    将 MEMORY.md 按二级标题（##）切分为大区块。
    
    Returns:
        列表，每项: {"heading": str, "level": int, "content": str, "start": int, "end": int}
    """
    sections = []
    lines = text.split("\n")
    current_heading = "前言"
    current_level = 0
    current_start = 0
    current_lines = []
    
    def flush(end_idx: int):
        content = "\n".join(current_lines)
        sections.append({
            "heading": current_heading,
            "level": current_level,
            "content": content,
            "start": current_start,
            "end": end_idx,
        })
    
    for i, line in enumerate(lines):
        m = re.match(r'^(#{1,6})\s+(.+?)\s*#*\s*$', line)
        if m and len(m.group(1)) == 2:  # 只按二级标题切分
            flush(i)
            current_level = 2
            current_heading = m.group(2).strip()
            current_start = i
            current_lines = [line]
        else:
            current_lines.append(line)
    
    flush(len(lines))
    return sections


def is_rule_section(heading: str) -> bool:
    """判断一个区块是否是规则区（完全不动）。"""
    for title in RULE_SECTION_TITLES:
        if title in heading:
            return True
    return False


def parse_entries(section_content: str) -> List[Dict]:
    """
    从核心状态锚点区解析条目。
    
    条目格式支持两种：
    1. 三级标题型：### 项目名 后跟若干列表行（整个 h3 块作为一个条目）
    2. 列表型：- **项目A**：状态... （单行列表项）
    
    Returns:
        列表，每项: {
            "full_text": str,       # 条目的完整文本
            "title": str,           # 条目标题
            "lines": List[str],     # 原始行
            "start_line": int,      # 在 section_content 中的起始行（index）
            "end_line": int,        # 在 section_content 中的结束行（index）
            "has_detail_link": bool, # 是否有详情链接指引
        }
    """
    lines = section_content.split("\n")
    entries = []
    current_entry = None
    
    def flush_entry(end_line_idx: int):
        nonlocal current_entry
        if current_entry:
            current_entry["end_line"] = end_line_idx
            current_entry["full_text"] = "\n".join(current_entry["lines"])
            current_entry["content"] = current_entry["full_text"]
            current_entry["has_detail_link"] = any(
                has_detail_link(l) for l in current_entry["lines"]
            )
            # 跳过空条目（只有标题没有内容）
            if len(current_entry["lines"]) >= 1:
                entries.append(current_entry)
            current_entry = None
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 三级标题：开启一个新条目块
        m_h3 = re.match(r'^###\s+(.+?)\s*#*\s*$', line)
        if m_h3:
            flush_entry(i - 1)
            current_entry = {
                "title": m_h3.group(1).strip(),
                "lines": [line],
                "start_line": i,
                "end_line": i,
                "has_detail_link": False,
            }
            i += 1
            continue
        
        # 如果当前在一个 h3 条目块中
        if current_entry is not None:
            # 空行：检查下一行是否还是该条目内容
            if line.strip() == "":
                # 看后面是否还有非空、非标题行属于这个条目
                # 简单处理：空行也归入当前条目，直到遇到下一个 h3 或 h2
                current_entry["lines"].append(line)
                i += 1
                continue
            # 列表行或普通行：归入当前条目
            current_entry["lines"].append(line)
            i += 1
            continue
        
        # 不在 h3 块中，检查是否是独立列表项条目
        m_li = re.match(r'^[-*+]\s+', line)
        if m_li and line.strip() not in ("-", "*", "+"):
            flush_entry(i - 1)
            # 收集连续的列表项（属于同一个条目的情况较少，
            # 通常顶层列表每项就是一个独立条目）
            item_line = line
            title = extract_title_from_list_item(item_line)
            entry_lines = [item_line]
            
            # 检查下一行是否是缩进的子项（属于同一列表项）
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                # 缩进的子列表或续行
                if re.match(r'^\s+[-*+]?\s*', next_line) and next_line.strip():
                    entry_lines.append(next_line)
                    j += 1
                elif next_line.strip() == "":
                    # 空行，可能是条目间隔
                    break
                else:
                    break
            
            current_entry = {
                "title": title,
                "lines": entry_lines,
                "start_line": i,
                "end_line": j - 1,
                "has_detail_link": any(has_detail_link(l) for l in entry_lines),
            }
            flush_entry(j - 1)
            i = j
            continue
        
        # 其他行（空行、普通文本行等）：跳过或结束当前条目
        if line.strip() == "":
            # 空行：如果当前有条目且内容足够，可能是条目间隔
            if current_entry and len([l for l in current_entry["lines"] if l.strip()]) > 1:
                # 检查后面是否还有属于这个条目的内容
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                # 如果下一行是列表缩进或普通文本，继续；如果是标题，结束
                if j < len(lines) and re.match(r'^#{2,}', lines[j]):
                    flush_entry(i - 1)
                    i = j
                    continue
            i += 1
            continue
        
        i += 1
    
    flush_entry(len(lines) - 1)
    
    # 过滤掉标题就直接是规则类的条目（有🔒标记的）
    filtered = []
    for e in entries:
        # 只有一行且是标题本身的 h3，跳过（没有内容）
        non_empty_lines = [l for l in e["lines"] if l.strip()]
        if len(non_empty_lines) <= 1 and e["lines"] and e["lines"][0].startswith("### "):
            continue
        filtered.append(e)
    
    return filtered


def extract_title_from_list_item(line: str) -> str:
    """从列表项中提取标题（加粗文本或冒号前内容）。"""
    # 优先取加粗文本
    bold_match = re.search(r'\*\*(.+?)\*\*', line)
    if bold_match:
        return bold_match.group(1).strip()
    
    # 其次取冒号/破折号前的内容
    for sep in ["：", ":", "——", "——", " - "]:
        if sep in line:
            parts = line.split(sep, 1)
            title = re.sub(r'^[-*+]\s+', '', parts[0]).strip()
            if title:
                return title
    
    # 兜底：去掉列表标记
    return re.sub(r'^[-*+]\s+', '', line).strip()[:30]


def has_detail_link(text: str) -> bool:
    """检查文本中是否有详情指引链接。"""
    patterns = [
        r'decision[/\\]',
        r'wiki[/\\]',
        r'recent_memory[/\\]',
        r'详见',
        r'详情',
        r'参见',
        r'参考',
    ]
    for p in patterns:
        if re.search(p, text):
            return True
    return False


# ---------- 压缩判断 ----------

def evaluate_compressibility(entry: Dict) -> Tuple[bool, str, int]:
    """
    评估一个条目是否可压缩。
    
    Returns:
        (可压缩: bool, 原因: str, 压缩优先级: int)
        优先级越高越应该被压缩（0=不压缩，1~5）
    """
    title = entry.get("title", "")
    content = entry.get("content", "")
    full = title + "\n" + content
    
    # 1. 明确保留信号 → 不压缩
    for sig in KEEP_SIGNALS:
        if sig in full:
            return False, f"含保留信号「{sig}」", 0
    
    # 2. 检查是否有详情指引（有详情链接的才适合压缩）
    if not entry.get("has_detail_link", False):
        return False, "无详情指引链接，压缩后无法追溯", 0
    
    # 3. 检查压缩信号
    compress_score = 0
    matched_signals = []
    for sig in COMPRESS_SIGNALS:
        if sig in full:
            compress_score += 2
            matched_signals.append(sig)
    
    # 4. 日期检查：如果有日期且超过 EXPIRED_DAYS 天
    # （简化：只检查日期格式存在，不做真实日期计算，
    #  真实使用时可接入当前日期做精确判断）
    date_matches = re.findall(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', full)
    if date_matches:
        # 有日期且有完成信号 → 高优先级
        if compress_score > 0:
            compress_score += 2
    
    # 5. 条目长度：太短的不需要压缩，太长的优先压缩
    entry_len = len(full)
    if entry_len < 50:
        compress_score -= 1  # 太短，压缩收益小
    elif entry_len > 300:
        compress_score += 1  # 长条目，压缩收益大
    
    # 判定
    if compress_score >= 2:
        reason = "可压缩：" + "、".join(matched_signals[:2])
        if date_matches:
            reason += f"（有日期标记）"
        priority = min(compress_score, 5)
        return True, reason, priority
    else:
        return False, "未达到压缩阈值", 0


# ---------- 压缩执行 ----------

def compress_entry(entry: Dict) -> str:
    """
    将一个条目压缩为简洁版本。
    
    压缩策略：
      1. 条目标题（作为索引键）+ 状态标签，单行呈现
      2. 提取 1 个核心数据点（如胜率、关键指标）
      3. 保留详情指引链接
      4. 去除冗余描述、背景信息、重复状态
      
    Returns:
        压缩后的条目文本字符串（单行或两行）
    """
    title = entry.get("title", "未命名")
    lines = entry.get("lines", [])
    full = entry.get("content", entry.get("full_text", ""))
    
    # 1. 提取状态
    status = "已归档"
    for sig in COMPRESS_SIGNALS:
        if sig in full:
            status = sig
            break
    
    # 2. 提取详情链接/指引
    detail_link = ""
    # 匹配纯文本路径（如 decision/xxx.md）
    path_matches = re.findall(
        r'(?:详见|详情|参见|参考)[：: ]?\s*([^\s，。、\n]+(?:\.md|\.pdf|\.txt))',
        full
    )
    if path_matches:
        detail_link = f"详见 {path_matches[0]}"
    
    # 再兜底：找任意 .md 路径
    if not detail_link:
        path_matches = re.findall(r'([a-zA-Z0-9_/\-]+\.md)', full)
        if path_matches:
            detail_link = f"详情: {path_matches[0]}"
    
    # 3. 提取核心数据点（数值/关键结论）
    key_point = ""
    # 优先找有数字、百分比、提升/下降等的行
    data_patterns = [
        r'[\d.]+\s*%',  # 百分比
        r'[\d.]+\s*个?\s*(?:节点|项目|模块|规则|方案|版本)',  # 数量
        r'提升[\d.]+',   # 提升
        r'下降[\d.]+',   # 下降
        r'胜率[:：]?\s*[\d.]+',  # 胜率
    ]
    
    for line in lines:
        clean_line = re.sub(r'^[-*+#\s]+', '', line).strip()
        # 跳过状态行、详情行、标题行
        if any(s in clean_line for s in COMPRESS_SIGNALS):
            continue
        if "详情" in clean_line or "详见" in clean_line:
            continue
        if clean_line == title:
            continue
        # 找有关键数据的行
        for pat in data_patterns:
            if re.search(pat, clean_line):
                # 截取关键信息部分
                if len(clean_line) <= 30:
                    key_point = clean_line
                else:
                    # 提取包含数据的片段
                    m = re.search(r'(.{0,10}' + pat + r'.{0,10})', clean_line)
                    if m:
                        key_point = m.group(1).strip()
                break
        if key_point:
            break
    
    # 如果没有数据点，找一句非状态的核心描述
    if not key_point:
        for line in lines:
            clean_line = re.sub(r'^[-*+#\s]+', '', line).strip()
            if not clean_line:
                continue
            if any(s in clean_line for s in COMPRESS_SIGNALS):
                continue
            if "详情" in clean_line or "详见" in clean_line:
                continue
            if clean_line == title:
                continue
            if 8 <= len(clean_line) <= 30:
                key_point = clean_line
                break
    
    # 4. 组装压缩后的条目（尽量压缩到 1-2 行）
    # 格式：- **标题**：状态 | 关键点 | 详情链接
    parts = [f"- **{title}**：{status}"]
    if key_point:
        parts.append(key_point)
    if detail_link:
        parts.append(detail_link)
    
    return " | ".join(parts)


# ---------- 主压缩函数 ----------

def compact_memory(text: str, dry_run: bool = False) -> Dict:
    """
    MEMORY.md 容量管理主入口。
    
    扫描核心状态锚点区，识别可压缩条目，执行压缩。
    
    Args:
        text: MEMORY.md 全文
        dry_run: 只报告不修改
    
    Returns:
        dict: {
            "success": bool,
            "original_size": int,      # 原始字节数
            "compressed_size": int,    # 压缩后字节数
            "bytes_saved": int,        # 节省字节数
            "compression_ratio": float,# 压缩比（压缩后/原始）
            "entries_checked": int,    # 检查的条目数
            "entries_compressed": int, # 压缩的条目数
            "compressed_items": List[Dict], # 被压缩的条目详情
            "output_text": str,        # 压缩后的全文（dry_run时为原文）
            "rule_section_intact": bool, # 规则区是否完整保留
        }
    """
    original_size = len(text.encode("utf-8"))
    
    # 1. 按二级标题切分区块
    sections = split_memory_sections(text)
    
    # 2. 找到核心状态锚点区
    target_section = None
    for sec in sections:
        if "核心状态锚点" in sec["heading"] or "状态锚点" in sec["heading"]:
            target_section = sec
            break
    
    if not target_section:
        return {
            "success": True,
            "original_size": original_size,
            "compressed_size": original_size,
            "bytes_saved": 0,
            "compression_ratio": 1.0,
            "entries_checked": 0,
            "entries_compressed": 0,
            "compressed_items": [],
            "output_text": text,
            "rule_section_intact": True,
            "reason": "未找到「核心状态锚点」区块",
        }
    
    # 3. 验证规则区完整（找到所有规则区，确认我们不会碰它们）
    rule_intact = True
    for sec in sections:
        if is_rule_section(sec["heading"]):
            # 规则区应与目标区不同
            if sec is target_section:
                rule_intact = False
                break
    
    # 4. 解析条目
    entries = parse_entries(target_section["content"])
    
    # 5. 评估每个条目的可压缩性
    compressible = []
    for entry in entries:
        can_compress, reason, priority = evaluate_compressibility(entry)
        if can_compress:
            compressible.append({
                "entry": entry,
                "reason": reason,
                "priority": priority,
            })
    
    # 按优先级降序
    compressible.sort(key=lambda x: x["priority"], reverse=True)
    
    # 6. 执行压缩（如果不是 dry_run）
    output_text = text
    compressed_items = []
    
    if not dry_run and compressible:
        # 按行从后往前替换（避免行号偏移）
        section_lines = target_section["content"].split("\n")
        
        # 按起始行号从大到小排序，这样替换时前面的行号不受影响
        sorted_by_line = sorted(
            compressible,
            key=lambda x: x["entry"]["start_line"],
            reverse=True
        )
        
        for item in sorted_by_line:
            entry = item["entry"]
            compressed = compress_entry(entry)
            
            start = entry["start_line"]
            end = entry["end_line"]
            
            # 替换行
            new_lines = compressed.split("\n")
            section_lines[start:end+1] = new_lines
            
            compressed_items.append({
                "title": entry["title"],
                "original_len": len(entry["full_text"]),
                "compressed_len": len(compressed),
                "reason": item["reason"],
                "original_preview": entry["full_text"][:80],
                "compressed_preview": compressed[:80],
            })
        
        # 组装回全文
        new_section_content = "\n".join(section_lines)
        
        # 用字符串替换更新全文
        output_text = text.replace(
            target_section["content"],
            new_section_content,
            1
        )
    
    else:
        # dry_run 模式下也返回详情
        for item in compressible:
            entry = item["entry"]
            compressed_items.append({
                "title": entry["title"],
                "original_len": len(entry["full_text"]),
                "compressed_len": len(compress_entry(entry)),
                "reason": item["reason"],
                "original_preview": entry["full_text"][:80],
                "compressed_preview": compress_entry(entry)[:80],
            })
    
    compressed_size = len(output_text.encode("utf-8"))
    bytes_saved = original_size - compressed_size
    ratio = compressed_size / max(original_size, 1)
    
    return {
        "success": True,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "bytes_saved": bytes_saved,
        "compression_ratio": round(ratio, 4),
        "entries_checked": len(entries),
        "entries_compressed": len(compressible),
        "compressed_items": compressed_items,
        "output_text": output_text,
        "rule_section_intact": rule_intact,
        "dry_run": dry_run,
    }


# ---------- 独立运行测试 ----------
if __name__ == "__main__":
    sample_memory = """# MEMORY.md

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
    
    print("=" * 60)
    print("MEMORY 容量管理器测试")
    print("=" * 60)
    
    # dry_run 模式
    print("\n【Dry Run 模式】")
    result = compact_memory(sample_memory, dry_run=True)
    print(f"  原始大小: {result['original_size']} 字节")
    print(f"  检查条目: {result['entries_checked']}")
    print(f"  可压缩: {result['entries_compressed']}")
    print(f"  规则区完整: {result['rule_section_intact']}")
    print(f"\n  可压缩条目:")
    for item in result["compressed_items"]:
        print(f"    - {item['title']}: {item['reason']}")
        print(f"      预计: {item['original_len']} → {item['compressed_len']} 字")
    
    # 实际压缩
    print("\n【实际压缩】")
    result = compact_memory(sample_memory, dry_run=False)
    print(f"  原始: {result['original_size']} 字节")
    print(f"  压缩后: {result['compressed_size']} 字节")
    print(f"  节省: {result['bytes_saved']} 字节 ({(1-result['compression_ratio'])*100:.1f}%)")
    print(f"  压缩条目: {result['entries_compressed']}/{result['entries_checked']}")
    print(f"  规则区完整: {result['rule_section_intact']}")
    
    # 验证规则区没动
    print("\n【规则区验证】")
    if "### 决策记录规则\n- 重大决策必须在24小时内写入 decision log" in result["output_text"]:
        print("  ✅ 规则区内容完整保留")
    else:
        print("  ❌ 规则区被意外修改！")
