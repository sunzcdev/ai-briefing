#!/usr/bin/env python3
"""精选排序 — 对采集到的项目按兴趣图谱排序+剪枝"""

import json, sys
from . import graph as ig

# 匹配度阈值
MIN_SCORE = 0.3       # 低于此值→"其他"
FEATURED_THRESHOLD = 0.8  # 高于此值→加"🎯 为你推荐"标签

def select_and_rank(items, interest_graph=None):
    """对项目列表排序，输出带得分的精选列表"""
    if interest_graph is None:
        interest_graph = ig.load()

    # 为每个项目计算得分
    scored = []
    other = []
    for item in items:
        name = item.get('name', '')
        topics = item.get('topics', [])
        language = item.get('language', '')
        score = ig.get_relevance_score(name, topics, language)
        entry = dict(item)
        entry['_interest_score'] = round(score, 2)
        entry['_featured'] = score >= FEATURED_THRESHOLD
        if score >= MIN_SCORE:
            scored.append(entry)
        else:
            other.append(entry)

    # 按得分降序
    scored.sort(key=lambda x: x['_interest_score'], reverse=True)
    other.sort(key=lambda x: x.get('stars', 0), reverse=True)

    return {
        'recommended': scored,
        'other': other,
        'summary': {
            'total': len(items),
            'recommended': len(scored),
            'other': len(other)
        }
    }


if __name__ == '__main__':
    data = json.load(sys.stdin) if not sys.stdin.isatty() else []
    if not data:
        print(json.dumps({'recommended': [], 'other': [], 'summary': {'total': 0, 'recommended': 0, 'other': 0}}, indent=2))
    else:
        result = select_and_rank(data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
