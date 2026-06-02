#!/usr/bin/env python3
"""LWF 采集包装 — 调用 ai-briefing 核心采集逻辑，输出 LWF 统一格式"""
import sys, os, json
from datetime import datetime, timezone

# ai-briefing 核心库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.collector.ai_briefing_collector import collect_projects, collect_news, _dedup

mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'

projects = collect_projects(mode)
news = collect_news(mode)
all_items = _dedup(projects + [n for n in news if n.get('_kind') != 'noise'])

output = {
    "workflow": "ai-briefing",
    "step_id": "collect",
    "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    "data": {"projects": projects, "news": news, "mode": mode, "total": len(all_items)},
    "meta": {"runner": "gha", "status": "success"}
}

os.makedirs('data', exist_ok=True)
with open('data/collect.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"[lwf] 采集完成: {len(projects)} 项目, {len(news)} 新闻")
