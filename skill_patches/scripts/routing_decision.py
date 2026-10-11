#!/usr/bin/env python3
"""
路由决策脚本 v1.0
用途：任务开始时运行，匹配skill映射表，输出路由决策卡，写入route_log
输入：sys.argv[1] = 任务描述（字符串）
输出：路由决策卡（stdout）+ 追加写入 route_log.jsonl
"""

import json
import sys
import os
from datetime import datetime

# 路径配置
# 项目根目录：/Coze/Drive/杨小壶/所有对话/主对话/
_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

# 映射表：优先 skill_patches/ 下，其次 harness/ 下
_MAP_CANDIDATES = [
    os.path.join(_PROJECT_ROOT, 'skill_patches', 'skill_scenario_map.json'),
    os.path.join(_PROJECT_ROOT, 'harness', 'skill_scenario_map.json'),
]
MAP_PATH = None  # 运行时在 load_map() 中动态确定

# 日志路径：统一到 harness/route_log.jsonl
LOG_PATH = os.path.join(_PROJECT_ROOT, 'harness', 'route_log.jsonl')

def load_map():
    """加载场景映射表（按优先级搜索多个候选路径）"""
    global MAP_PATH
    for candidate in _MAP_CANDIDATES:
        if os.path.exists(candidate):
            MAP_PATH = candidate
            with open(candidate, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

def match_scenarios(task_desc, scenarios):
    """关键词匹配，返回匹配结果列表（按匹配度排序）"""
    results = []
    task_lower = task_desc.lower()
    
    for scenario in scenarios:
        matched_keywords = []
        for kw in scenario.get('keywords', []):
            if kw.lower() in task_lower:
                matched_keywords.append(kw)
        
        if matched_keywords:
            results.append({
                'id': scenario['id'],
                'skill': scenario['skill'],
                'matched_keywords': matched_keywords,
                'match_count': len(matched_keywords),
                'match_strength': scenario.get('match_strength', 'unknown'),
                'execution': scenario.get('execution', 'unknown'),
                'note': scenario.get('note', '')
            })
    
    # 按匹配关键词数量降序
    results.sort(key=lambda x: x['match_count'], reverse=True)
    return results

def check_composition(task_desc, compositions):
    """检查是否命中组合模式"""
    task_lower = task_desc.lower()
    for comp in compositions:
        if comp['pattern'].lower() in task_lower or comp['trigger'].lower() in task_lower:
            return comp
    return None

def generate_card(task_desc, matches, composition, timestamp):
    """生成路由决策卡"""
    lines = []
    lines.append(f"[路由决策 {timestamp}]")
    lines.append(f"任务摘要: {task_desc[:80]}{'...' if len(task_desc) > 80 else ''}")
    
    if composition:
        lines.append(f"命中组合模式: {composition['pattern']}")
        lines.append(f"执行序列: {' → '.join(composition['sequence'])}")
        if composition.get('planning_ref'):
            lines.append(f"参考planning: {composition['planning_ref']}")
        if composition.get('note'):
            lines.append(f"注意事项: {composition['note']}")
        lines.append(f"执行路径: 组合模式（见上方序列）")
    elif matches:
        best = matches[0]
        lines.append(f"匹配skill: {best['skill']}")
        lines.append(f"匹配关键词: {', '.join(best['matched_keywords'])}")
        lines.append(f"匹配强度: {best['match_strength']}")
        lines.append(f"执行路径: {best['execution']}")
        if best.get('note'):
            lines.append(f"注意事项: {best['note']}")
        if len(matches) > 1:
            alt_skills = [m['skill'] for m in matches[1:3]]
            lines.append(f"备选skill: {', '.join(alt_skills)}")
    else:
        lines.append("匹配skill: 无强匹配")
        lines.append("执行路径: 主session直接执行（通用工具）")
    
    return '\n'.join(lines)

def write_log(task_desc, card, matches, composition, timestamp):
    """追加写入route_log.jsonl（格式与harness/CONFIG.md对齐）"""
    log_entry = {
        'ts': datetime.now().isoformat(timespec='seconds'),
        'scenario': 'skill_routing_decision',
        'chosen': matches[0]['skill'] if matches else 'main-direct',
        'fallback_used': len(matches) > 1 if matches else False,
        'success': True,
        'latency_ms': 0,
        'note': (
            f"task={task_desc[:80]}; "
            f"keywords={matches[0]['matched_keywords'] if matches else []}; "
            f"composition={composition['pattern'] if composition else None}"
        ),
    }

    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception:
        pass  # 日志写入失败不影响主流程

def write_skip(task_desc, reason, timestamp):
    """记录跳过路由的日志（格式与harness/CONFIG.md对齐）"""
    log_entry = {
        'ts': datetime.now().isoformat(timespec='seconds'),
        'scenario': 'skill_routing_decision',
        'chosen': 'skip',
        'fallback_used': False,
        'success': True,
        'latency_ms': 0,
        'note': f"skip_reason={reason}; task={task_desc[:80]}",
    }
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception:
        pass  # 日志写入失败不影响主流程
    print(f"[路由决策 {timestamp}] 跳过路由: {reason}")

def main():
    if len(sys.argv) < 2:
        print("[路由决策] 错误：缺少任务描述参数")
        sys.exit(1)
    
    task_desc = sys.argv[1]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # skip模式：python3 routing_decision.py "任务描述" --skip "原因"
    if '--skip' in sys.argv:
        skip_idx = sys.argv.index('--skip')
        reason = sys.argv[skip_idx + 1] if skip_idx + 1 < len(sys.argv) else '简单任务'
        write_skip(task_desc, reason, timestamp)
        return
    
    # 加载映射表
    map_data = load_map()
    if not map_data:
        # 映射表不存在时记录日志但不崩溃（映射表功能保留但不阻塞）
        print(f"[路由决策 {timestamp}] 映射表不存在，跳过路由匹配")
        write_skip(task_desc, '映射表不存在', timestamp)
        return
    
    scenarios = map_data.get('L1_scenarios', [])
    compositions = map_data.get('L2_compositions', [])
    constraints = map_data.get('L3_constraints', {})
    
    # 匹配
    matches = match_scenarios(task_desc, scenarios)
    composition = check_composition(task_desc, compositions)
    
    # 生成决策卡
    card = generate_card(task_desc, matches, composition, timestamp)
    
    # 追加约束信息
    if matches:
        skill = matches[0]['skill']
        if skill in constraints:
            card += f"\n约束: {constraints[skill]}"
    
    # 输出
    print(card)
    
    # 写入日志
    write_log(task_desc, card, matches, composition, timestamp)

if __name__ == '__main__':
    main()
