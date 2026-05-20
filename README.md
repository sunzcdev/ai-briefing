# AI 新玩意简报系统

代码采集 → LLM 润色 → Apple 风格 HTML → 邮件推送 → 二次内化闭环

## 目录结构

```
src/
├── collector/        ← 代码采集（GitHub API + 免费源）
├── storage/          ← 持久化存储 + 兴趣图谱
├── digest/           ← 润色 + HTML 生成 + 邮件发送
└── internalization/  ← 二次内化（用户标记→采集→分析→图谱）
data/                 ← 运行时数据
tests/                ← 测试
```

## 工作流

```
cron (每天7:00)
  → 判断模式（月报/周报/跳过）
  → collector 采集
  → LLM 精选+排版
  → HTML 生成 + 邮件发送
  → (新) 用户标记 → internalization 二次内化 → 优化下次精选
```

## 核心原则

- **代码干体力活，LLM 只做润色**
- **只发周报（周一）和月报（1号）**，不发日报
- 收件人：sunzcdev@gmail.com

## 历史脚本

原始脚本仍在 `~/.hermes/scripts/` 运行中，新功能直接在此项目开发。
