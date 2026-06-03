# AI Briefing LWF Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor ai-briefing from main.py all-in-one + store/git to LWF multi-step pipeline with store/rclone, aligned with ai-daily-learning.

**Architecture:** 5-step GHA pipeline: detect → collect → digest(script→LLM) → sync(rclone→坚果云) → notify(email). No artifact, no local runner.

**Tech Stack:** LWF framework, rclone (WebDAV/坚果云), GitHub Models API (gpt-4o), SMTP (QQ邮箱)

---

### Task 1: Rewrite workflow.yaml

**Files:**
- Modify: `workflow.yaml` (full rewrite)
- Generated: `.github/workflows/ai-briefing.yml` (via lwf deploy)

- [ ] **Step 1: Write new workflow.yaml**

```yaml
name: ai-briefing
trigger:
  schedule: "0 23 * * *"        # UTC 23:00 = 北京 07:00
  workflow_dispatch:
    inputs:
      mode:
        description: "模式: daily/weekly/monthly"
        default: "daily"

steps:
  # ── 第一步：检测模式 ──
  - id: detect
    runner: gha
    capability: detect
    using: script
    config:
      file: scripts/detect-mode.sh

  # ── 第二步：采集 ──
  - id: collect
    runner: gha
    depends: [detect]
    capability: collect
    using: script
    config:
      file: scripts/collect.py

  # ── 第三步：LLM 精选 ──
  - id: digest
    runner: gha
    depends: [collect]
    capability: process
    using: script
    config:
      file: scripts/digest.py

  # ── 第四步：同步到坚果云 ──
  - id: sync
    runner: gha
    depends: [digest]
    capability: store
    using: rclone
    config:
      remote: "jianguoyun"
      type: "webdav"
      url: "https://dav.jianguoyun.com/dav/"
      vendor: "other"
      user_secret: "RCLONE_USER"
      pass_secret: "RCLONE_PASS"
      source: "data/"
      target: "notebook/学/AI简报/"

  # ── 第五步：邮件通知 ──
  - id: notify
    runner: gha
    depends: [digest]
    optional: true
    capability: notify
    using: email
    config:
      to: "james.sun@qq.com"
      subject: "✅ AI 简报"
```

Key changes from current:
- Removed store/git bridge
- Added store/rclone + notify/email
- digest 改为 process/script（包装 LLM 调用，流程更可控）
- All 5 steps run on GHA, no artifact

- [ ] **Step 2: lwf deploy to generate GHA YML**

Run: `lwf deploy workflow.yaml`
Expected: `.github/workflows/ai-briefing.yml` generated

- [ ] **Step 3: Verify generated YML is valid**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ai-briefing.yml')); print('YAML OK')"`
Expected: `YAML OK`

- [ ] **Step 4: Commit**

```bash
git add workflow.yaml .github/workflows/ai-briefing.yml
git commit -m "lwf: rewrite pipeline — detect→collect→digest→rclone→email"
```

---

### Task 2: Adjust scripts for new secrets/config

**Files:**
- Modify: `scripts/collect.py` — read EMAIL_TO from env
- Modify: `scripts/digest.py` — ensure clean output for rclone
- Modify: `scripts/send.py` — read EMAIL_TO from env, correct email config
- No change: `scripts/detect-mode.sh`, `src/collector/`, `src/curator.py`, `src/digest/`

- [ ] **Step 1: Update collect.py — add EMAIL_TO env support**

Current collect.py outputs `data/collect.json` with all items. It already handles this correctly. Just verify no changes needed — the collect step doesn't need email config.

- [ ] **Step 2: Update digest.py — ensure digest.json is rclone-ready**

digest.py reads `data/collect.json`, calls `curate()` (LLM), and writes `data/digest.json`. Ensure:
- digest.json is self-contained (no external paths)
- All content fields are strings (for rclone sync to work cleanly)

Current code handles this. Verify and leave unchanged unless issues found.

- [ ] **Step 3: Update send.py — read EMAIL_TO from env**

Current send.py reads `EMAIL_TO` env var with `DEFAULT_TO_EMAIL` fallback from src/config. Need to:
```python
# Change DEFAULT_TO_EMAIL in src/config.py
# OR just rely on env EMAIL_TO
```

Check src/config.py for `DEFAULT_TO_EMAIL` and update it to `james.sun@qq.com`.

- [ ] **Step 4: Update src/config.py — correct defaults**

```python
DEFAULT_TO_EMAIL = "james.sun@qq.com"  # was probably different
```

Also add `EMAIL_FROM` and `EMAIL_PASS` env reading for SMTP auth.

- [ ] **Step 5: Commit**

```bash
git add scripts/collect.py scripts/digest.py scripts/send.py src/config.py
git commit -m "fix: align email config with new secrets convention"
```

---

### Task 3: Deploy, set secrets, verify

- [ ] **Step 1: Push to origin**

```bash
git push origin lwf
```

- [ ] **Step 2: Set repository secrets**

```bash
gh secret set LLM_KEY -R sunzcdev/ai-briefing <<< "$(cat ~/.ssh/...)"

gh secret set RCLONE_USER -R sunzcdev/ai-briefing <<< "坚果云账号"
gh secret set RCLONE_PASS -R sunzcdev/ai-briefing <<< "坚果云应用密码"

gh secret set EMAIL_FROM -R sunzcdev/ai-briefing <<< "james.sun@qq.com"
gh secret set EMAIL_TO -R sunzcdev/ai-briefing <<< "james.sun@qq.com"
gh secret set EMAIL_PASS -R sunzcdev/ai-briefing <<< "QQ邮箱授权码"
```

(Won't execute actual secret values in plan — will prompt user during execution)

- [ ] **Step 3: Set SYSTEM_PROMPT variable**

```bash
gh variable set SYSTEM_PROMPT -R sunzcdev/ai-briefing <<< "你是AI领域的资讯编辑..."
```

- [ ] **Step 4: Manual trigger to verify**

```bash
gh workflow run ai-briefing -R sunzcdev/ai-briefing --ref lwf -f mode=daily
```

- [ ] **Step 5: Check run status**

```bash
gh run view -R sunzcdev/ai-briefing
```
