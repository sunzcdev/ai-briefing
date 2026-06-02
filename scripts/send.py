#!/usr/bin/env python3
"""LWF 发信包装 — 读取 LLM 精选结果，渲染 HTML 并发送"""
import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

digest_path = 'data/digest.json'
if not os.path.exists(digest_path):
    print("[lwf] 无精选结果，跳过发信")
    sys.exit(0)

with open(digest_path) as f:
    digest = json.load(f)

from src.digest.send_ai_briefing import send
from src.config import DEFAULT_TO_EMAIL

to_email = os.environ.get('EMAIL_TO', DEFAULT_TO_EMAIL)
subject = f"AI 新玩意简报 {datetime.now().strftime('%Y-%m-%d')}"

data = digest.get('data', {})
projects = data.get('projects', [])
news = data.get('news', [])

html_parts = ['<h2>📦 精选项目</h2>']
if projects:
    for p in projects:
        name = p.get('name', '')
        comment = p.get('comment', '')
        url = p.get('url', '#')
        html_parts.append(f'<p>🔹 <a href="{url}"><b>{name}</b></a> — {comment}</p>')
else:
    html_parts.append('<p>暂无精选项目</p>')

if news:
    html_parts.append('<h2>🔥 热点事件</h2>')
    for n in news:
        name = n.get('name', '')
        comment = n.get('comment', '')
        url = n.get('url', '#')
        html_parts.append(f'<p>🔹 <a href="{url}"><b>{name}</b></a> — {comment}</p>')

html = '<html><body>' + ''.join(html_parts) + '</body></html>'

try:
    send(html, subject, to_email)
    print(f"[lwf] 邮件已发送至 {to_email}")
except Exception as e:
    print(f"[lwf] 发信失败: {e}")
    sys.exit(1)
