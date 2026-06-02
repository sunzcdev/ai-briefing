#!/usr/bin/env python3
"""
AI 简报主入口 — 串联采集→清洗→HTML渲染→邮件发送
用法: python3 main.py [daily|weekly|monthly]
"""
import json, os, re, sys
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.collector.ai_briefing_collector import collect_daily, collect_weekly, collect_monthly
from src.storage.ai_briefing_storage import cmd_save
from src.digest.send_ai_briefing import send
from src.config import DATA_DIR, QQ_SMTP_PASS

# ── 每期限量 ──────────────────────────────────
MAX_ITEMS = {'daily': 10, 'weekly': 20, 'monthly': 30}


def _clean_item(item):
    """清洗单条 item 的描述文本"""
    desc = (item.get('description') or '').strip()

    # 去掉无意义描述
    if not desc or len(desc) < 15:
        item['description'] = ''
        return item

    # 检测冗余重复（同一句话出现 ≥3 次 → 取第一次）
    # 按句号/逗号/分号分割，去重
    parts = re.split(r'[。，；,;.]', desc)
    parts = [p.strip() for p in parts if len(p.strip()) > 5]
    unique = []
    seen = set()
    for p in parts:
        key = p[:20]  # 前20字作为指纹
        if key not in seen:
            seen.add(key)
            unique.append(p)

    if len(unique) < len(parts):
        # 有重复，重建描述
        desc = '，'.join(unique)

    # 截断过长描述（100字以内）
    if len(desc) > 100:
        desc = desc[:97] + '…'

    item['description'] = desc
    return item


def _clean_items(items, mode):
    """对 items 执行清洗 + 限数"""
    # 1. 描述清洗
    items = [_clean_item(it) for it in items]

    # 2. 筛掉无简介的（description 为空或太短）
    items = [it for it in items if len(it.get('description', '')) >= 15]

    # 3. 按星数降序
    items.sort(key=lambda x: x.get('stars', 0), reverse=True)

    # 4. 截取上限
    items = items[:MAX_ITEMS.get(mode, 20)]

    return items


# ── 卡片渲染 ──────────────────────────────────

def _render_card(item):
    tag = item.get('tag', '')
    badge = (f'<span style="display:inline-block;font-size:10px;font-weight:600;color:#6e6e73;'
             f'background:#f2f2f7;padding:2px 8px 1px;border-radius:8px;margin-right:6px;'
             f'vertical-align:middle;">{tag}</span>') if tag else ''
    stars = (f'<span style="font-size:12px;color:#8e8e93;margin-left:6px;">⭐ {item["stars"]}</span>'
             ) if item.get('stars') else ''
    return (f'<div style="background:#fff;border:1px solid #e8e8ed;border-radius:12px;'
            f'padding:14px 16px;margin-bottom:10px;">'
            f'<div style="font-size:15px;font-weight:600;color:#1d1d1f;line-height:1.4;">'
            f'{badge}<a href="{item["url"]}" target="_blank" style="color:#1d1d1f;text-decoration:none;">'
            f'{item["name"]}</a>{stars}</div>'
            f'<div style="font-size:14px;color:#515154;margin-top:4px;line-height:1.5;">'
            f'{item.get("description", "")}</div></div>')


def render_html(items, mode='weekly'):
    template_path = os.path.join(_PROJECT_ROOT, 'src', 'digest', 'ai_digest_template.html')
    with open(template_path, encoding='utf-8') as f:
        html = f.read()
    now = datetime.now()
    weekdays = ['一', '二', '三', '四', '五', '六', '日']

    sections = {'开源项目': [], '新工具': [], '新玩法 & 创意': [], '新模型': []}
    for item in items:
        tag = item.get('tag', '')
        sections.get(tag, []).append(item)

    featured_item = next((it for it in items if it.get('featured')), items[0] if items else None)

    replacements = {
        '##TITLE##': 'AI 新玩意早报', '##ICON##': '🤖',
        '##DATE##': now.strftime('%Y年%m月%d日'), '##WEEKDAY##': weekdays[now.weekday()],
        '##QUOTE##': '代码干体力活，LLM只做润色',
        '##HEADER_BG##': '#1d1d1f', '##ACCENT##': '#007aff',
        '##FEATURED_BG##': '#f0f7ff', '##FEATURED_BORDER##': '#cce5ff',
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    if featured_item:
        html = html.replace('##FEATURED_TITLE##', featured_item['name'])
        html = html.replace('##FEATURED_DESC##', featured_item.get('description', '')[:200])
        html = html.replace('##FEATURED_URL##', featured_item['url'])

    for key, placeholder in [
        ('开源项目', '##OPENSOURCE_CARDS##'), ('新工具', '##TOOLS_CARDS##'),
        ('新玩法 & 创意', '##PLAY_CARDS##'), ('新模型', '##MODEL_CARDS##')
    ]:
        cards = ''.join(_render_card(it) for it in sections[key]) or '<div style="color:#8e8e93;padding:8px 0;">暂无</div>'
        html = html.replace(placeholder, cards)

    return html


# ── 主流程 ─────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'weekly'
    collectors = {'daily': collect_daily, 'weekly': collect_weekly, 'monthly': collect_monthly}
    if mode not in collectors:
        print(f'Usage: python3 main.py [{"/".join(collectors)}]', file=sys.stderr); sys.exit(1)

    print(f'[ai-briefing] Mode: {mode}', flush=True)

    raw = collectors[mode]()
    items = raw if isinstance(raw, list) else raw.get('items', [])
    print(f'[ai-briefing] Raw: {len(items)} items', flush=True)

    # 粗略分类
    for item in items:
        nd = (item.get('name', '') + ' ' + item.get('description', '')).lower()
        if any(k in nd for k in ['llm', 'gpt', 'model ', 'language model', 'transformer', 'diffusion']):
            item['tag'] = '新模型'
        elif any(k in nd for k in ['tool', 'cli', 'plugin', 'extension', 'app ', 'ui', 'dashboard', 'web']):
            item['tag'] = '新工具'
        elif any(k in nd for k in ['game', 'art', 'music', 'video', 'creative', 'demo', 'fun']):
            item['tag'] = '新玩法 & 创意'
        else:
            item['tag'] = '开源项目'

    # 清洗 + 限数
    items = _clean_items(items, mode)
    print(f'[ai-briefing] Cleaned: {len(items)} items', flush=True)

    if not items:
        print('[ai-briefing] No items after cleaning, skip.', flush=True)
        return

    items[0]['featured'] = True

    # 渲染
    html = render_html(items, mode)
    html_path = os.path.join(DATA_DIR, f'{mode}_{datetime.now().strftime("%Y%m%d")}.html')
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[ai-briefing] HTML: {html_path}', flush=True)

    # 存储
    try:
        cmd_save(datetime.now().strftime('%Y-%m-%d'), json.dumps(items, ensure_ascii=False))
    except Exception as e:
        print(f'[ai-briefing] Storage skip: {e}', flush=True)

    # 发信
    if not QQ_SMTP_PASS:
        print('[ai-briefing] QQ_SMTP_PASS missing, email skip.', flush=True)
    else:
        labels = {'daily': '日报', 'weekly': '周报', 'monthly': '月报'}
        try:
            send(html, f'AI 新玩意{labels.get(mode, mode)} {datetime.now().strftime("%Y-%m-%d")}')
            print('[ai-briefing] Email sent.', flush=True)
        except Exception as e:
            print(f'[ai-briefing] Email fail: {e}', flush=True)

    print('[ai-briefing] Done.', flush=True)


if __name__ == '__main__':
    main()
