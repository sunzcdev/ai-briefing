#!/usr/bin/env python3
"""LWF LLM 精选包装 — 读取 collect.json，调用 curate，合并原始字段后输出 digest.json"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.curator import curate

collect_path = 'data/collect.json'
if not os.path.exists(collect_path):
    print("[lwf] 无采集结果，跳过精选")
    sys.exit(1)

with open(collect_path) as f:
    collect = json.load(f)

data = collect.get('data', {})
projects = data.get('projects', [])
news = data.get('news', [])
mode = data.get('mode', 'daily')

# 建立 name -> item 索引（保留原始 url/description/stars）
project_index = {p['name']: p for p in projects if p.get('name')}
news_index = {n['name']: n for n in news if n.get('name')}

print(f"[lwf] LLM 精选: {len(projects)} 项目, {len(news)} 新闻", flush=True)
curated = curate(projects, news, mode)

def merge_originals(curated_list, index):
    """合并 LLM 评论与原始字段"""
    result = []
    for item in (curated_list or []):
        name = item.get('name', '')
        orig = index.get(name, {})
        merged = {
            'name': name,
            'comment': item.get('comment', ''),
            'url': orig.get('url', '#'),
            'description': orig.get('description', ''),
            'stars': orig.get('stars', 0),
        }
        result.append(merged)
    return result

if curated:
    digest = {
        "workflow": "ai-briefing",
        "step_id": "digest",
        "timestamp": collect.get('timestamp'),
        "data": {
            "projects": merge_originals(curated.get('projects', []), project_index),
            "news": merge_originals(curated.get('news', []), news_index),
            "mode": mode
        },
        "meta": {"runner": "gha", "status": "success"}
    }
    print(f"[lwf] LLM 精选完成: {len(digest['data']['projects'])} 项目, {len(digest['data']['news'])} 新闻", flush=True)
else:
    digest = {
        "workflow": "ai-briefing",
        "step_id": "digest",
        "timestamp": collect.get('timestamp'),
        "data": {"projects": [], "news": [], "mode": mode},
        "meta": {"runner": "gha", "status": "fallback"}
    }
    print("[lwf] LLM 精选返回空", flush=True)

os.makedirs('data', exist_ok=True)
with open('data/digest.json', 'w') as f:
    json.dump(digest, f, ensure_ascii=False, indent=2)
