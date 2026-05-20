#!/usr/bin/env python3
"""内部化模块冒烟测试"""

import json, os, sys, tempfile, time

# 切到项目目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, 'src'))

passed = 0
failed = 0

def check(name, cond, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print(f'  ✅ {name}')
    else:
        failed += 1
        print(f'  ❌ {name} {detail}')

# ==== test 1: import ====
print('\n=== 模块导入 ===')
try:
    from internalization import storage, collector, analyzer, graph, selector
    check('所有模块导入成功', True)
except Exception as e:
    check(f'模块导入失败: {e}', False)

# ==== test 2: storage mark/read ====
print('\n=== 存储 ===')
from internalization import storage as st

item_id = f'test-{int(time.time())}'
marked_at = st.save_mark(item_id, 'test/repo', 'https://github.com/test/repo')
check('保存标记成功', bool(marked_at))

marks = st.get_marks(days=30)
check('读取标记', any(m['item_id'] == item_id for m in marks))

# ==== test 3: collector (mock) ====
print('\n=== 采集器 ===')
from internalization import collector as col

# 解析 URL
owner, repo = col.extract_owner_repo('https://github.com/torvalds/linux')
check('解析 GitHub URL', owner == 'torvalds' and repo == 'linux')

owner2, repo2 = col.extract_owner_repo('torvalds/linux')
check('解析 owner/repo', owner2 == 'torvalds' and repo2 == 'linux')

# 保存模拟采集数据
mock_data = {
    'name': 'test/example', 'stars': 100, 'forks': 20,
    'description': '测试项目', 'language': 'Python',
    'topics': ['ai', 'llm', 'testing'], 'license': 'MIT',
    'recent_commits': [{'sha': 'abc1234', 'message': 'fix bug', 'date': '2026-05-20', 'author': 'test'}],
    'releases': [{'tag': 'v1.0', 'name': 'First release', 'published': '2026-05-01', 'prerelease': False}]
}
st.save_collected(item_id, mock_data)
loaded = st.load_collected(item_id)
check('保存和读取采集数据', loaded and loaded['name'] == 'test/example')

# ==== test 4: analyzer prompt ====
print('\n=== 分析器 ===')
from internalization import analyzer as an

prompt = an.build_analysis_prompt(mock_data)
check('生成分析 prompt', 'user_value' in prompt and 'hermes_value' in prompt)

# 测试解析
test_response = '```json\n{"user_value": {"score": 8, "reason": "不错", "tags": ["AI"]}, "hermes_value": {"score": 7, "reason": "可用", "tags": ["写作素材"]}}\n```'
parsed = an.parse_analysis_response(test_response)
check('解析 LLM 响应', parsed['user_value']['score'] == 8 and parsed['hermes_value']['score'] == 7)

# ==== test 5: graph ====
print('\n=== 兴趣图谱 ===')
from internalization import graph as ig

g = ig.load()
check('加载空图谱', 'categories' in g and 'keywords' in g)

analysis = {
    'user_value': {'score': 8, 'reason': '好项目', 'tags': ['AI/LLM', '开发者工具']},
    'hermes_value': {'score': 7, 'reason': '有用', 'tags': ['写作素材']}
}
updated = ig.update_from_analysis('test-graph-1', analysis, mock_data)
check('更新图谱', len(updated['keywords']) > 0)
check('图谱含 AI/LLM 分类', 'AI/LLM' in updated['categories'] or '开发者工具' in updated['categories'])

score = ig.get_relevance_score('test/example', ['ai', 'llm', 'testing'], 'Python')
check('兴趣匹配得分 > 0', score > 0.0)

# ==== test 6: selector ====
print('\n=== 精选排序 ===')
from internalization import selector as sel

items = [
    {'name': 'test/example', 'topics': ['ai', 'llm'], 'language': 'Python', 'stars': 100},
    {'name': 'unrelated/thing', 'topics': ['css'], 'language': 'HTML', 'stars': 50},
]
sorted_result = sel.select_and_rank(items)
check('排序结果含 summary', 'summary' in sorted_result)
check('推荐列表有项目', len(sorted_result.get('recommended', [])) > 0)

# ==== 汇总 ====
print(f'\n=== 结果: {passed} 通过, {failed} 失败 ===')
sys.exit(0 if failed == 0 else 1)
