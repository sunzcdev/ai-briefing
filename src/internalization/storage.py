#!/usr/bin/env python3
"""内部化存储 — marks.jsonl + 采集数据 + 分析结果"""

import json, os, time

DATA_DIR = os.path.expanduser('~/.hermes/data/ai_briefing')
MARKS_FILE = os.path.join(DATA_DIR, 'marks.jsonl')
COLLECTED_DIR = os.path.join(DATA_DIR, 'collected')
ANALYZED_DIR = os.path.join(DATA_DIR, 'analyzed')

def _ensure():
    for d in [DATA_DIR, COLLECTED_DIR, ANALYZED_DIR]:
        os.makedirs(d, exist_ok=True)

# === 标记 ===

def save_mark(item_id, name, url, source='manual', extra=None):
    _ensure()
    entry = {
        'item_id': item_id, 'name': name, 'url': url,
        'source': source, 'marked_at': time.strftime('%Y-%m-%dT%H:%M:%S')
    }
    if extra:
        entry.update(extra)
    with open(MARKS_FILE, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry['marked_at']

def get_marks(days=30):
    _ensure()
    if not os.path.exists(MARKS_FILE):
        return []
    cutoff = time.time() - days * 86400
    marks = []
    with open(MARKS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            t = entry.get('marked_at', '')
            if t and time.mktime(time.strptime(t[:10], '%Y-%m-%d')) >= cutoff - 86400:
                marks.append(entry)
    return marks

# === 采集数据 ===

def save_collected(item_id, data):
    _ensure()
    path = os.path.join(COLLECTED_DIR, f'{item_id}.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_collected(item_id):
    path = os.path.join(COLLECTED_DIR, f'{item_id}.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def list_collected():
    _ensure()
    files = os.listdir(COLLECTED_DIR)
    items = []
    for fn in sorted(files):
        if fn.endswith('.json'):
            item_id = fn[:-5]
            data = load_collected(item_id)
            if data:
                items.append(data)
    return items

# === 分析结果 ===

def save_analysis(item_id, data):
    _ensure()
    path = os.path.join(ANALYZED_DIR, f'{item_id}.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_analysis(item_id):
    path = os.path.join(ANALYZED_DIR, f'{item_id}.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

def list_analyzed():
    _ensure()
    files = os.listdir(ANALYZED_DIR)
    items = []
    for fn in sorted(files):
        if fn.endswith('.json'):
            item_id = fn[:-5]
            data = load_analysis(item_id)
            if data:
                items.append(data)
    return items


if __name__ == '__main__':
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'mark' and len(sys.argv) >= 4:
        save_mark(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else '')
        print('OK')
    elif cmd == 'marks':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        marks = get_marks(days)
        print(json.dumps(marks, indent=2, ensure_ascii=False))
    elif cmd == 'collected':
        items = list_collected()
        print(json.dumps(items, indent=2, ensure_ascii=False))
    elif cmd == 'analyzed':
        items = list_analyzed()
        print(json.dumps(items, indent=2, ensure_ascii=False))
    else:
        print(__doc__)
