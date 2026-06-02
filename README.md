# AI 新玩意简报系统

代码采集 → HTML 渲染 → 邮件推送

## 目录结构

```
src/
├── config.py          ← 全局配置（环境变量注入）
├── collector/         ← 数据采集（GitHub API + HN/Reddit/热榜）
├── storage/           ← 持久化存储
├── digest/            ← HTML 模板 + 邮件发送
└── internalization/   ← 二次内化（本地运行，GHA 跳过）
main.py                ← 主入口
.github/workflows/     ← GHA 定时任务
```

## 使用

```bash
# 本地运行
python3 main.py weekly

# 环境变量
export GITHUB_TOKEN=ghp_xxx
export QQ_SMTP_PASS=xxx       # QQ邮箱SMTP授权码
export AI_BRIEFING_TO=xxx     # 收件人（可选，默认 sunzcdev@gmail.com）
```

## GHA 定时

- **每周一 7:00** → 周报
- **每月1号 7:00** → 月报
- 手动触发：Actions → AI 简报 → workflow_dispatch

### 需配置的 Secrets

| Secret | 说明 |
|--------|------|
| `QQ_SMTP_PASS` | QQ邮箱SMTP授权码 |
| `AI_BRIEFING_TO` | 收件人（可选） |

`GITHUB_TOKEN` 由 Actions 自动提供。
