"""
AI 简报全局配置
所有路径/凭据通过环境变量注入，零硬编码。
"""

import os

# ── 数据目录 ──────────────────────────────────
DATA_DIR = os.environ.get(
    'AI_BRIEFING_DATA',
    os.path.expanduser('~/.hermes/data/ai_briefing')
)

CACHE_DIR = os.environ.get(
    'AI_BRIEFING_CACHE',
    os.path.expanduser('~/.hermes/cache/ai_briefing')
)

TRACKER_PATH = os.environ.get(
    'AI_BRIEFING_TRACKER',
    os.path.expanduser('~/.hermes/scripts/ai_interest_tracker.json')
)

# ── API 凭据 ──────────────────────────────────
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')

# QQ 邮箱 SMTP
QQ_EMAIL = os.environ.get('QQ_EMAIL', 'james.sun@qq.com')
QQ_SMTP_PASS = os.environ.get('QQ_SMTP_PASS', '')
QQ_SMTP_HOST = os.environ.get('QQ_SMTP_HOST', 'smtp.qq.com')
QQ_SMTP_PORT = int(os.environ.get('QQ_SMTP_PORT', '465'))

DEFAULT_TO_EMAIL = os.environ.get('AI_BRIEFING_TO', 'sunzcdev@gmail.com')

# ── LLM 精选配置（单 JSON 环境变量，防泄露公开仓库） ────
import json
_CURATOR_LLM_RAW = os.environ.get('CURATOR_LLM', '{}')
_CURATOR_LLM_CFG = json.loads(_CURATOR_LLM_RAW) if _CURATOR_LLM_RAW.strip() else {}
CURATOR_API_KEY = _CURATOR_LLM_CFG.get('api_key', '')
CURATOR_API_URL = _CURATOR_LLM_CFG.get('api_url', '')
CURATOR_MODEL = _CURATOR_LLM_CFG.get('model', '')

# ── 运行模式 ──────────────────────────────────
SKIP_INTERNALIZATION = os.environ.get(
    'AI_BRIEFING_SKIP_INTERNALIZATION', ''
).lower() in ('1', 'true', 'yes')
