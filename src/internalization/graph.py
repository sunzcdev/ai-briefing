#!/usr/bin/env python3
"""兴趣图谱 — 持久化存储偏好权重，时间衰减"""

import json, os, sys, time
from . import storage

GRAPH_FILE = os.path.expanduser('~/.hermes/data/ai_briefing/interest_graph.json')

DEFAULT_GRAPH = {
    'categories': {},
    'tech_stack': {},
    'keywords': [],
    'last_decay': time.strftime('%Y-%m-%d'),
    'project_ids': []
}

def load():
    """加载兴趣图谱"""
    if os.path.exists(GRAPH_FILE):
        try:
            with open(GRAPH_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_GRAPH)

def save(graph):
    """保存兴趣图谱"""
    os.makedirs(os.path.dirname(GRAPH_FILE), exist_ok=True)
    with open(GRAPH_FILE, 'w') as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

def update_from_analysis(item_id, analysis, project):
    """根据分析结果更新图谱"""
    graph = load()
    now = time.strftime('%Y-%m-%d')

    # 记录项目
    if item_id not in graph['project_ids']:
        graph['project_ids'].append(item_id)

    # 更新 categories — 从分析标签推断
    user_value = analysis.get('user_value', {})
    tags = user_value.get('tags', [])
    for tag in tags:
        if tag not in graph['categories']:
            graph['categories'][tag] = {'weight': 0.0, 'last_active': now, 'projects': []}
        cat = graph['categories'][tag]
        cat['weight'] = min(1.0, cat['weight'] + 0.2)
        cat['last_active'] = now
        if item_id not in cat['projects']:
            cat['projects'].append(item_id)

    # 更新 tech_stack
    lang = project.get('language', '')
    if lang:
        if lang not in graph['tech_stack']:
            graph['tech_stack'][lang] = 0.0
        graph['tech_stack'][lang] = min(1.0, graph['tech_stack'][lang] + 0.15)

    # 更新 keywords — 从 topics + analysis 标签
    topics = project.get('topics', [])
    for topic in topics:
        existing = [k for k in graph['keywords'] if k['keyword'] == topic]
        if existing:
            existing[0]['weight'] = min(1.0, existing[0]['weight'] + 0.1)
            existing[0]['last_active'] = now
        else:
            graph['keywords'].append({'keyword': topic, 'weight': 0.3, 'last_active': now})

    # 从分析标签也加 keywords
    for tag in tags:
        existing = [k for k in graph['keywords'] if k['keyword'] == tag]
        if existing:
            existing[0]['weight'] = min(1.0, existing[0]['weight'] + 0.15)
            existing[0]['last_active'] = now
        else:
            graph['keywords'].append({'keyword': tag, 'weight': 0.25, 'last_active': now})

    apply_decay(graph)
    save(graph)
    return graph

def apply_decay(graph):
    """时间衰减 — 30天无活动减半，60天清除"""
    now = time.time()
    # 处理 categories
    to_remove = []
    for k, v in graph['categories'].items():
        days = 0
        if v.get('last_active'):
            days = (now - time.mktime(time.strptime(v['last_active'], '%Y-%m-%d'))) / 86400
        if days > 60:
            to_remove.append(k)
        elif days > 30:
            v['weight'] *= 0.5
    for k in to_remove:
        del graph['categories'][k]

    # 处理 keywords
    to_remove = []
    for kw in graph['keywords']:
        days = 0
        if kw.get('last_active'):
            days = (now - time.mktime(time.strptime(kw['last_active'], '%Y-%m-%d'))) / 86400
        if days > 60:
            to_remove.append(kw)
        elif days > 30:
            kw['weight'] *= 0.5
    for kw in to_remove:
        graph['keywords'].remove(kw)

    graph['last_decay'] = time.strftime('%Y-%m-%d')

def get_relevance_score(project_name, topics, language):
    """计算一个项目与兴趣图谱的匹配度 (0-1)"""
    graph = load()
    score = 0.0
    max_possible = 0.0

    # 按 topics 匹配（每个 topic 最多 0.3）
    graph_keywords = {kw['keyword']: kw['weight'] for kw in graph['keywords']}
    for topic in topics:
        if topic in graph_keywords:
            score += graph_keywords[topic]
        max_possible += 0.3

    # 按语言匹配（最多 0.5）
    if language in graph['tech_stack']:
        score += graph['tech_stack'][language]
    max_possible += 0.5

    # 按名称关键词匹配（每个匹配最多 0.2）
    name_lower = project_name.lower()
    for kw in graph['keywords']:
        if kw['keyword'].lower() in name_lower:
            score += kw['weight']

    if max_possible == 0:
        return 0.0
    return min(1.0, score / max_possible)


if __name__ == '__main__':
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'show'
    if cmd == 'show':
        print(json.dumps(load(), indent=2, ensure_ascii=False))
    elif cmd == 'score':
        if len(sys.argv) >= 3:
            topics = []
            lang = ''
            if len(sys.argv) >= 5:
                topics = sys.argv[3].split(',')
                lang = sys.argv[4]
            elif len(sys.argv) >= 4:
                topics = sys.argv[3].split(',')
            s = get_relevance_score(sys.argv[2], topics, lang)
            print(f'{s:.2f}')
        else:
            print('用法: graph.py score <project_name> [topic1 topic2 ...]')
    elif cmd == 'add' and len(sys.argv) >= 3:
        # 直接从命令行添加测试标记
        data = json.loads(sys.argv[2])
        g = load()
        g['project_ids'].append('test-' + str(int(time.time())))
        for k, v in data.items():
            g['categories'][k] = {'weight': v, 'last_active': time.strftime('%Y-%m-%d'), 'projects': []}
        save(g)
        print('OK')
    else:
        print(json.dumps(load(), indent=2, ensure_ascii=False))
