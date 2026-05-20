#!/usr/bin/env python3
"""Send AI briefing HTML email via QQ SMTP, with plain text fallback.

Usage:
  cat briefing.html | python3 send_ai_briefing.py 'Subject' [recipient]
  
  If recipient omitted, defaults to sunzcdev@gmail.com.
"""
import smtplib
import sys
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

SMTP_HOST = 'smtp.qq.com'
SMTP_PORT = 465
FROM_EMAIL = 'james.sun@qq.com'
FROM_PASS = 'QQ_SMTP_PASS_PLACEHOLDER'
DEFAULT_TO = 'sunzcdev@gmail.com'


def html_to_plain_text(html: str) -> str:
    """Strip HTML tags, keep readable text content for email fallback."""
    text = html
    # Remove scripts and styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    # Replace <br>, </p>, </div>, </tr> with newline
    text = re.sub(r'</?(?:br|p|div|tr|li|h[1-6])[^>]*>', '\n', text, flags=re.IGNORECASE)
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ').replace('&quot;', '"')
    # Remove excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +\n', '\n', text)
    return text.strip()


def send(html_content, subject, to_email=DEFAULT_TO):
    msg = MIMEMultipart('alternative')
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email
    msg['Subject'] = Header(subject, 'utf-8')

    # Plain text version first (used by WeChat notifications, etc.)
    plain_text = html_to_plain_text(html_content)
    msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))

    # HTML version second
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as s:
        s.login(FROM_EMAIL, FROM_PASS)
        s.sendmail(FROM_EMAIL, [to_email], msg.as_string())
    print('OK')


if __name__ == '__main__':
    html = sys.stdin.read()
    subject = sys.argv[1] if len(sys.argv) > 1 else 'AI/IT 行业早报'
    to_email = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TO
    send(html, subject, to_email)
