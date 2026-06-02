#!/usr/bin/env python3
"""
LLM 精选 + 点评模块
用硅基流动 Qwen2.5-32B（免费）从候选项目中挑出 7 优质项目 + 3 热点事件。
"""
import json, os, sys
from datetime import datetime

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.config import CURATOR_API_KEY, CURATOR_API_URL, CURATOR_MODEL


def _call_llm(prompt, max_tokens=2000):
    if not CURATOR_API_KEY:
        print('[curator] API key not set, skip LLM curation.', file=sys.stderr)
        return None

    import urllib.request as req
    body = json.dumps({
        'model': CURATOR_MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.3,
    }).encode()

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CURATOR_API_KEY}',
    }

    try:
        r = req.Request(CURATOR_API_URL, data=body, headers=headers, method='POST')
        with req.urlopen(r, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data['choices'][0]['message']['content']
    except Exception as e:
        print(f'[curator] API call failed: {e}', file=sys.stderr)
        return None


def _build_prompt(projects, news, mode):
    now = datetime.now().strftime('%Y年%m月%d日')
    projects_text = '\n'.join(
        f'{i+1}. [{p["name"]}]({p["url"]}) ⭐{p.get("stars", 0)} — {p.get("description", "无简介")[:100]}'
        for i, p in enumerate(projects)
    )
    news_text = '\n'.join(
        f'{i+1}. [{n["name"]}]({n["url"]}) — {n.get("description", "无详情")[:100]}'
        for i, n in enumerate(news)
    )

    return f"""你是 AI 领域资深编辑，任务是为 {now} 的 AI 简报做精选。

## 候选项目（{len(projects)} 个）
{projects_text}

## 候选新闻/事件（{len(news)} 个）
{news_text}

## 要求
从【候选项目】中挑出 **7 个最值得关注的优质项目**（优先 AI/Agent 领域，兼顾国内外、中文项目）。
从【候选新闻】中挑出 **3 个最重要的人工智能热点事件或资讯**。

每个项目/事件用一行中文点评（10-25 字），点出核心价值或亮点。

## 输出格式
严格 JSON 格式，不要多余文字：
{{
  "projects": [
    {{"name": "完整项目名", "comment": "一句话中文点评"}},
    ...
  ],
  "news": [
    {{"name": "标题", "comment": "一句话中文点评"}},
    ...
  ]
}}"""


def curate(projects, news, mode):
    projects = sorted(projects, key=lambda x: x.get('stars', 0), reverse=True)[:30]
    news = sorted(news, key=lambda x: x.get('stars', 0), reverse=True)[:30]

    if not CURATOR_API_KEY:
        print('[curator] No API key, fallback to star ranking.', flush=True)
        return None

    prompt = _build_prompt(projects, news, mode)
    result = _call_llm(prompt)
    if not result:
        return None

    try:
        json_str = result
        if '```json' in result:
            json_str = result.split('```json')[1].split('```')[0].strip()
        elif '```' in result:
            json_str = result.split('```')[1].split('```')[0].strip()
        parsed = json.loads(json_str)
        if 'projects' not in parsed or 'news' not in parsed:
            raise ValueError('Missing projects or news key')
        return parsed
    except Exception as e:
        print(f'[curator] Parse failed: {e}', file=sys.stderr)
        print(f'[curator] Raw: {result[:500]}', file=sys.stderr)
        return None
