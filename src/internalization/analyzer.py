#!/usr/bin/env python3
"""双维分析 — 构建 LLM 分析 prompt + 解析结果"""

import json, os, sys, time
from . import storage

def build_analysis_prompt(project):
    """根据采集到的项目数据，生成分析 prompt"""
    name = project.get('name', 'unknown')
    url = project.get('url', '')
    desc = project.get('description', '')
    lang = project.get('language', '')
    topics = project.get('topics', [])
    stars = project.get('stars', 0)
    license_name = project.get('license', '')
    recent_commits = project.get('recent_commits', [])
    last_commit_date = recent_commits[0]['date'] if recent_commits else '未知'
    releases = project.get('releases', [])

    topics_str = ', '.join(topics) if topics else '无'
    commits_summary = '\n'.join(f"  - {c['date']} {c['message']}" for c in recent_commits[:3]) if recent_commits else '  无近期提交'

    return f"""分析以下项目对用户的价值。

## 项目信息
- 名称: {name}
- URL: {url}
- 描述: {desc}
- 语言: {lang}
- Star: {stars}
- License: {license_name}
- 标签: {topics_str}
- 最后提交: {last_commit_date}
- 最近提交:
{commits_summary}

## 用户画像
用户是一名 AI 工程师和独立开发者，关注：AI/LLM、开源工具、开发者体验、本地推理、agent 系统。用 Python/TypeScript/Rust。

## 分析维度

### 1. 对用户的价值 (1-10)
评估标准：技术栈匹配度、解决的实际问题、兴趣领域相关性、是否可用于自有项目。
输出格式：分数 + 一句话理由 + 标签（如"技术栈匹配"、"解决具体问题"、"灵感启发"）

### 2. 对 Hermes 的价值 (1-10)
评估标准：是否适合日报写作、可作为案例分享、知识库素材、可复用的经验。
输出格式：分数 + 一句话理由 + 标签（如"写作素材"、"案例可复用"）

## 输出格式
严格按 JSON 输出，不要多余文字：
```json
{{
  "user_value": {{"score": 8, "reason": "...", "tags": ["标签1", "标签2"]}},
  "hermes_value": {{"score": 7, "reason": "...", "tags": ["标签1"]}}
}}
```"""

def parse_analysis_response(response_text):
    """解析 LLM 响应中的 JSON"""
    import re
    # 尝试提取 ```json ... ``` 中的内容
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 直接尝试解析整段
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass
    # 尝试找第一个 { 到最后一个 }
    m = re.search(r'\{.*\}', response_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {'user_value': {'score': 5, 'reason': '解析失败', 'tags': []},
            'hermes_value': {'score': 5, 'reason': '解析失败', 'tags': []}}


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        cmd = 'prompt'
    else:
        cmd = sys.argv[1]

    if cmd == 'prompt':
        # 从 stdin 或参数读取项目数据
        if not sys.stdin.isatty():
            data = json.load(sys.stdin)
        else:
            data = {'name': 'example/repo', 'url': 'https://github.com/example/repo', 'description': '示例项目', 'language': 'Python', 'topics': ['ai', 'llm'], 'stars': 100, 'recent_commits': [], 'releases': []}
        print(build_analysis_prompt(data))
    elif cmd == 'parse':
        text = sys.stdin.read()
        result = parse_analysis_response(text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f'用法: {sys.argv[0]} [prompt|parse]')
