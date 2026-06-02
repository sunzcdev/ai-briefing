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


def _today():
    return datetime.now().strftime('%Y-%m-%d')


# ===== GitHub 搜索 =====

def github_search(query, per_page=15):
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


# ===== Hacker News =====

def hn_search(max_items=15):
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
                    'source': '热榜'
                })
        return items[:20]
    except Exception as e:
        print(f'[warn] TopHub failed: {e}', file=sys.stderr)
        return []


# ===== Twitter/X =====

def twitter_search(query, max_results=10):
    consumer_key = os.environ.get('TWITTER_CONSUMER_KEY', '')
    if not consumer_key:
        return []
    from requests_oauthlib import OAuth1
    import requests
    auth = OAuth1(
        consumer_key,
        os.environ.get('TWITTER_CONSUMER_SECRET', ''),
        os.environ.get('TWITTER_ACCESS_TOKEN', ''),
        os.environ.get('TWITTER_ACCESS_SECRET', '')
    )
    q = quote(query)
    url = f'https://api.twitter.com/2/tweets/search/recent?query={q}&max_results={max_results}&tweet.fields=public_metrics,created_at'
    try:
        resp = requests.get(url, auth=auth, timeout=10)
        if resp.status_code != 200:
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
        return []


# ===== 综合采集 =====

def collect_standard(results):
    results.extend(hn_search(10))
    _delay()
    results.extend(reddit_search('MachineLearning', 8))
    _delay()
    results.extend(reddit_search('LocalLLaMA', 8))
    _delay()
    results.extend(tophub_search())
    return results


def collect_daily():
    yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    results = []
    results.extend(github_search(
        f'created:>{yesterday} stars:>5 (ai OR llm OR gpt OR agent OR "machine learning") sort:stars-desc',
        per_page=25
    ))
    _delay()
    results.extend(github_search(
        f'created:>{yesterday} stars:>50 sort:stars-desc',
        per_page=15
    ))
    _delay()
    results.extend(twitter_search('AI open source project OR AI tool OR new LLM release', 8))
    results = collect_standard(results)
    return _dedup(results)


def collect_weekly():
    week_ago = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d')
    results = []
    results.extend(github_search(
        f'created:>{week_ago} stars:>20 (ai OR llm OR gpt OR agent OR "machine learning") sort:stars-desc',
        per_page=25
    ))
    _delay()
    results.extend(github_search(
        f'created:>{week_ago} stars:>100 sort:stars-desc',
        per_page=15
    ))
    results = collect_standard(results)
    return _dedup(results)


def collect_monthly():
    month_ago = (datetime.now() - timedelta(days=32)).strftime('%Y-%m-%d')
    results = []
    results.extend(github_search(
        f'created:>{month_ago} stars:>100 (ai OR llm OR gpt OR agent OR "machine learning") sort:stars-desc',
        per_page=30
    ))
    results.extend(github_search(
        f'created:>{month_ago} stars:>500 sort:stars-desc',
        per_page=20
    ))
    return _dedup(results)


def _dedup(items):
    seen = set()
    unique = []
    for item in items:
        if item['url'] not in seen:
            seen.add(item['url'])
            unique.append(item)
    return unique


def read_tracker():
    try:
        with open(TRACKER_PATH) as f:
            return json.load(f).get('projects', [])
    except:
        return []


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    funcs = {'daily': collect_daily, 'weekly': collect_weekly, 'monthly': collect_monthly}
    if mode not in funcs:
        print(f'Usage: {sys.argv[0]} [daily|weekly|monthly]', file=sys.stderr)
        sys.exit(1)
    data = funcs[mode]()
    print(json.dumps({'items': data, 'tracked': read_tracker(), 'mode': mode}, ensure_ascii=False, indent=2))
