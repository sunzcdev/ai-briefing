#!/usr/bin/env python3
"""LWF LLM 精选包装 — 读取 collect.json，调用 curate，输出 digest.json"""
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

print(f"[lwf] LLM 精选: {len(projects)} 项目, {len(news)} 新闻", flush=True)
curated = curate(projects, news, mode)

if curated:
    digest = {
        "workflow": "ai-briefing",
        "step_id": "digest",
        "timestamp": collect.get('timestamp'),
        "data": {
            "projects": curated.get('projects', []),
            "news": curated.get('news', []),
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
