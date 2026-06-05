# AI 简报改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 ai-briefing 的目录同步、MD 输出、采集层重写（anysearch 为主源）、跨期去重。

**Architecture:** 不改整体结构，在现有 main.py + collector 上增量改造。采集层新增 anysearch HTTP 客户端，替代 GitHub API 关键词搜索。MD 输出在主流程中追加一个渲染步骤。

**Tech Stack:** Python stdlib（urllib + re + json），anysearch HTTP API，GitHub REST API

---

### Task 1: 配 ANYSEARCH_API_KEY secret + 修 rclone 路径

**Files:**
- Modify: `.github/workflows/ai-briefing.yml`
- Modify: `workflow.yaml`

- [ ] **Step 1: 设置 GitHub secret**

```bash
cd /home/ubuntu/ai-briefing
gh secret set ANYSEARCH_API_KEY --body "as_sk_7b15bd8f9312ebb466344544ed255f39"
```

- [ ] **Step 2: 修 .github/workflows/ai-briefing.yml 同步路径 + 加 evn 变量**

在第51行附近（rclone 配置区域），找到：
```yaml
          rclone copy data/ jianguoyun:notebook/学/AI简报/
```
改为：
```yaml
          rclone copy data/ jianguoyun:notebook/学/AI/AI简报/
```

同时在 collect-process 步骤的环境变量中加上 `ANYSEARCH_API_KEY`（紧接 LLM_KEY 所在行，约第37行）：
```yaml
          ANYSEARCH_API_KEY: ${{ secrets.ANYSEARCH_API_KEY }}
```

- [ ] **Step 3: 修 workflow.yaml 同步路径**

```yaml
      target: "notebook/学/AI/AI简报/"
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ai-briefing.yml workflow.yaml
git commit -m "fix: correct rclone path to 学/AI/AI简报/, add ANYSEARCH_API_KEY secret"
```

---

### Task 2: 添加 MD 输出模块

**Files:**
- Create: `src/digest/render_md.py`
- Modify: `main.py`（在 render_html 之后调用 render_md）

- [ ] **Step 1: 创建 render_md.py**

```python
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
```

- [ ] **Step 2: 在 main.py 中接入 render_md**

在 main.py 中：
1. import 处加上：`from src.digest.render_md import render_md`
2. 在 render_html 调用之后（约第224行）、html 保存之后，追加：

```python
    # 5b. 生成 Markdown（供 Obsidian 同步）
    try:
        render_md(selected_projects, selected_news, curated, mode, DATA_DIR)
    except Exception as e:
        print(f'[ai-briefing] MD render skip: {e}', flush=True)
```

注意：流程编号要调整，原来的 step 6/7 顺延。

- [ ] **Step 3: 本地验证**

```bash
cd /home/ubuntu/ai-briefing
AI_BRIEFING_DATA=/tmp/test_briefing_data python3 main.py daily 2>&1 | tail -10
cat /tmp/test_briefing_data/daily_*.md | head -20
```

- [ ] **Step 4: Commit**

```bash
git add src/digest/render_md.py main.py
git commit -m "feat: add MD output for Obsidian sync"
```

---

### Task 3: 重写采集层 — anysearch 为主源

**Files:**
- Modify: `src/collector/ai_briefing_collector.py`（重写采集逻辑，保留接口签名）
- Modify: `src/config.py`（加上 anysearch API 配置）

- [ ] **Step 1: config.py 加 anysearch 配置**

```python
# ── AnySearch ──────────────────────────────────
ANYSEARCH_API_KEY = os.environ.get('ANYSEARCH_API_KEY', '')
ANYSEARCH_ENDPOINT = 'https://api.anysearch.com/mcp'
```

- [ ] **Step 2: 重写 collector.py**

保留 `collect_projects(mode)` 和 `collect_news(mode)` 的接口签名，内部实现改为任何 search 为主：

```python
import json, os, sys, re, time
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.parse import quote

from src.config import ANYSEARCH_API_KEY, ANYSEARCH_ENDPOINT, DATA_DIR

def _anysearch_request(payload):
    """调用 anysearch JSON-RPC API"""
    headers = {
        'Content-Type': 'application/json',
    }
    if ANYSEARCH_API_KEY:
        headers['Authorization'] = f'Bearer {ANYSEARCH_API_KEY}'
    body = json.dumps(payload).encode()
    req = Request(ANYSEARCH_ENDPOINT, data=body, headers=headers, method='POST')
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f'[collector] anysearch API error: {e}', file=sys.stderr)
        return None

def anysearch_search(query, max_results=15, freshness='week'):
    """通用 anysearch 搜索"""
    payload = {
        'jsonrpc': '2.0',
        'method': 'tools/call',
        'params': {
            'name': 'search',
            'arguments': {
                'query': query,
                'max_results': max_results,
                'content_types': 'web,news',
                'freshness': freshness,
            }
        },
        'id': 1,
    }
    result = _anysearch_request(payload)
    if result and 'result' in result:
        items = []
        for r in result['result'].get('results', []):
            items.append({
                'type': 'anysearch',
                'name': r.get('title', '')[:120],
                'url': r.get('url', ''),
                'description': r.get('snippet', '')[:200],
                'stars': 0,  # will be enriched
                'source': 'AnySearch',
                '_kind': 'project' if ('github.com' in r.get('url', '') or 'gitlab.com' in r.get('url', '')) else 'news',
            })
        return items
    return []

def anysearch_extract(url):
    """extract 页面全文"""
    payload = {
        'jsonrpc': '2.0',
        'method': 'tools/call',
        'params': {'name': 'extract', 'arguments': {'url': url}},
        'id': 1,
    }
    result = _anysearch_request(payload)
    if result and 'result' in result:
        return result['result'].get('content', '')
    return ''

def _extract_github_urls(text):
    """从文本中提取 GitHub 仓库 URL"""
    urls = re.findall(r'https?://github\.com/[\w.-]+/[\w.-]+', text)
    unique = []
    seen = set()
    for u in urls:
        parts = u.rstrip('/').split('/')
        if len(parts) >= 5:
            key = f'{parts[-2]}/{parts[-1]}'
            if key not in seen:
                seen.add(key)
                unique.append(u)
    return unique

# ... （保留 github_search/github_trending 作为兜底，但优先级降低）

def collect_projects(mode):
    """采集候选项目 — anysearch 主源 + GitHub 补信息"""
    now = datetime.now()
    freshness = 'day' if mode == 'daily' else 'week' if mode == 'weekly' else 'month'
    
    results = []
    
    # ★ AnySearch 多路并行搜索（固定文章源）
    search_queries = [
        f'AI Agent framework open source trending {freshness}',
        f'LLM tool building github {freshness}',
        f'大模型 智能体 开源项目 {freshness}',
        f'github trending ai ml projects {freshness}',
        f'mcp server agent tool llm {freshness}',
    ]
    
    for q in search_queries:
        time.sleep(1)  # rate limit
        items = anysearch_search(q, max_results=10, freshness=freshness)
        results.extend(items)
    
    # ★ 从搜索结果中提取文章全文，发现更多项目
    article_urls = [it['url'] for it in results 
                    if it['_kind'] == 'news' and not it['url'].startswith('https://github.com')]
    for url in article_urls[:5]:  # 只 extract 前5篇
        time.sleep(1)
        content = anysearch_extract(url)
        if content:
            gh_urls = _extract_github_urls(content)
            for gu in gh_urls:
                results.append({
                    'type': 'anysearch-extracted',
                    'name': gu.split('/')[-2] + '/' + gu.split('/')[-1],
                    'url': gu,
                    'description': '',
                    'stars': 0,
                    'source': 'AnySearch extracted',
                    '_kind': 'project',
                })
    
    # ★ 用 GitHub API 补星数
    # ... (复用原有的 _req/_get 工具函数)
    for item in results:
        if item.get('stars', 0) == 0 and 'github.com' in item['url']:
            try:
                time.sleep(0.3)
                parts = item['url'].rstrip('/').split('/')
                owner, repo = parts[-2], parts[-1]
                data = json.loads(urlopen(_req(f'https://api.github.com/repos/{owner}/{repo}'), timeout=8).read().decode())
                item['stars'] = data.get('stargazers_count', 0)
                item['description'] = (data.get('description') or '').strip()
                item['language'] = data.get('language') or ''
            except:
                pass
    
    # ★ 跨期去重
    seen = _load_history_urls()
    before = len(results)
    results = [it for it in results if it['url'] not in seen]
    print(f'[collector] Cross-run dedup: {before} → {len(results)} (removed {before - len(results)} duplicates)', flush=True)
    
    return results

def _load_history_urls():
    """读取历史已选项目 URL"""
    history = set()
    data_dir = DATA_DIR
    if os.path.exists(data_dir):
        for fname in os.listdir(data_dir):
            if fname.startswith('daily_') and fname.endswith('.json'):
                try:
                    with open(os.path.join(data_dir, fname)) as f:
                        data = json.load(f)
                        for item in data.get('items', []):
                            if item.get('url'):
                                history.add(item['url'])
                except:
                    pass
    return history
```

注意：上面是核心逻辑展示。实际代码实现时要保持完整可运行，包括保留原有的 `_req`、`_get`、`github_search`、`github_trending` 等函数作为兜底。

- [ ] **Step 3: 本地验证**

```bash
cd /home/ubuntu/ai-briefing
AI_BRIEFING_DATA=/tmp/test_briefing_data python3 -c "
from src.collector.ai_briefing_collector import collect_projects
projects = collect_projects('daily')
print(f'Collected: {len(projects)} projects')
for p in projects[:5]:
    print(f'  {p[\"name\"]} ⭐{p.get(\"stars\",0)} {p[\"url\"][:60]}')
"
```

- [ ] **Step 4: Commit**

```bash
git add src/collector/ai_briefing_collector.py src/config.py
git commit -m "feat: rewrite collector with anysearch as primary source + cross-run dedup"
```

---

### Task 4: 推送上线

- [ ] **Step 1: 推送所有改动**

```bash
cd /home/ubuntu/ai-briefing && git push
```

- [ ] **Step 2: 手动触发一次 GHA 验证**

```bash
gh workflow run ai-briefing --ref main -f mode=daily
```

- [ ] **Step 3: 查看运行日志**

```bash
sleep 60 && gh run list --workflow ai-briefing --limit 1 --json databaseId,databaseId | head -5
gh run view <run_id> --log | grep -E '\[ai-briefing\]|\[collector\]|\[render_md\]|rclone|Transferred'
```

- [ ] **Step 4: 确认坚果云上有新文件**

```bash
rclone ls jianguoyun:notebook/学/AI/AI简报/ 2>&1 | tail -5
```
