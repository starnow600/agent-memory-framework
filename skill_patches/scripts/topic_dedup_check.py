#!/usr/bin/env python3
"""
话题追踪推送去重检查器
用法: python topic_dedup_check.py --topic "话题名" [--graph path/to/knowledge_graph.json]

返回JSON:
{
  "topic": "输入的话题名",
  "matched_nodes": ["匹配的图谱节点ID"],
  "has_existing_answer": true/false,
  "answer_summary": "已有结论摘要（如有）",
  "recommendation": "skip|annotate|deliver",
  "reason": "判断依据"
}
"""

import json
import argparse
import os
import sys

DEFAULT_GRAPH = os.path.join(os.path.dirname(__file__), '..', '..', 'recent_memory', 'knowledge_graph.json')

def load_graph(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def match_topic_to_nodes(topic, graph):
    """通过名称、别名匹配话题到图谱节点"""
    topic_lower = topic.lower().strip()
    matches = []
    
    for nid, node in graph['nodes'].items():
        # 检查节点ID
        if topic_lower in nid.lower():
            matches.append(nid)
            continue
        
        # 检查别名
        aliases = [a.lower() for a in node.get('aliases', [])]
        if topic_lower in aliases:
            matches.append(nid)
            continue
        
        # 检查话题是否包含在别名中（部分匹配）
        for alias in aliases:
            if alias in topic_lower or topic_lower in alias:
                matches.append(nid)
                break
    
    return matches

def check_related_decisions(node_id, graph):
    """检查与节点相关的决策/结论节点"""
    related = []
    for rel in graph['relations']:
        if rel.get('source') == node_id or rel.get('target') == node_id:
            other = rel['target'] if rel['source'] == node_id else rel['source']
            if other in graph['nodes']:
                other_node = graph['nodes'][other]
                if other_node.get('type') in ('decision', 'project') and other_node.get('narrative_digest'):
                    related.append({
                        'node_id': other,
                        'type': other_node['type'],
                        'digest': other_node['narrative_digest'][:200]
                    })
    return related

def check_existing_answer(node_id, graph):
    """检查节点是否有已有结论（narrative_digest或相关决策）"""
    node = graph['nodes'].get(node_id, {})
    
    # 检查节点自身是否有结论摘要
    digest = node.get('narrative_digest', '')
    has_digest = len(digest) > 20  # 有实质性内容
    
    # 检查相关决策节点
    related_decisions = check_related_decisions(node_id, graph)
    
    return {
        'has_digest': has_digest,
        'digest_preview': digest[:200] if has_digest else '',
        'related_decisions': related_decisions,
        'node_type': node.get('type', 'unknown'),
        'node_created': node.get('created', 'unknown')
    }

def main():
    parser = argparse.ArgumentParser(description='话题追踪推送去重检查')
    parser.add_argument('--topic', required=True, help='待推送的话题名称')
    parser.add_argument('--graph', default=DEFAULT_GRAPH, help='knowledge_graph.json路径')
    args = parser.parse_args()
    
    if not os.path.exists(args.graph):
        print(json.dumps({
            'topic': args.topic,
            'matched_nodes': [],
            'has_existing_answer': False,
            'answer_summary': '',
            'recommendation': 'deliver',
            'reason': f'图谱文件不存在: {args.graph}'
        }, ensure_ascii=False, indent=2))
        return
    
    graph = load_graph(args.graph)
    
    # Step 1: 匹配话题到图谱节点
    matched = match_topic_to_nodes(args.topic, graph)
    
    if not matched:
        print(json.dumps({
            'topic': args.topic,
            'matched_nodes': [],
            'has_existing_answer': False,
            'answer_summary': '',
            'recommendation': 'deliver',
            'reason': '图谱中无匹配节点，视为新信息'
        }, ensure_ascii=False, indent=2))
        return
    
    # Step 2: 检查每个匹配节点是否有已有结论
    answer_details = []
    has_answer = False
    summaries = []
    
    for nid in matched:
        check = check_existing_answer(nid, graph)
        answer_details.append({'node_id': nid, **check})
        
        if check['has_digest']:
            has_answer = True
            summaries.append(f"[{nid}] {check['digest_preview']}")
        
        for dec in check['related_decisions']:
            has_answer = True
            summaries.append(f"[{dec['node_id']}→{nid}] {dec['digest']}")
    
    # Step 3: 生成建议
    if has_answer:
        recommendation = 'annotate'  # 默认标注，不跳过
        reason = f'图谱中找到{len(matched)}个匹配节点，其中{len(summaries)}个有已有结论'
    else:
        recommendation = 'deliver'
        reason = f'图谱中找到{len(matched)}个匹配节点，但均无实质性结论'
    
    result = {
        'topic': args.topic,
        'matched_nodes': matched,
        'has_existing_answer': has_answer,
        'answer_summary': '; '.join(summaries[:3]),  # 最多展示3条
        'recommendation': recommendation,
        'answer_details': answer_details,
        'reason': reason
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
