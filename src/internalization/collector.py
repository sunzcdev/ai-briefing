#!/usr/bin/env python3
"""深度采集 — 标记后从 GitHub 抓详细信息"""

import json, os, sys, time
from urllib.request import urlopen, Request

GH_TOKEN = None
_keys_path = os.path.expanduser('~/.hermes/scripts/api_keys.json')
if os.path.exists(_keys_path):
    try:
        with open(_keys_path) as f:
            _keys = json.load(f)
        GH_TOKEN = _keys.get('github_token')
    except Exception:
        pass

DATA_DIR = os.path.expanduser('~/.hermes/data/ai_briefing/collected')
os.makedirs(DATA_DIR, exist_ok=True)

def _req(url):
    headers = {'User-Agent': 'HermesBot/1.0', 'Accept': 'application/vnd.github.v3+json'}
    if GH_TOKEN:
        headers['Authorization'] = f'token {GH_TOKEN}'
    return Request(url, headers=headers)

def _get(url):
    return json.loads(urlopen(_req(url), timeout=15).read().decode())

def extract_owner_repo(url_or_name):
    """从 URL 或 'owner/repo' 提取 owner, repo"""
    url_or_name = url_or_name.strip().rstrip('/')
    if 'github.com/' in url_or_name:
        parts = url_or_name.split('github.com/')[-1].split('/')
        if len(parts) >= 2:
            return parts[0], parts[1].split('/')[0].split('?')[0].split('#')[0]
    if '/' in url_or_name and not url_or_name.startswith('http'):
        parts = url_or_name.split('/')
        return parts[0], parts[1].split('?')[0].split('#')[0]
    return None, None

def collect_deep(url_or_name):
    """深度采集一个 GitHub 项目的详细信息"""
    owner, repo = extract_owner_repo(url_or_name)
    if not owner or not repo:
        return {'error': f'无法解析项目: {url_or_name}'}

    result = {'name': f'{owner}/{repo}', 'url': f'https://github.com/{owner}/{repo}'}

    # 基本信息
    try:
        repo_data = _get(f'https://api.github.com/repos/{owner}/{repo}')
        result['stars'] = repo_data.get('stargazers_count', 0)
        result['forks'] = repo_data.get('forks_count', 0)
        result['description'] = (repo_data.get('description') or '').strip()
        result['language'] = repo_data.get('language') or ''
        result['topics'] = repo_data.get('topics', [])
        result['license'] = (repo_data.get('license') or {}).get('spdx_id', '')
        result['created_at'] = repo_data.get('created_at', '')[:10]
        result['updated_at'] = repo_data.get('updated_at', '')[:10]
        result['open_issues'] = repo_data.get('open_issues_count', 0)
    except Exception as e:
        result['error'] = f'获取仓库信息失败: {e}'
        return result

    # 最近提交
    try:
        time.sleep(0.5)
        commits = _get(f'https://api.github.com/repos/{owner}/{repo}/commits?per_page=5')
        result['recent_commits'] = [
            {'sha': c['sha'][:7], 'message': c['commit']['message'].split('\n')[0][:80],
             'date': c['commit']['committer']['date'][:10], 'author': c['commit']['author']['name']}
            for c in commits
        ]
    except Exception:
        result['recent_commits'] = []

    # 最新 release
    try:
        time.sleep(0.5)
        releases = _get(f'https://api.github.com/repos/{owner}/{repo}/releases?per_page=3')
        result['releases'] = [
            {'tag': r['tag_name'], 'name': r.get('name', '')[:60],
             'published': r['published_at'][:10], 'prerelease': r.get('prerelease', False)}
            for r in releases
        ]
    except Exception:
        result['releases'] = []

    # 保存
    item_id = f'{owner}_{repo}'.replace('.', '_').replace('/', '_')
    path = os.path.join(DATA_DIR, f'{item_id}.json')
    with open(path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    result['item_id'] = item_id
    return result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'用法: {sys.argv[0]} <github_url_or_name>')
        sys.exit(1)
    result = collect_deep(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
