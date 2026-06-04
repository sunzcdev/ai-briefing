#!/usr/bin/env python3
"""生成 Obsidian 格式的 Markdown 版本 AI 简报"""
import os
from datetime import datetime

def render_md(project_items, news_items, curated, mode='daily', output_dir=None):
    weekdays = ['一', '二', '三', '四', '五', '六', '日']
    now = datetime.now()
    date_str = now.strftime('%Y年%m月%d日')
    weekday = weekdays[now.weekday()]
    mode_labels = {'daily': '日报', 'weekly': '周报', 'monthly': '月报'}
    
    curated_projects = {c['name']: c.get('comment', '') for c in (curated or {}).get('projects', [])}
    curated_news = {c['name']: c.get('comment', '') for c in (curated or {}).get('news', [])}
    
    lines = []
    lines.append(f'# AI 新玩意早报 — {date_str} {weekday}')
    lines.append('')
    lines.append(f'> {mode_labels.get(mode, mode)} | LLM 精选')
    lines.append('')
    
    # Featured
    if project_items:
        featured = project_items[0]
        lines.append('## 🔥 本周精选')
        lines.append('')
        comment = curated_projects.get(featured['name'], '')
        stars = f' ⭐{featured.get("stars", 0)}' if featured.get('stars') else ''
        lines.append(f'### [{featured["name"]}]({featured["url"]}){stars}')
        desc = featured.get('description', '') or ''
        if desc:
            lines.append(f'> {desc}')
        if comment:
            lines.append(f'> ')
            lines.append(f'> 💬 {comment}')
        lines.append('')
        lines.append('---')
        lines.append('')
    
    # 分类展示
    sections = {'开源项目': [], '新工具': [], '新玩法 & 创意': [], '新模型': []}
    for item in project_items:
        tag = item.get('tag', '开源项目')
        sections.get(tag, []).append(item)
    
    for section_name, items in sections.items():
        if not items:
            continue
        lines.append(f'## {section_name}')
        lines.append('')
        for item in items:
            stars = f' ⭐{item.get("stars", 0)}' if item.get('stars') else ''
            lines.append(f'- [{item["name"]}]({item["url"]}){stars}')
            comment = curated_projects.get(item['name'], '')
            if comment:
                lines.append(f'  - 💬 {comment}')
            desc = item.get('description', '') or ''
            if desc and not comment:
                lines.append(f'  - {desc[:120]}')
        lines.append('')
    
    # 热点事件
    if news_items:
        lines.append('---')
        lines.append('')
        lines.append('## 🔥 AI 热点事件')
        lines.append('')
        for item in news_items:
            lines.append(f'- [{item["name"]}]({item["url"]})')
            comment = curated_news.get(item['name'], '')
            if comment:
                lines.append(f'  - 💬 {comment}')
        lines.append('')
    
    content = '\n'.join(lines)
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f'{mode}_{now.strftime("%Y%m%d")}.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[render_md] MD: {filepath}', flush=True)
    
    return content
