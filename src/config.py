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

# ── LLM 配置（可选，用于 internalization） ────
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
LLM_API_URL = os.environ.get(
    'LLM_API_URL',
    'https://api.deepseek.com/v1/chat/completions'
)
LLM_MODEL = os.environ.get('LLM_MODEL', 'deepseek-chat')

# ── 运行模式 ──────────────────────────────────
SKIP_INTERNALIZATION = os.environ.get(
    'AI_BRIEFING_SKIP_INTERNALIZATION', ''
).lower() in ('1', 'true', 'yes')
