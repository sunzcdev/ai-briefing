#!/usr/bin/env python3
"""
AI 新玩意早报 - 数据采集器（anysearch 发现 + GitHub API 补详情 + 跨期去重）
用法: python3 src/collector/ai_briefing_collector.py [daily|weekly|monthly]
"""
import json, sys, os, re, time
from datetime import datetime, timedelta
from urllib.request import urlopen, Request as URLRequest
from urllib.parse import quote

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.config import CACHE_DIR, GITHUB_TOKEN, DATA_DIR

os.makedirs(CACHE_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════
# AnySearch API（JSON-RPC 2.0）
# ══════════════════════════════════════════════════════════════════

_ANYSEARCH_URL = 'https://api.anysearch.com/mcp'
_ANYSEARCH_KEY = os.environ.get('ANYSEARCH_API_KEY', '')
_BATCH_DELAY = 0.3  # 批次间隔


def _anysearch_call(query, content_types='web', max_results=10, freshness='week'):
    """调用 anysearch 搜索"""
    payload = {
        'jsonrpc': '2.0', 'method': 'tools/call',
        'params': {
            'name': 'search',
            'arguments': {
                'query': query,
                'content_types': content_types,
                'max_results': max_results,
                'freshness': freshness,
            }
        },
        'id': 1
    }
    body = json.dumps(payload).encode()
    headers = {'Content-Type': 'application/json'}
    if _ANYSEARCH_KEY:
        headers['Authorization'] = f'Bearer {_ANYSEARCH_KEY}'

    req = URLRequest(_ANYSEARCH_URL, data=body, headers=headers, method='POST')
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return data.get('result', {}).get('content', [{}])[0].get('text', '')
    except Exception as e:
        print(f'[warn] AnySearch failed ({query}): {e}', file=sys.stderr)
        return ''


def _parse_search_results(text):
    """从 anysearch API 返回的 markdown 文本中提取 (title, url, desc)"""
    items = []
    for match in re.finditer(
        r'### \d+\.\s*(.+?)\n- \*\*URL\*\*:\s*(https?://[^\n]+)\n(.*?)(?=\n### |\Z)',
        text, re.DOTALL
    ):
        title = match.group(1).strip()
        url = match.group(2).strip()
        desc = match.group(3).strip()
        desc = re.sub(r'[-*#]', '', desc).strip()[:200]
        items.append({'title': title, 'url': url, 'description': desc})
    return items


def _extract_github_repo(url):
    """从 URL 提取 GitHub owner/repo，返回 (owner, repo) 或 None"""
    m = re.match(r'https?://github\.com/([^/]+)/([^/#?]+)', url)
    if m and m.group(1) not in ('', 'apps', 'topics', 'trending', 'explore', 'sponsors'):
        return (m.group(1), m.group(2))
    return None


def _extract_repos_from_text(text):
    """从文本中提取 GitHub owner/repo 引用"""
    repos = set()
    for match in re.finditer(
        r'(?:#+|[-*])\s*([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)(?:\s|$)',
        text
    ):
        owner, repo = match.group(1), match.group(2)
        if (owner not in ('', 'URL', 'URLs', 'github', 'git')
            and not repo.startswith('github')
            and not repo.endswith(('.com', '.io', '.org'))
            and len(owner) >= 2 and len(repo) >= 2
            and not any(k in repo.lower() for k in ['crack', 'hack', 'pro-', '-pro'])):
            repos.add(f"{owner}/{repo}")
    return repos


def _is_news_url(url):
    """判断 URL 是否可能是新闻/文章"""
    ignored_domains = ('youtube.com', 'youtu.be', 'reddit.com')
    if any(d in url for d in ignored_domains):
        return False
    return not url.startswith('https://github.com/')


def _is_curated_list_article(url, title):
    """判断文章是否可能是精选列表类"""
    title_lower = (title or '').lower()
    url_lower = url.lower()
    indicators = ['top', 'best', 'curated', 'trending', 'awesome', 'must-have',
                  'most starred', 'popular', 'notable', 'breakout']
    return (any(kw in title_lower or kw in url_lower for kw in indicators)
            and 'github' in url_lower
            and _is_news_url(url))


def _anysearch_extract(url):
    """用 anysearch extract 获取页面内容"""
    payload = {
        'jsonrpc': '2.0', 'method': 'tools/call',
        'params': {'name': 'extract', 'arguments': {'url': url}},
        'id': 1
    }
    body = json.dumps(payload).encode()
    headers = {'Content-Type': 'application/json'}
    if _ANYSEARCH_KEY:
        headers['Authorization'] = f'Bearer {_ANYSEARCH_KEY}'
    try:
        req = URLRequest(_ANYSEARCH_URL, data=body, headers=headers, method='POST')
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        return data.get('result', {}).get('content', [{}])[0].get('text', '')
    except Exception as e:
        print(f'[warn] Extract failed ({url[:60]}): {e}', file=sys.stderr)
        return ''


# ── New anysearch helpers (primary API for collect_projects) ────

def _anysearch_request(method, arguments):
    """Generic anysearch JSON-RPC call"""
    payload = {
        'jsonrpc': '2.0', 'method': 'tools/call',
        'params': {'name': method, 'arguments': arguments},
        'id': 1
    }
    body = json.dumps(payload).encode()
    headers = {'Content-Type': 'application/json'}
    if _ANYSEARCH_KEY:
        headers['Authorization'] = f'Bearer {_ANYSEARCH_KEY}'
    try:
        req = URLRequest(_ANYSEARCH_URL, data=body, headers=headers, method='POST')
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return data.get('result', {}).get('content', [{}])[0].get('text', '')
    except Exception as e:
        print(f'[warn] AnySearch {method} failed: {e}', file=sys.stderr)
        return ''


def anysearch_search(query, max_results=10, freshness='week'):
    """Search using anysearch, returns list of item dicts"""
    text = _anysearch_request('search', {
        'query': query,
        'content_types': 'web',
        'max_results': max_results,
        'freshness': freshness,
    })
    items = _parse_search_results(text)
    result = []
    for item in items:
        url = item['url']
        is_gh = bool(_extract_github_repo(url))
        result.append({
            'type': 'anysearch',
            'name': item['title'],
            'url': url,
            'description': item['description'],
            'stars': 0,
            'source': 'AnySearch',
            '_kind': 'project' if is_gh else 'news',
        })
    return result


def anysearch_extract(url):
    """Extract page content using anysearch"""
    return _anysearch_request('extract', {'url': url})


def _extract_github_urls(text):
    """Extract GitHub repo URLs from text"""
    urls = []
    for match in re.finditer(r'https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)', text):
        owner, repo = match.group(1), match.group(2)
        if owner not in ('', 'apps', 'topics', 'trending', 'explore', 'sponsors'):
            urls.append(f'https://github.com/{owner}/{repo}')
    return list(set(urls))


# ══════════════════════════════════════════════════════════════════
# GitHub API
# ══════════════════════════════════════════════════════════════════

def _req(url):
    """Create a URLRequest with common headers"""
    headers = {'User-Agent': 'HermesBot/1.0', 'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return URLRequest(url, headers=headers)


def _get(url):
    """Simple GET wrapper"""
    return urlopen(_req(url), timeout=10)


def _delay(seconds):
    """Sleep wrapper"""
    time.sleep(seconds)


def _github_repo_info(owner, repo):
    """从 GitHub API 获取仓库详情"""
    url = f'https://api.github.com/repos/{owner}/{repo}'
    try:
        req = _req(url)
        with urlopen(req, timeout=10) as resp:
            r = json.loads(resp.read().decode())
        return {
            'type': 'github',
            'name': r['full_name'],
            'url': r['html_url'],
            'description': (r.get('description') or '').strip(),
            'stars': r['stargazers_count'],
            'language': r.get('language') or '',
            'topics': r.get('topics', []),
            'created': r['created_at'][:10],
            'source': 'AnySearch',
        }
    except Exception as e:
        print(f'[warn] GitHub API failed ({owner}/{repo}): {e}', file=sys.stderr)
        return None


def github_search(query, per_page=15):
    """Search GitHub repositories via API"""
    url = f'https://api.github.com/search/repositories?q={quote(query)}&per_page={per_page}&sort=stars&order=desc'
    try:
        data = json.loads(urlopen(_req(url), timeout=10).read().decode())
        results = []
        for r in data.get('items', []):
            results.append({
                'type': 'github-search',
                'name': r['full_name'],
                'url': r['html_url'],
                'description': (r.get('description') or '').strip(),
                'stars': r['stargazers_count'],
                'language': r.get('language') or '',
                'topics': r.get('topics', []),
                'created': r['created_at'][:10],
                'source': 'GitHub Search',
                '_kind': 'project',
            })
        return results
    except Exception as e:
        print(f'[warn] GitHub search failed: {e}', file=sys.stderr)
        return []


# ══════════════════════════════════════════════════════════════════
# HN 新闻
# ══════════════════════════════════════════════════════════════════

def hn_search(max_items=15):
    """Hacker News 最新热门"""
    try:
        ids = json.loads(urlopen(
            URLRequest('https://hacker-news.firebaseio.com/v0/topstories.json'),
            timeout=10
        ).read().decode())[:max_items]
        items = []
        for sid in ids:
            story = json.loads(urlopen(
                URLRequest(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json'),
                timeout=10
            ).read().decode())
            if story and story.get('type') == 'story' and story.get('title'):
                items.append({
                    'type': 'hn',
                    'name': story['title'][:120],
                    'url': story.get('url', f'https://news.ycombinator.com/item?id={sid}'),
                    'description': (story.get('title', '') or '')[:200],
                    'stars': story.get('score', 0),
                    'source': 'Hacker News',
                    '_kind': 'project' if 'github.com' in (story.get('url', '') or '') else 'news',
                })
        return items
    except Exception as e:
        print(f'[warn] HN failed: {e}', file=sys.stderr)
        return []


# ══════════════════════════════════════════════════════════════════
# 去重
# ══════════════════════════════════════════════════════════════════

def _dedup(items):
    seen = set()
    unique = []
    for item in items:
        key = item.get('url', item.get('name', ''))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _load_history_urls():
    """读取历史已选项目 URL（跨期去重）"""
    history = set()
    if os.path.exists(DATA_DIR):
        for fname in os.listdir(DATA_DIR):
            if fname.startswith('daily_') and fname.endswith('.json'):
                try:
                    with open(os.path.join(DATA_DIR, fname)) as f:
                        data = json.load(f)
                        for item in data.get('items', []):
                            if item.get('url'):
                                history.add(item['url'])
                except Exception:
                    pass
    return history


# ══════════════════════════════════════════════════════════════════
# 主采集函数
# ══════════════════════════════════════════════════════════════════

_DISCOVERY_QUERIES = {
    'daily': [
        ('trending AI open source projects github', 'code', 'week', 8),
        ('large language model release new', 'code', 'week', 5),
        ('AI agent framework new github', 'code', 'week', 5),
        ('github trending AI agent tool', 'code', 'week', 5),
        ('AI news today', 'web', 'day', 6),
        ('top open source AI projects this week', 'web', 'week', 5),
    ],
    'weekly': [
        ('trending AI open source projects github', 'code', 'month', 10),
        ('best open source AI agent tools', 'code', 'month', 8),
        ('github popular AI repositories', 'code', 'month', 8),
        ('AI news this week', 'web', 'week', 8),
        ('best AI articles this week', 'web', 'week', 5),
    ],
    'monthly': [
        ('top AI GitHub repositories 2026', 'code', 'year', 12),
        ('best open source AI projects 2026', 'code', 'year', 10),
        ('AI industry news monthly', 'web', 'month', 10),
        ('AI agent frameworks comparison', 'web', 'year', 6),
        ('github awesome AI', 'code', 'year', 10),
    ],
}


def _get_queries(mode):
    return _DISCOVERY_QUERIES.get(mode, _DISCOVERY_QUERIES['daily'])


def collect_projects(mode):
    """anysearch 发现 + GitHub API 补详情，支持跨期去重"""
    now = datetime.now()
    freshness = 'day' if mode == 'daily' else 'week' if mode == 'weekly' else 'month'

    results = []

    # ★ AnySearch 多路搜索（固定查询源）
    search_queries = [
        f'AI Agent framework open source trending {freshness}',
        f'LLM tool building github {freshness}',
        f'大模型 智能体 开源项目 {freshness}',
        f'github trending ai ml projects {freshness}',
        f'mcp server agent tool llm {freshness}',
    ]

    for q in search_queries:
        time.sleep(1)
        items = anysearch_search(q, max_results=10, freshness=freshness)
        results.extend(items)

    # ★ 多路并行: 也保留 GitHub API 兜底搜索
    since = (now - timedelta(days=2 if mode == 'daily' else 8)).strftime('%Y-%m-%d')
    gh_threshold = 5 if mode == 'daily' else 20
    results.extend(github_search(
        f'created:>{since} stars:>{gh_threshold} (ai OR llm OR agent) sort:stars-desc',
        per_page=15
    ))

    # ★ 从 anysearch 结果中 extract 文章全文，发现更多项目
    article_urls = [it['url'] for it in results
                    if it.get('_kind') == 'news' and 'github.com' not in it.get('url', '')]
    for url in article_urls[:5]:
        time.sleep(1)
        content = anysearch_extract(url)
        if content:
            gh_urls = _extract_github_urls(content)
            for gu in gh_urls:
                repo_name = '/'.join(gu.rstrip('/').split('/')[-2:])
                results.append({
                    'type': 'anysearch-extracted',
                    'name': repo_name,
                    'url': gu,
                    'description': '',
                    'stars': 0,
                    'source': 'AnySearch extracted',
                    '_kind': 'project',
                })

    # ★ GitHub API 补星数
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
            except Exception:
                pass

    # ★ 跨期去重
    seen = _load_history_urls()
    before = len(results)
    results = [it for it in results if it['url'] not in seen]
    print(f'[collector] Cross-run dedup: {before} → {len(results)} (removed {before - len(results)} duplicates)', flush=True)

    return results


def collect_news(mode):
    """anysearch 新闻 + HN 采集"""
    news_items = []

    # 新闻查询（只取非 GitHub 的结果）
    for q, ct, fresh, n in _get_queries(mode):
        text = _anysearch_call(q, ct, n, fresh)
        if text:
            for item in _parse_search_results(text):
                if _is_news_url(item['url']) and not _extract_github_repo(item['url']):
                    news_items.append({
                        'type': 'web',
                        'name': item['title'],
                        'url': item['url'],
                        'description': item['description'],
                        'stars': 0,
                        'source': 'Web',
                        '_kind': 'news',
                    })
        time.sleep(_BATCH_DELAY)

    # 补 HN
    hn_items = hn_search(10)

    all_news = _dedup(news_items + hn_items)

    # 标记 AI 相关
    for it in all_news:
        nd = (it.get('name', '') + ' ' + it.get('description', '')).lower()
        is_ai = any(k in nd for k in [
            'ai', 'llm', 'gpt', 'agent', '大模型', '智能', '人工智能',
            'machine learning', 'openai', 'model', 'neural', 'deep learning',
            'transformer', 'rag', 'mcp', 'diffusion', 'embedding',
        ])
        if not is_ai:
            it['_kind'] = 'noise'

    ai_count = sum(1 for n in all_news if n.get('_kind') != 'noise')
    print(f'[collector] News: {len(news_items)} web + {len(hn_items)} hn → {ai_count} AI-related', flush=True)
    return all_news


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    projects = collect_projects(mode)
    print(json.dumps(projects, ensure_ascii=False, indent=2))
