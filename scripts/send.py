#!/usr/bin/env python3
"""LWF 发信包装 — 用 ai_digest_template.html 渲染后通过 QQ SMTP 发送"""
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
from src.config import EMAIL_TO

to_email = EMAIL_TO
now = datetime.now()
weekdays = ['一', '二', '三', '四', '五', '六', '日']
subject = f"AI 新玩意简报 {now.strftime('%Y-%m-%d')}"

data = digest.get('data', {})
projects = data.get('projects', [])
news = data.get('news', [])

# ── 读取已有模板 ──
template_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'src', 'digest', 'ai_digest_template.html'
)
with open(template_path, encoding='utf-8') as f:
    html = f.read()

# ── 替换基础信息 ──
replacements = {
    '##TITLE##': 'AI 新玩意早报', '##ICON##': '🤖',
    '##DATE##': now.strftime('%Y年%m月%d日'), '##WEEKDAY##': weekdays[now.weekday()],
    '##QUOTE##': 'LLM 精选，AI 圈每日必读',
    '##HEADER_BG##': '#1d1d1f', '##ACCENT##': '#007aff',
    '##FEATURED_BG##': '#f0f7ff', '##FEATURED_BORDER##': '#cce5ff',
}
for k, v in replacements.items():
    html = html.replace(k, v)

# ── 精选项目卡片 ──
def _card(item, comment):
    stars = f'<span style="font-size:12px;color:#8e8e93;margin-left:6px;">⭐ {item.get("stars", "")}</span>' if item.get('stars') else ''
    comment_html = f'<div style="font-size:13px;color:#007aff;margin-top:6px;font-weight:500;">💬 {comment}</div>' if comment else ''
    desc = (item.get('description') or '')[:120]
    return (
        '<div style="background:#fff;border:1px solid #e8e8ed;border-radius:12px;'
        f'padding:14px 16px;margin-bottom:10px;">'
        f'<div style="font-size:15px;font-weight:600;color:#1d1d1f;">'
        f'<a href="{item.get("url", "#")}" target="_blank" style="color:#1d1d1f;text-decoration:none;">'
        f'{item["name"]}</a>{stars}</div>'
        f'<div style="font-size:14px;color:#515154;margin-top:4px;">{desc}</div>'
        f'{comment_html}</div>'
    )

# featured（第一个项目置顶）
if projects:
    first = projects[0]
    html = html.replace('##FEATURED_TITLE##', first.get('name', '暂无'))
    html = html.replace('##FEATURED_DESC##', first.get('comment', first.get('description', ''))[:200])
    html = html.replace('##FEATURED_URL##', first.get('url', '#'))
    rest = projects[1:]
else:
    html = html.replace('##FEATURED_TITLE##', '暂无')
    html = html.replace('##FEATURED_DESC##', '')
    html = html.replace('##FEATURED_URL####', '#')
    rest = []

# 所有剩余项目合并到 开源项目 区域
cards = ''.join(_card(p, p.get('comment', '')) for p in rest) or '<div style="color:#8e8e93;padding:8px 0;">暂无</div>'
html = html.replace('##OPENSOURCE_CARDS##', cards)
html = html.replace('##TOOLS_CARDS##', '')
html = html.replace('##PLAY_CARDS##', '')
html = html.replace('##MODEL_CARDS##', '')

# ── 热点事件（追加在开源项目之后） ──
if news:
    news_html = (
        '<div style="font-size:18px;font-weight:700;margin:32px 0 14px;color:#1d1d1f;">🔥 AI 热点事件</div>'
    )
    for n in news:
        comment = n.get('comment', '')
        comment_html = f'<div style="font-size:13px;color:#007aff;margin-top:4px;">💬 {comment}</div>' if comment else ''
        news_html += (
            '<div style="background:#fff8f0;border:1px solid #ffe0b2;border-radius:12px;'
            f'padding:14px 16px;margin-bottom:10px;">'
            f'<div style="font-size:15px;font-weight:600;color:#1d1d1f;">'
            f'<a href="{n.get("url", "#")}" target="_blank" style="color:#1d1d1f;text-decoration:none;">{n["name"]}</a></div>'
            f'{comment_html}</div>'
        )
    # 在开源项目区块后面插入
    html = html.replace(
        '##OPENSOURCE_CARDS##',
        '##OPENSOURCE_CARDS##\n' + news_html
    )

try:
    send(html, subject, to_email)
    print(f"[lwf] 邮件已发送至 {to_email}")
except Exception as e:
    print(f"[lwf] 发信失败: {e}")
    sys.exit(1)
