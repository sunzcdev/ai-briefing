#!/usr/bin/env python3
"""
AI 新玩意早报 - 数据采集器
用免费API采集数据，LLM只需要做最后的润色和摘要。
输出: JSON数组 [{name, url, description, stars, source}]
"""
import json, sys, os, re
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.parse import quote

CACHE_DIR = os.path.expanduser('~/.hermes/cache/ai_briefing')
os.makedirs(CACHE_DIR, exist_ok=True)

# 读取 API Keys
_GH_TOKEN = None
_TWITTER = {}
_keys_path = os.path.expanduser('~/.hermes/scripts/api_keys.json')
if os.path.exists(_keys_path):
    try:
        with open(_keys_path) as f:
            _keys = json.load(f)
        _GH_TOKEN = _keys.get('github_token')
        _TWITTER = _keys.get('twitter', {})
    except:
        pass

def _req(url):
    headers = {'User-Agent': 'HermesBot/1.0', 'Accept': 'application/vnd.github.v3+json'}
    if _GH_TOKEN:
        headers['Authorization'] = f'token {_GH_TOKEN}'
    return Request(url, headers=headers)

def _get(url, timeout=12):
    return json.loads(urlopen(_req(url), timeout=timeout).read().decode())

def _today():
    return datetime.now().strftime('%Y-%m-%d')

# ===== GitHub 搜索 =====

def github_search(query, per_page=15):
    """GitHub API搜索仓库"""
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

def _delay():
    import time; time.sleep(1.5)

# ===== Twitter/X 搜索 =====

def twitter_search(query, max_results=10):
    """用 OAuth 1.0 搜推文（暂不可用，等用户配好）"""
    if not _TWITTER.get('consumer_key'):
        return []
    from requests_oauthlib import OAuth1
    import requests
    auth = OAuth1(
        _TWITTER['consumer_key'], _TWITTER['consumer_secret'],
        _TWITTER['access_token'], _TWITTER['access_token_secret']
    )
    q = quote(query)
    url = f'https://api.twitter.com/2/tweets/search/recent?query={q}&max_results={max_results}&tweet.fields=public_metrics,created_at'
    try:
        resp = requests.get(url, auth=auth, timeout=10)
        if resp.status_code != 200:
            print(f'[warn] Twitter API error: {resp.status_code}', file=sys.stderr)
            return []
        items = []
        for tweet in resp.json().get('data', []):
            items.append({
                'type': 'twitter', 'name': tweet.get('text', '')[:120],
                'url': f"https://x.com/i/status/{tweet['id']}",
                'description': tweet.get('text', '')[:200],
                'stars': tweet.get('public_metrics', {}).get('like_count', 0),
                'source': 'Twitter'
            })
        return items
    except Exception as e:
        print(f'[warn] Twitter search failed: {e}', file=sys.stderr)
        return []

# ===== Hacker News =====

def hn_search(max_items=15):
    """Hacker News 最新热门"""
    try:
        ids = _get('https://hacker-news.firebaseio.com/v0/topstories.json')[:max_items]
        items = []
        for sid in ids:
            story = _get(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json')
            if story and story.get('type') == 'story' and story.get('title'):
                items.append({
                    'type': 'hn',
                    'name': story['title'][:120],
                    'url': story.get('url', f'https://news.ycombinator.com/item?id={sid}'),
                    'description': (story.get('title', '') or '')[:200],
                    'stars': story.get('score', 0),
                    'source': 'Hacker News'
                })
        return items
    except Exception as e:
        print(f'[warn] HN failed: {e}', file=sys.stderr)
        return []

# ===== Reddit =====

def reddit_search(subreddit, limit=10):
    """搜 Reddit 子版块热门帖"""
    url = f'https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}'
    try:
        req = Request(url, headers={'User-Agent': 'HermesBot/1.0'})
        data = json.loads(urlopen(req, timeout=10).read().decode())
        items = []
        for post in data.get('data', {}).get('children', []):
            p = post['data']
            items.append({
                'type': 'reddit',
                'name': p.get('title', '')[:120],
                'url': f"https://reddit.com{p.get('permalink', '')}",
                'description': (p.get('selftext', '') or p.get('title', ''))[:200],
                'stars': p.get('score', 0),
                'source': f'r/{subreddit}'
            })
        return items
    except Exception as e:
        print(f'[warn] Reddit failed: {e}', file=sys.stderr)
        return []

# ===== TopHub（中文热榜聚合） =====

def tophub_search():
    """tophub.today 中文热榜聚合"""
    url = 'https://tophub.today/'
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urlopen(req, timeout=10).read().decode('utf-8')
        items = []
        # 提取热门条目
        for match in re.finditer(r'<a[^>]*href="(https?://[^"]+)"[^>]*class="[^"]*cc-cd-cb-[^"]*"[^>]*>(.*?)</a>.*?<span[^>]*class="[^"]*e.[^"]*"[^>]*>(\d+)</span>', html, re.DOTALL):
            name = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            if name:
                items.append({
                    'type': 'hotlist',
                    'name': name[:120],
                    'url': match.group(1),
                    'description': '',
                    'stars': int(match.group(3)),
                    'source': '热榜'
                })
        return items[:20]
    except Exception as e:
        print(f'[warn] TopHub failed: {e}', file=sys.stderr)
        return []

# ===== 综合采集 =====

def collect_standard(results):
    """所有模式公用的标准数据源"""
    results.extend(hn_search(10))
    _delay()
    results.extend(reddit_search('MachineLearning', 8))
    _delay()
    results.extend(reddit_search('LocalLLaMA', 8))
    _delay()
    results.extend(tophub_search())
    return results

def collect_daily():
    """日报：昨天到今天的新项目"""
    yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    results = []

    # GitHub
    results.extend(github_search(
        f'created:>{yesterday} stars:>5 (ai OR llm OR gpt OR agent OR "machine learning") sort:stars-desc',
        per_page=25
    ))
    _delay()
    results.extend(github_search(
        f'created:>{yesterday} stars:>50 sort:stars-desc',
        per_page=15
    ))

    # Twitter
    _delay()
    results.extend(twitter_search('AI open source project OR AI tool OR new LLM release', 8))

    # 其他源
    results = collect_standard(results)

    return _dedup(results)


def collect_weekly():
    """周报：上周的项目"""
    week_ago = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d')
    results = []

    # GitHub
    results.extend(github_search(
        f'created:>{week_ago} stars:>20 (ai OR llm OR gpt OR agent OR "machine learning") sort:stars-desc',
        per_page=25
    ))
    _delay()
    results.extend(github_search(
        f'created:>{week_ago} stars:>100 sort:stars-desc',
        per_page=15
    ))

    # 其他源
    results = collect_standard(results)

    return _dedup(results)

def collect_monthly():
    """月报：上个月的项目"""
    month_ago = (datetime.now() - timedelta(days=32)).strftime('%Y-%m-%d')
    today = _today()
    results = []

    # AI核心高星项目
    results.extend(github_search(
        f'created:>{month_ago} stars:>100 (ai OR llm OR gpt OR agent OR "machine learning") sort:stars-desc',
        per_page=30
    ))
    # 通用高星项目
    results.extend(github_search(
        f'created:>{month_ago} stars:>500 sort:stars-desc',
        per_page=20
    ))

    return _dedup(results)

def _dedup(items):
    """按URL去重"""
    seen = set()
    unique = []
    for item in items:
        if item['url'] not in seen:
            seen.add(item['url'])
            unique.append(item)
    return unique

def read_tracker():
    """读取感兴趣的项目追踪"""
    path = os.path.expanduser('~/.hermes/scripts/ai_interest_tracker.json')
    try:
        with open(path) as f:
            return json.load(f).get('projects', [])
    except:
        return []

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    if mode == 'daily':
        data = collect_daily()
    elif mode == 'weekly':
        data = collect_weekly()
    elif mode == 'monthly':
        data = collect_monthly()
    else:
        print(f'Usage: {sys.argv[0]} [daily|weekly|monthly]', file=sys.stderr)
        sys.exit(1)

    print(json.dumps({'items': data, 'tracked': read_tracker(), 'mode': mode}, ensure_ascii=False, indent=2))
