#!/usr/bin/env python3
"""
AI 新玩意早报 - 数据采集器（anysearch 发现 + GitHub API 补详情）
用法: python3 src/collector/ai_briefing_collector.py [daily|weekly|monthly]
"""
import json, sys, os, re
from datetime import datetime, timedelta
from urllib.request import urlopen, Request as URLRequest
from urllib.parse import quote

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.config import CACHE_DIR, GITHUB_TOKEN

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
    """从文本中提取 GitHub owner/repo 引用（如 ## owner/repo 或 owner/repo 后跟描述）"""
    repos = set()
    # 匹配 ## owner/repo 或 - owner/repo 模式（trending 页、描述文本常见）
    for match in re.finditer(
        r'(?:#+|[-*])\s*([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)(?:\s|$)',
        text
    ):
        owner, repo = match.group(1), match.group(2)
        # 过滤明显不是 GitHub repo 的
        if (owner not in ('', 'URL', 'URLs', 'github', 'git') 
            and not repo.startswith('github')
            and not repo.endswith(('.com', '.io', '.org'))
            and len(owner) >= 2 and len(repo) >= 2
            and not any(k in repo.lower() for k in ['crack', 'hack', 'pro-', '-pro'])):
            repos.add(f"{owner}/{repo}")
    return repos


def _is_news_url(url):
    """判断 URL 是否可能是新闻/文章（非 GitHub 代码页）"""
    ignored_domains = ('youtube.com', 'youtu.be', 'reddit.com')
    if any(d in url for d in ignored_domains):
        return False
    return not url.startswith('https://github.com/')


# ══════════════════════════════════════════════════════════════════
# GitHub API 补详情
# ══════════════════════════════════════════════════════════════════

def _github_repo_info(owner, repo):
    """从 GitHub API 获取仓库详情"""
    url = f'https://api.github.com/repos/{owner}/{repo}'
    headers = {'User-Agent': 'HermesBot/1.0', 'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    try:
        req = URLRequest(url, headers=headers)
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


# ══════════════════════════════════════════════════════════════════
# HN 新闻（保留现有，firebase API 稳定）
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


# ══════════════════════════════════════════════════════════════════
# 主采集函数
# ══════════════════════════════════════════════════════════════════

_DISCOVERY_QUERIES = {
    'daily': [
        # 项目发现（code 类型直接返回 GitHub repo 详情）
        ('trending AI open source projects github', 'code', 'week', 8),
        ('large language model release new', 'code', 'week', 5),
        ('AI agent framework new github', 'code', 'week', 5),
        ('github trending AI agent tool', 'code', 'week', 5),
        # 新闻发现
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
    """
    用 anysearch 发现 + GitHub API 补详情来采集项目
    """
    import time
    queries = _get_queries(mode)
    
    # Phase 1: anysearch 批量发现
    raw_items = []
    for q, ct, fresh, n in queries:
        text = _anysearch_call(q, ct, n, fresh)
        if text:
            raw_items.extend(_parse_search_results(text))
        time.sleep(_BATCH_DELAY)
    
    # Phase 2: 提取 GitHub 仓库（从 URL + 描述文本）
    seen_repos = set()
    projects = []
    for item in raw_items:
        gh = _extract_github_repo(item['url'])
        if gh:
            repo_key = f"{gh[0]}/{gh[1]}"
            if repo_key not in seen_repos:
                seen_repos.add(repo_key)
                info = _github_repo_info(gh[0], gh[1])
                if info:
                    projects.append(info)
                time.sleep(0.3)
        # 从描述文本中也提取 GitHub 引用
        text_repos = _extract_repos_from_text(item.get('description', ''))
        for repo_key in text_repos:
            if repo_key not in seen_repos:
                seen_repos.add(repo_key)
                parts = repo_key.split('/')
                info = _github_repo_info(parts[0], parts[1])
                if info:
                    projects.append(info)
                time.sleep(0.3)
        # 新闻类结果留给 collect_news 处理
    
    # Phase 3: 补一些精选文章里的项目（通过 anysearch extract 拉精选列表内容）
    # 当前 MVP 只处理直接搜到的 GitHub URL，不做文章内提取
    
    print(f'[collector] AnySearch: {len(raw_items)} raw → {len(projects)} projects', flush=True)
    return projects


def collect_news(mode):
    """
    anysearch 新闻 + HN 采集
    """
    import time
    
    # 新闻查询（只取非 GitHub 的结果）
    news_items = []
    for q, ct, fresh, n in _get_queries(mode):
        text = _anysearch_call(q, ct, n, fresh)
        if text:
            for item in _parse_search_results(text):
                # 保留新闻/文章（非 GitHub 仓库）
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
    
    # 标记 AI 相关（降低阈值：保留所有东西，让 LLM 去筛）
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
