# AI 简报改造设计文档

## 概述

对 ai-briefing 项目进行四项改造：
1. **目录修正** — rclone 同步路径从 `学/AI简报/` 改为 `学/AI/AI简报/`
2. **MD 输出** — 在 HTML 邮件之外，生成 Markdown 文件同步到 Obsidian
3. **采集层重写** — 以 anysearch 为主数据源，替代 GitHub API 硬编码搜索
4. **跨期去重** — 读取历史已选项目，过滤重复内容

## 1. 目录修正

### 改动点
- `.github/workflows/ai-briefing.yml` 第57行：`rclone copy data/ jianguoyun:notebook/学/AI简报/` → `jianguoyun:notebook/学/AI/AI简报/`
- `workflow.yaml` 第35行：同理

### 影响
无。rclone 会在目标不存在时自动创建目录。

## 2. MD 输出

### 设计
在 `main.py` 的 HTML 渲染步骤之后，追加一个 `render_md()` 函数：

```python
def render_md(project_items, news_items, curated, mode='daily'):
    """生成 Obsidian 友好的 Markdown"""
    输出格式：
    
    # AI 新玩意早报 — 2026年6月4日 星期四
    
    ## 🔥 本周精选
    
    ### [项目名](url) ⭐1234
    > LLM 点评内容...
    
    ---
    
    ### 开源项目
    ...
    
    ### AI 热点事件
    ...
```

- 存为 `data/daily_20260604.md`
- rclone 同步时一起传到坚果云

### 规则
- 使用 Obsidian 兼容的 WikiLink 或标准 Markdown 链接
- LLM 点评用 blockquote `>` 包裹
- 项目分类展示（开源项目/新工具/新玩法/新模型）
- 热点事件单独区域
- 避免 HTML 标签

## 3. 采集层重写 — anysearch 为主源

### 数据流

```
anysearch (主源)
  ├── 搜索 AI/LLM/Agent 相关文章（batch_search 并行）
  ├── extract 拉取文章全文
  ├── 正则/GitHub URL 解析提取项目
  │
  └── GitHub API（辅助）
        ├── 补全 star 数、描述、语言
        └── 获取 trending 数据兜底
```

### anysearch 查询设计

```python
batch_search(
    query1="AI Agent framework open source 2026",
    query2="LLM tool building trending github",
    query3="大模型 智能体 开源项目",
    freshness="week",
    max_results=20,
)
```

### 跨期去重

- 读取 `data/` 下已有的 `daily_*.json` 历史记录
- 提取所有已选项目的 name + url
- 新采集到的项目与之比对，已出现的跳过

## 4. 密钥配置

- `ANYSEARCH_API_KEY` → GitHub repo secret
- Workflow env 中引用

## 无需改动

- HTML 邮件发送逻辑不变
- LLM 精选逻辑不变
- 存储逻辑不变
- rclone 同步机制不变
