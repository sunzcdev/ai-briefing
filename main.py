#!/usr/bin/env python3
"""
AI 简报主入口 — 采集→LLM精选→HTML渲染→邮件发送
用法: python3 main.py [daily|weekly|monthly]
"""
import json, os, re, sys
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.collector.ai_briefing_collector import collect_projects, collect_news, _dedup
from src.curator import curate
from src.storage.ai_briefing_storage import cmd_save
from src.digest.send_ai_briefing import send
from src.digest.render_md import render_md
from src.config import DATA_DIR, EMAIL_PASS


def _clean_item(item):
    """清洗单条 item 的描述文本"""
    desc = (item.get('description') or '').strip()
    if not desc or len(desc) < 15:
        item['description'] = ''
        return item
    parts = re.split(r'[。，；,;.]', desc)
    parts = [p.strip() for p in parts if len(p.strip()) > 5]
    unique = []
    seen = set()
    for p in parts:
        key = p[:20]
        if key not in seen:
            seen.add(key)
            unique.append(p)
    desc = '，'.join(unique) if len(unique) < len(parts) else desc
    if len(desc) > 100:
        desc = desc[:97] + '…'
    item['description'] = desc
    return item


def _tag_item(item):
    """分类打 tag"""
    nd = (item.get('name', '') + ' ' + item.get('description', '')).lower()
    if any(k in nd for k in ['llm', 'gpt', 'model ', 'language model', 'transformer', 'diffusion']):
        item['tag'] = '新模型'
    elif any(k in nd for k in ['tool', 'cli', 'plugin', 'extension', 'app ', 'ui', 'dashboard', 'web']):
        item['tag'] = '新工具'
    elif any(k in nd for k in ['game', 'art', 'music', 'video', 'creative', 'demo', 'fun']):
        item['tag'] = '新玩法 & 创意'
    else:
        item['tag'] = '开源项目'
    return item


def _has_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def _render_card(item, comment=''):
    tag = item.get('tag', '')
    badge = (f'<span style="display:inline-block;font-size:10px;font-weight:600;color:#6e6e73;'
             f'background:#f2f2f7;padding:2px 8px 1px;border-radius:8px;margin-right:6px;'
             f'vertical-align:middle;">{tag}</span>') if tag else ''
    stars = (f'<span style="font-size:12px;color:#8e8e93;margin-left:6px;">⭐ {item["stars"]}</span>'
             ) if item.get('stars') else ''
    desc = item.get('description', '')
    # 非中文描述不显示，用 LLM 点评替代
    if desc and not _has_chinese(desc):
        desc = ''
    comment_html = (f'<div style="font-size:13px;color:#007aff;margin-top:6px;font-weight:500;">'
                    f'💬 {comment}</div>') if comment else ''
    return (f'<div style="background:#fff;border:1px solid #e8e8ed;border-radius:12px;'
            f'padding:14px 16px;margin-bottom:10px;">'
            f'<div style="font-size:15px;font-weight:600;color:#1d1d1f;line-height:1.4;">'
            f'{badge}<a href="{item["url"]}" target="_blank" style="color:#1d1d1f;text-decoration:none;">'
            f'{item["name"]}</a>{stars}</div>'
            f'<div style="font-size:14px;color:#515154;margin-top:4px;line-height:1.5;">'
            f'{desc}</div>'
            f'{comment_html}</div>')


def render_html(project_items, news_items, curated, mode='daily'):
    template_path = os.path.join(_PROJECT_ROOT, 'src', 'digest', 'ai_digest_template.html')
    with open(template_path, encoding='utf-8') as f:
        html = f.read()
    now = datetime.now()
    weekdays = ['一', '二', '三', '四', '五', '六', '日']

    # 构建项目卡片（含 LLM 点评）
    curated_projects = {c['name']: c.get('comment', '') for c in (curated or {}).get('projects', [])}
    curated_news = {c['name']: c.get('comment', '') for c in (curated or {}).get('news', [])}

    sections = {'开源项目': [], '新工具': [], '新玩法 & 创意': [], '新模型': []}
    for item in project_items:
        tag = item.get('tag', '')
        sections.get(tag, []).append(item)

    featured_item = project_items[0] if project_items else None

    # 替换模板占位符
    replacements = {
        '##TITLE##': 'AI 新玩意早报', '##ICON##': '🤖',
        '##DATE##': now.strftime('%Y年%m月%d日'), '##WEEKDAY##': weekdays[now.weekday()],
        '##QUOTE##': 'LLM 精选，AI 圈每日必读',
        '##HEADER_BG##': '#1d1d1f', '##ACCENT##': '#007aff',
        '##FEATURED_BG##': '#f0f7ff', '##FEATURED_BORDER##': '#cce5ff',
    }
    for k, v in replacements.items():
        html = html.replace(k, v)

    if featured_item:
        html = html.replace('##FEATURED_TITLE##', featured_item['name'])
        html = html.replace('##FEATURED_DESC##',
            curated_projects.get(featured_item['name'], featured_item.get('description', '')[:200]))
        html = html.replace('##FEATURED_URL##', featured_item['url'])

    # 分类卡片（含点评）
    for key, placeholder in [
        ('开源项目', '##OPENSOURCE_CARDS##'), ('新工具', '##TOOLS_CARDS##'),
        ('新玩法 & 创意', '##PLAY_CARDS##'), ('新模型', '##MODEL_CARDS##')
    ]:
        cards = ''.join(
            _render_card(it, curated_projects.get(it['name'], ''))
            for it in sections[key]
        ) or '<div style="color:#8e8e93;padding:8px 0;">暂无</div>'
        html = html.replace(placeholder, cards)

    # 热点事件区域（追加在模板最后）
    if news_items:
        news_html = '\n<div style="font-size:18px;font-weight:700;margin:32px 0 14px;color:#1d1d1f;">🔥 AI 热点事件</div>\n'
        for item in news_items:
            comment = curated_news.get(item['name'], '')
            comment_html = (f'<div style="font-size:13px;color:#007aff;margin-top:4px;">💬 {comment}</div>'
                           ) if comment else ''
            news_html += (f'<div style="background:#fff8f0;border:1px solid #ffe0b2;border-radius:12px;'
                         f'padding:14px 16px;margin-bottom:10px;">'
                         f'<div style="font-size:15px;font-weight:600;color:#1d1d1f;line-height:1.4;">'
                         f'<a href="{item["url"]}" target="_blank" style="color:#1d1d1f;text-decoration:none;">'
                         f'{item["name"]}</a></div>'
                         f'<div style="font-size:14px;color:#515154;margin-top:4px;">'
                         f'{item.get("description", "")[:150]}</div>'
                         f'{comment_html}</div>\n')
        # 插入在 footer 前
        html = html.replace('##PLAY_CARDS##',
            '##PLAY_CARDS##\n' + news_html)

    return html


def build_pool(projects, news):
    """构造完整 item 池（供存储用）"""
    pool = []
    for p in projects:
        p['_kind'] = 'project'
        pool.append(p)
    for n in news:
        n['_kind'] = 'news'
        pool.append(n)
    return pool


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    if mode not in ('daily', 'weekly', 'monthly'):
        print(f'Usage: python3 main.py [daily|weekly|monthly]', file=sys.stderr)
        sys.exit(1)

    print(f'[ai-briefing] Mode: {mode}', flush=True)

    # 1. 采集
    raw_projects = collect_projects(mode)
    raw_news = collect_news(mode)
    print(f'[ai-briefing] Raw: {len(raw_projects)} projects, {len(raw_news)} news', flush=True)

    # 2. 去重 + 清洗
    all_candidates = _dedup(raw_projects)
    all_news = _dedup([n for n in raw_news if n.get('_kind') != 'noise'])

    for item in all_candidates:
        _clean_item(item)
        _tag_item(item)
    for item in all_news:
        _clean_item(item)

    # 筛掉无简介的项目
    all_candidates = [it for it in all_candidates
                      if len(it.get('description', '')) >= 15]
    all_candidates.sort(key=lambda x: x.get('stars', 0), reverse=True)

    # 取候选给 LLM
    candidates_pool = all_candidates[:50]
    news_pool = all_news[:50]

    print(f'[ai-briefing] Candidate pool: {len(candidates_pool)} projects, {len(news_pool)} news', flush=True)

    # 3. LLM 精选
    curated = curate(candidates_pool, news_pool, mode)

    if curated:
        # LLM 精选成功：根据 LLM 选出的 name 匹配回原始 item
        curated_names_p = {c['name'] for c in curated.get('projects', [])}
        curated_names_n = {c['name'] for c in curated.get('news', [])}

        selected_projects = [it for it in candidates_pool if it['name'] in curated_names_p]
        selected_news = [it for it in news_pool if it['name'] in curated_names_n]
        print(f'[ai-briefing] LLM curated: {len(selected_projects)} projects, {len(selected_news)} news', flush=True)
    else:
        # Fallback: 按星数取
        selected_projects = candidates_pool[:10]
        selected_news = news_pool[:5]
        curated = {'projects': [], 'news': []}
        print(f'[ai-briefing] Fallback (star ranking): {len(selected_projects)} projects, {len(selected_news)} news', flush=True)

    if not selected_projects:
        print('[ai-briefing] No items, skip.', flush=True)
        return

    # 4. 标记 featured
    selected_projects[0]['featured'] = True

    # 5. 渲染 HTML
    html = render_html(selected_projects, selected_news, curated, mode)
    html_path = os.path.join(DATA_DIR, f'{mode}_{datetime.now().strftime("%Y%m%d")}.html')
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[ai-briefing] HTML: {html_path}', flush=True)

    # 5b. 生成 Markdown（供 Obsidian 同步）
    try:
        render_md(selected_projects, selected_news, curated, mode, DATA_DIR)
    except Exception as e:
        print(f'[ai-briefing] MD render skip: {e}', flush=True)

    # 6. 存储
    pool = build_pool(selected_projects, selected_news)
    try:
        cmd_save(datetime.now().strftime('%Y-%m-%d'), json.dumps(pool, ensure_ascii=False))
    except Exception as e:
        print(f'[ai-briefing] Storage skip: {e}', flush=True)

    # 7. 发信
    if not EMAIL_PASS:
        print('[ai-briefing] EMAIL_PASS missing, email skip.', flush=True)
    else:
        labels = {'daily': '日报', 'weekly': '周报', 'monthly': '月报'}
        subject = f'AI 新玩意{labels.get(mode, mode)} {datetime.now().strftime("%Y-%m-%d")}'
        try:
            send(html, subject)
            print('[ai-briefing] Email sent.', flush=True)
        except Exception as e:
            print(f'[ai-briefing] Email fail: {e}', flush=True)

    print('[ai-briefing] Done.', flush=True)


if __name__ == '__main__':
    main()
