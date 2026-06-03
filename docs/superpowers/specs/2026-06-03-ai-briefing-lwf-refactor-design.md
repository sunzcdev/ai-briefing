# AI 简报 LWF 重构设计

## 背景

将 ai-briefing 从旧有的 `main.py` 一把梭架构 + `store/git` 桥，重构为 LWF 标准的多步骤流水线架构，对齐 ai-daily-learning 的模式。

## 架构

```
detect → collect → llm(提取) → store/rclone → notify/email
         │            │             │             │
    data/mode.txt  data/collect  data/digest   ☁️ 坚果云  📧 邮件
```

所有步骤跑在 GHA，无 local runner，无 artifact。

## 步骤详情

### detect — detect/script
- 脚本: `scripts/detect-mode.sh`（已有，基本不改）
- 输出: 通过 `GITHUB_OUTPUT` 输出 `mode` 变量

### collect — collect/script
- 脚本: `scripts/collect.py`（已有，微调）
- 输入: `mode` 参数
- 依赖核心库 `src/collector/ai_briefing_collector.py`
- 输出: `data/collect.json`

### llm — process/llm
- 脚本: `scripts/digest.py`（改为被 llm 步骤调用的 prompt 模式）
- 模型: 配置化（默认 gpt-4o）
- 输入: `data/collect.json`
- 输出: `data/digest.json`
- system_prompt: 通过 GitHub Variable `SYSTEM_PROMPT` 注入

### sync — store/rclone
- 远程: 坚果云 webdav
- 源: `data/`
- 目标: `notebook/学/AI简报/`

### notify — notify/email
- 发件: `james.sun@qq.com`
- 收件: `james.sun@qq.com`
- 主题: ✅ AI 简报

## Secrets（6个）

| Secret | 值示例 | 用途 |
|--------|--------|------|
| `LLM_KEY` | GitHub PAT | GitHub Models API |
| `RCLONE_USER` | 坚果云账号 | rclone |
| `RCLONE_PASS` | 坚果云应用密码 | rclone |
| `EMAIL_FROM` | james.sun@qq.com | SMTP 发件 |
| `EMAIL_PASS` | QQ 邮箱授权码 | SMTP 密码 |
| `EMAIL_TO` | james.sun@qq.com | SMTP 收件 |

## Variables（1个）

| Variable | 用途 |
|----------|------|
| `SYSTEM_PROMPT` | LLM 提取的 system prompt |

## 与 ai-daily-learning 对齐点

1. 步骤命名规范一致（detect/collect/llm/sync/notify）
2. store/rclone 取代 store/git
3. 无 artifact，无 local runner
4. Secrets 命名一致
5. process/llm 的 prompt 用 `vars.` 注入

## 无需改动

- `src/collector/ai_briefing_collector.py` — 采集逻辑不动
- `src/curator.py` — 精选逻辑不动
- `src/digest/ai_digest_template.html` — 模板不动
- `src/digest/send_ai_briefing.py` — 发送逻辑不动
