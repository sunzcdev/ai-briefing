#!/usr/bin/env python3
"""
AI 简报持久化存储模块
用法见 __doc__ 或 python3 src/storage/ai_briefing_storage.py
"""
import json, os, sys
from datetime import datetime, timedelta

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.config import DATA_DIR

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
    _ensure_dir()
    items = json.loads(items_json)
    file_path = os.path.join(DATA_DIR, f'daily_{date_str}.json')
    data = {"date": date_str, "items": items, "saved_at": datetime.now().isoformat()}
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    index = _load_index()
    existing = [e for e in index['daily_files'] if e['date'] != date_str]
    existing.append({"date": date_str, "file": f'daily_{date_str}.json'})
    index['daily_files'] = sorted(existing, key=lambda x: x['date'])
    _save_index(index)
    print(f"OK: saved {len(items)} items for {date_str}")


def cmd_read(days):
    _ensure_dir()
    cutoff = (datetime.now() - timedelta(days=int(days))).strftime('%Y-%m-%d')
    result = []
    for entry in _load_index()['daily_files']:
        if entry['date'] >= cutoff:
            fp = os.path.join(DATA_DIR, entry['file'])
            if os.path.exists(fp):
                with open(fp, encoding='utf-8') as f:
                    result.append(json.load(f))
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_feedback(feedback_json):
    _ensure_dir()
    entry = json.loads(feedback_json)
    entry.setdefault('date', datetime.now().strftime('%Y-%m-%d'))
    entry.setdefault('timestamp', datetime.now().isoformat())
    with open(FEEDBACK_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    print("OK: feedback saved")


def cmd_read_feedback():
    _ensure_dir()
    if not os.path.exists(FEEDBACK_FILE):
        print("[]"); return
    entries = [json.loads(line) for line in open(FEEDBACK_FILE, encoding='utf-8') if line.strip()]
    print(json.dumps(entries, ensure_ascii=False, indent=2))


def cmd_list():
    dates = [e['date'] for e in _load_index()['daily_files']]
    print(f"Total: {len(dates)}")
    for d in dates[-30:]:
        print(f"  {d}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmds = {
        'save': lambda: cmd_save(sys.argv[2], sys.argv[3]) if len(sys.argv) >= 4 else print(__doc__),
        'read': lambda: cmd_read(sys.argv[2]) if len(sys.argv) >= 3 else print(__doc__),
        'feedback': lambda: cmd_feedback(sys.argv[2]) if len(sys.argv) >= 3 else print(__doc__),
        'read-feedback': cmd_read_feedback,
        'list': cmd_list,
    }
    sys.argv[1] in cmds and cmds[sys.argv[1]]() or print(f"Unknown: {sys.argv[1]}")
