#!/usr/bin/env python3
"""
AI 简报持久化存储模块
管理日报数据的持久化存储和读取，供周报/月报提炼使用。
数据存储在 ~/.hermes/data/ai_briefing/（不是 cache，不会清理）

用法：
  # 保存日报精选
  python3 ai_briefing_storage.py save 2026-05-19 '[
    {"name":"项目名","url":"...","description":"...","reason":"精选理由","tag":"开源项目","stars":123},
    ...
  ]'

  # 读取最近 N 天的日报数据
  python3 ai_briefing_storage.py read 7

  # 追加用户反馈
  python3 ai_briefing_storage.py feedback '{"source":"email","content":"这个项目不错","date":"2026-05-19"}'

  # 读取所有用户反馈
  python3 ai_briefing_storage.py read-feedback
"""
import json
import os
import sys
from datetime import datetime, timedelta

DATA_DIR = os.path.expanduser('~/.hermes/data/ai_briefing')
INDEX_FILE = os.path.join(DATA_DIR, 'index.json')
FEEDBACK_FILE = os.path.join(DATA_DIR, 'feedback.jsonl')


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_index():
    _ensure_dir()
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE) as f:
            return json.load(f)
    return {"daily_files": []}


def _save_index(index):
    _ensure_dir()
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def cmd_save(date_str, items_json):
    """保存某一日的日报精选到 data 目录"""
    _ensure_dir()
    items = json.loads(items_json)
    file_path = os.path.join(DATA_DIR, f'daily_{date_str}.json')
    data = {
        "date": date_str,
        "items": items,
        "saved_at": datetime.now().isoformat()
    }
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 更新索引
    index = _load_index()
    # 替换或追加
    existing = [e for e in index['daily_files'] if e['date'] != date_str]
    existing.append({"date": date_str, "file": f'daily_{date_str}.json'})
    index['daily_files'] = sorted(existing, key=lambda x: x['date'])
    _save_index(index)
    print(f"OK: saved {len(items)} items for {date_str}")


def cmd_read(days):
    """读取最近 N 天的日报数据"""
    _ensure_dir()
    index = _load_index()
    cutoff = (datetime.now() - timedelta(days=int(days))).strftime('%Y-%m-%d')

    result = []
    for entry in index['daily_files']:
        if entry['date'] >= cutoff:
            file_path = os.path.join(DATA_DIR, entry['file'])
            if os.path.exists(file_path):
                with open(file_path, encoding='utf-8') as f:
                    data = json.load(f)
                    result.append(data)

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_feedback(feedback_json):
    """追加用户反馈"""
    _ensure_dir()
    entry = json.loads(feedback_json)
    if 'date' not in entry:
        entry['date'] = datetime.now().strftime('%Y-%m-%d')
    if 'timestamp' not in entry:
        entry['timestamp'] = datetime.now().isoformat()
    with open(FEEDBACK_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    print("OK: feedback saved")


def cmd_read_feedback():
    """读取所有用户反馈"""
    _ensure_dir()
    if not os.path.exists(FEEDBACK_FILE):
        print("[]")
        return
    entries = []
    with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    print(json.dumps(entries, ensure_ascii=False, indent=2))


def cmd_list():
    """列出所有已保存的日报日期"""
    index = _load_index()
    dates = [e['date'] for e in index['daily_files']]
    print(f"Total daily entries: {len(dates)}")
    for d in dates[-30:]:
        print(f"  {d}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'save' and len(sys.argv) >= 4:
        cmd_save(sys.argv[2], sys.argv[3])
    elif cmd == 'read' and len(sys.argv) >= 3:
        cmd_read(sys.argv[2])
    elif cmd == 'feedback' and len(sys.argv) >= 3:
        cmd_feedback(sys.argv[2])
    elif cmd == 'read-feedback':
        cmd_read_feedback()
    elif cmd == 'list':
        cmd_list()
    else:
        print(f"Unknown command or missing args: {cmd}")
        print(__doc__)
        sys.exit(1)
