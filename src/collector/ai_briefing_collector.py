#!/usr/bin/env python3
"""
AI 新玩意早报 - 数据采集器
用法: python3 src/collector/ai_briefing_collector.py [daily|weekly|monthly]
"""
import json, sys, os, re
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.parse import quote

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.config import CACHE_DIR, GITHUB_TOKEN, TRACKER_PATH

os.makedirs(CACHE_DIR, exist_ok=True)


def _req(url):
    headers = {'User-Agent': 'HermesBot/1.0', 'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return Request(url, headers=headers)


def _get(url, timeout=12):
    return json.loads(urlopen(_req(url), timeout=timeout).read().decode())


def _delay():
    import time; time.sleep(1.5)


# ===== GitHub 搜索 =====

def github_search(query, per_page=15):
    """GitHub API 搜索仓库"""
    q = quote(query)
    url = f'https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page={per_page}'
    try:
        data = _get(url)
        items = []
        for r in data.get('items', []):
            items.append({
                'type': 'github',
                'name': r['full_name'],
                'url': r['html_url'],
                'description': (r.get('description') or '').strip(),
                'stars': r['stargazers_count'],
                'language': r.get('language') or '',
                'topics': r.get('topics', []),
                'created': r['created_at'][:10],
                'source': 'GitHub'
            })
        return items
    except Exception as e:
        print(f'[warn] GitHub search failed: {e}', file=sys.stderr)
        return []


def github_trending(language='', since='daily'):
    """GitHub Trending（爬取）"""
    url = f'https://github.com/trending/{language}?since={since}'
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urlopen(req, timeout=10).read().decode('utf-8')
        items = []
        for match in re.finditer(
            r'<h2[^>]*class="h3[^"]*">\s*<a[^>]*href="/([^/]+)/([^"]+)"',
            html
        ):
            owner, repo = match.group(1), match.group(2)
            name = f'{owner}/{repo}'
            items.append({
                'type': 'github-trending',
                'name': name,
                'url': f'https://github.com/{name}',
                'description': '',
                'stars': 0,
                'language': language or 'unknown',
                'source': 'GitHub Trending'
            })
        return items[:10]
    except Exception as e:
        print(f'[warn] Trending failed: {e}', file=sys.stderr)
        return []


# ===== Hacker News =====

def hn_search(max_items=20):
    """Hacker News 最新热门（同时产出项目 & 新闻）"""
    try:
        ids = _get('https://hacker-news.firebaseio.com/v0/topstories.json')[:max_items]
        items = []
        for sid in ids:
            story = _get(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json')
            if story and story.get('type') == 'story' and story.get('title'):
                title = story['title'][:120]
                url = story.get('url', f'https://news.ycombinator.com/item?id={sid}')
                desc = (story.get('title', '') or '')[:200]
                is_project = bool(re.search(r'github\.com|gitlab\.com|\.dev|\.app|release|开源', title, re.I))
                items.append({
                    'type': 'hn',
                    'name': title,
                    'url': url,
                    'description': desc,
                    'stars': story.get('score', 0),
                    'source': 'Hacker News',
                    '_kind': 'project' if is_project else 'news'
                })
        return items
    except Exception as e:
        print(f'[warn] HN failed: {e}', file=sys.stderr)
        return []


# ===== Reddit =====

def reddit_search(subreddit, limit=15):
    url = f'https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}'
    try:
        req = Request(url, headers={'User-Agent': 'HermesBot/1.0'})
        data = json.loads(urlopen(req, timeout=10).read().decode())
        items = []
        for post in data.get('data', {}).get('children', []):
            p = post['data']
            title = p.get('title', '')[:120]
            is_project = bool(re.search(r'github\.com|release|开源|项目|launch|announce', title, re.I))
            items.append({
                'type': 'reddit',
                'name': title,
                'url': f"https://reddit.com{p.get('permalink', '')}",
                'description': (p.get('selftext', '') or p.get('title', ''))[:200],
                'stars': p.get('score', 0),
                'source': f'r/{subreddit}',
                '_kind': 'project' if is_project else 'news'
            })
        return items
    except Exception as e:
        print(f'[warn] Reddit failed: {e}', file=sys.stderr)
        return []


# ===== TopHub =====

def tophub_search():
    url = 'https://tophub.today/'
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urlopen(req, timeout=10).read().decode('utf-8')
        items = []
        for match in re.finditer(
            r'<a[^>]*href="(https?://[^\"]+)"[^>]*class="[^\"]*cc-cd-cb-[^\"]*"[^>]*>(.*?)</a>.*?<span[^>]*class="[^\"]*e.[^\"]*"[^>]*>(\d+)</span>',
            html, re.DOTALL
        ):
            name = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            if name:
                items.append({
                    'type': 'hotlist',
                    'name': name[:120],
                    'url': match.group(1),
                    'description': '',
                    'stars': int(match.group(3)),
                    'source': '热榜',
                    '_kind': 'news'
                })
        return items[:15]
    except Exception as e:
        print(f'[warn] TopHub failed: {e}', file=sys.stderr)
        return []


# ===== 综合采集 =====

def _tag_project_kind(items):
    """统一标记 _kind（未标记的默认 project）"""
    for it in items:
        if '_kind' not in it:
            it['_kind'] = 'project'


def _dedup(items):
    seen = set()
    unique = []
    for item in items:
        if item['url'] not in seen:
            seen.add(item['url'])
            unique.append(item)
    return unique


def collect_projects(mode):
    """采集候选项目（含中文 AI 项目 + GitHub Trending）"""
    now = datetime.now()
    if mode == 'daily':
        since = (now - timedelta(days=2)).strftime('%Y-%m-%d')
        gh_threshold = 5
    elif mode == 'weekly':
        since = (now - timedelta(days=8)).strftime('%Y-%m-%d')
        gh_threshold = 20
    else:  # monthly
        since = (now - timedelta(days=32)).strftime('%Y-%m-%d')
        gh_threshold = 100

    results = []

    # ★ 国际 AI/Agent 项目
    results.extend(github_search(
        f'created:>{since} stars:>{gh_threshold} (ai OR llm OR gpt OR agent OR "machine learning") sort:stars-desc',
        per_page=20
    ))
    results.extend(github_search(
        f'created:>{since} stars:>{gh_threshold * 3} sort:stars-desc',
        per_page=10
    ))

    # ★ 中文 AI/Agent 项目
    cn_queries = [
        f'created:>{since} stars:>{gh_threshold} (大模型 OR 智能体 OR 人工智能 OR AI助手) language:Chinese sort:stars-desc',
        f'created:>{since} stars:>{gh_threshold} (agent OR llm OR rag OR mcp) language:Chinese sort:stars-desc',
    ]
    for q in cn_queries:
        _delay()
        results.extend(github_search(q, per_page=15))

    # ★ GitHub Trending
    _delay()
    results.extend(github_trending('python', 'daily' if mode == 'daily' else 'weekly'))

    return results


def collect_news(mode):
    """采集热点事件"""
    results = []

    # HN + Reddit
    results.extend(hn_search(15))
    _delay()
    results.extend(reddit_search('MachineLearning', 10))
    _delay()
    results.extend(reddit_search('LocalLLaMA', 10))

    # TopHub 中文热榜
    results.extend(tophub_search())

    # GitHub Trending（也产出新闻类）
    _delay()
    results.extend(github_trending('', 'daily' if mode == 'daily' else 'weekly'))

    # 标记 AI 相关
    for it in results:
        nd = (it.get('name', '') + ' ' + it.get('description', '')).lower()
        is_ai = any(k in nd for k in ['ai', 'llm', 'gpt', 'agent', '大模型', '智能', '人工智能', 'machine learning', 'openai'])
        if not is_ai:
            it['_kind'] = 'noise'

    return results


def read_tracker():
    try:
        with open(TRACKER_PATH) as f:
            return json.load(f).get('projects', [])
    except:
        return []


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    projects = collect_projects(mode)
    news = collect_news(mode)
    all_items = _dedup(projects + [n for n in news if n.get('_kind') != 'noise'])
    print(json.dumps({
        'items': all_items,
        'tracked': read_tracker(),
        'mode': mode
    }, ensure_ascii=False, indent=2))
