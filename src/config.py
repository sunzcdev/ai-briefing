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

# QQ 邮箱 SMTP（统一用 EMAIL_* 命名，兼容旧名）
EMAIL_FROM = os.environ.get('EMAIL_FROM') or os.environ.get('QQ_EMAIL', 'james.sun@qq.com')
EMAIL_PASS = os.environ.get('EMAIL_PASS') or os.environ.get('QQ_SMTP_PASS', '')
EMAIL_TO = os.environ.get('EMAIL_TO') or os.environ.get('AI_BRIEFING_TO', 'james.sun@qq.com')

# SMTP 连接参数
QQ_SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.qq.com')
QQ_SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))

# ── LLM 精选配置 ──────────────────────────────
# 优先用 LLM_KEY（LWF 环境变量对齐），兼容旧 CURATOR_LLM JSON
LLM_API_KEY = os.environ.get('LLM_KEY', '')
LLM_API_URL = os.environ.get('LLM_API_URL', 'https://models.github.ai/inference/v1/chat/completions')
LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-4o')

# 旧兼容：CURATOR_LLM JSON 环境变量
import json
_CURATOR_LLM_RAW = os.environ.get('CURATOR_LLM', '{}')
_CURATOR_LLM_CFG = json.loads(_CURATOR_LLM_RAW) if _CURATOR_LLM_RAW.strip() else {}
CURATOR_API_KEY = _CURATOR_LLM_CFG.get('api_key', LLM_API_KEY)
CURATOR_API_URL = _CURATOR_LLM_CFG.get('api_url', LLM_API_URL)
CURATOR_MODEL = _CURATOR_LLM_CFG.get('model', LLM_MODEL)

# ── 运行模式 ──────────────────────────────────
SKIP_INTERNALIZATION = os.environ.get(
    'AI_BRIEFING_SKIP_INTERNALIZATION', ''
).lower() in ('1', 'true', 'yes')
