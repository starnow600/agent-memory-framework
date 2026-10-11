#!/usr/bin/env python3
"""
深度解读时机判断器
用法: python deep_interpretation_check.py --topic "话题名" [--scenarios path/to/scenarios.json]

返回JSON:
{
  "topic": "输入的话题名",
  "should_deep_interpret": true/false,
  "matched_scenario": "匹配的场景ID（如有）",
  "reason": "判断依据"
}
"""

import json
import argparse
import os
import sys

DEFAULT_SCENARIOS = os.path.join(os.path.dirname(__file__), '..', 'functional', 'deep_interpretation_scenarios.json')

def load_scenarios(path):
    """加载场景库"""
    if not os.path.exists(path):
        # 默认场景库
        return {
            "confirmed": [
                {
                    "id": "holding_related",
                    "name": "持仓/策略直接相关",
                    "keywords": ["持仓", "策略", "量化", "风控", "止损", "建仓", "评分", "引擎", "v5", "v6"],
                    "check_graph": True,
                    "graph_node_types": ["stock", "decision", "tool"]
                }
            ],
            "pending": [
                {
                    "id": "first_time_major",
                    "name": "新话题首次出现且影响大",
                    "keywords": ["重大", "突破", "变革", "首次", "政策"],
                    "check_graph": False,
                    "note": "待积累：观察哪些首次话题后续被证明重要"
                },
                {
                    "id": "contradicts_history",
                    "name": "与历史决策矛盾",
                    "keywords": ["矛盾", "反转", "相反", "不同于"],
                    "check_graph": True,
                    "graph_node_types": ["decision"],
                    "note": "待积累：观察哪些矛盾信号值得展开分析"
                },
                {
                    "id": "multi_topic_resonance",
                    "name": "多话题共振",
                    "keywords": ["共振", "同步", "多个话题"],
                    "check_graph": False,
                    "note": "待积累：观察多少个话题指向同方向时值得合并分析"
                },
                {
                    "id": "user_followup",
                    "name": "用户主动追问",
                    "keywords": ["追问", "详细", "为什么", "怎么", "如何"],
                    "check_graph": False,
                    "note": "可立即使用——用户追问即信号"
                }
            ],
            "stats": {
                "confirmed_count": 1,
                "pending_count": 4,
                "total": 5,
                "threshold_for_rule_extraction": 8
            }
        }
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_topic_against_scenarios(topic, scenarios, graph=None):
    """检查话题是否匹配任何深度解读场景"""
    topic_lower = topic.lower()
    
    # 先检查confirmed场景
    for scenario in scenarios.get('confirmed', []):
        matched = False
        
        # 关键词匹配
        for kw in scenario.get('keywords', []):
            if kw in topic_lower:
                matched = True
                break
        
        # 图谱检查（如果需要）
        if matched and scenario.get('check_graph') and graph:
            # 进一步验证图谱中是否有相关节点
            for nid, node in graph.get('nodes', {}).items():
                if node.get('type') in scenario.get('graph_node_types', []):
                    aliases = [a.lower() for a in node.get('aliases', [])]
                    if topic_lower in aliases or any(alias in topic_lower for alias in aliases):
                        return {
                            'should_deep_interpret': True,
                            'matched_scenario': scenario['id'],
                            'scenario_name': scenario['name'],
                            'reason': f'匹配已确认场景：{scenario["name"]}'
                        }
        elif matched:
            return {
                'should_deep_interpret': True,
                'matched_scenario': scenario['id'],
                'scenario_name': scenario['name'],
                'reason': f'匹配已确认场景：{scenario["name"]}'
            }
    
    # 检查pending场景（仅作为参考，不强制深度解读）
    for scenario in scenarios.get('pending', []):
        for kw in scenario.get('keywords', []):
            if kw in topic_lower:
                return {
                    'should_deep_interpret': False,  # pending场景不强制
                    'matched_scenario': scenario['id'],
                    'scenario_name': scenario['name'],
                    'reason': f'匹配待观察场景：{scenario["name"]}（{scenario.get("note", "")}）',
                    'suggestion': '可考虑深度解读，但非强制'
                }
    
    return {
        'should_deep_interpret': False,
        'matched_scenario': None,
        'reason': '未匹配任何深度解读场景，保持标题模式'
    }

def main():
    parser = argparse.ArgumentParser(description='深度解读时机判断')
    parser.add_argument('--topic', required=True, help='话题名称')
    parser.add_argument('--scenarios', default=DEFAULT_SCENARIOS, help='场景库JSON路径')
    parser.add_argument('--graph', default=None, help='knowledge_graph.json路径（可选）')
    args = parser.parse_args()
    
    scenarios = load_scenarios(args.scenarios)
    
    # 如果指定了图谱，加载
    graph = None
    if args.graph and os.path.exists(args.graph):
        with open(args.graph, 'r', encoding='utf-8') as f:
            graph = json.load(f)
    
    result = check_topic_against_scenarios(args.topic, scenarios, graph)
    result['topic'] = args.topic
    result['stats'] = scenarios.get('stats', {})
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
