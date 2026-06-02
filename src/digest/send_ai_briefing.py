#!/usr/bin/env python3
"""Send AI briefing HTML email via QQ SMTP, with plain text fallback.

Usage:
  cat briefing.html | python3 src/digest/send_ai_briefing.py 'Subject' [recipient]
"""
import smtplib, sys, re, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.config import QQ_EMAIL, QQ_SMTP_PASS, QQ_SMTP_HOST, QQ_SMTP_PORT, DEFAULT_TO_EMAIL


def html_to_plain_text(html):
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'</?(?:br|p|div|tr|li|h[1-6])[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    for e, r in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&nbsp;', ' '), ('&quot;', '"')]:
        text = text.replace(e, r)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def send(html_content, subject, to_email=DEFAULT_TO_EMAIL):
    msg = MIMEMultipart('alternative')
    msg['From'] = QQ_EMAIL
    msg['To'] = to_email
    msg['Subject'] = Header(subject, 'utf-8')
    msg.attach(MIMEText(html_to_plain_text(html_content), 'plain', 'utf-8'))
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    with smtplib.SMTP_SSL(QQ_SMTP_HOST, QQ_SMTP_PORT) as s:
        s.login(QQ_EMAIL, QQ_SMTP_PASS)
        s.sendmail(QQ_EMAIL, [to_email], msg.as_string())
    print('OK')


if __name__ == '__main__':
    if not QQ_SMTP_PASS:
        print('[error] QQ_SMTP_PASS not set.', file=sys.stderr); sys.exit(1)
    send(html=sys.stdin.read(), subject=sys.argv[1] if len(sys.argv) > 1 else 'AI/IT 行业早报',
         to_email=sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TO_EMAIL)
