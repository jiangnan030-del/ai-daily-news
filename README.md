# 🤖 AI 前沿日报 (AI Daily News)

> 每天自动聚合 GitHub Trending、Hacker News、arXiv 的 AI 前沿资讯，由 Google Gemini 智能摘要，发布到 GitHub Pages。

[![Daily News](https://github.com/jiangnan030-del/ai-daily-news/actions/workflows/daily-news.yml/badge.svg)](https://github.com/jiangnan030-del/ai-daily-news/actions/workflows/daily-news.yml)

## ✨ 特性

- 🔄 **全自动运行** — GitHub Actions 每日定时触发，零人工干预
- 📡 **多源聚合** — GitHub Trending + Hacker News + arXiv 三大 AI 信息源
- 🧠 **AI 智能摘要** — Google Gemini 自动生成中文摘要、评分和分类
- 🌐 **精美网站** — 自动构建 GitHub Pages 静态站点，支持暗黑/明亮主题
- 💰 **完全免费** — GitHub Actions + Gemini 免费额度，零成本运行
- 📊 **数据存档** — 每日原始数据以 JSON 格式归档，方便后续分析

## 📡 数据来源

| 来源 | 内容 | 频率 |
|------|------|------|
| 🔥 GitHub Trending | AI/ML 相关热门开源项目 | 每日 |
| 📰 Hacker News | AI 相关热门讨论和新闻 | 每日 |
| 📄 arXiv | 最新 AI 学术论文 (cs.AI/CL/CV/LG) | 每日 |

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角 **Fork** 按钮，将本仓库 Fork 到你的 GitHub 账户。

### 2. 配置 Gemini API Key

1. 前往 [Google AI Studio](https://aistudio.google.com/apikey) 免费获取 API Key
2. 进入你 Fork 的仓库 → **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. Name: `GEMINI_API_KEY`，Value: 你的 API Key

### 3. 启用 GitHub Pages

1. 进入仓库 → **Settings** → **Pages**
2. Source 选择 **GitHub Actions**

### 4. 启用 GitHub Actions

1. 进入仓库 → **Actions** 标签页
2. 点击 **I understand my workflows, go ahead and enable them**
3. 选择 **AI Daily News Generator** 工作流
4. 点击 **Run workflow** 手动触发第一次运行

### 5. 完成！

- 工作流会每天北京时间 **8:00** 自动运行
- 生成的日报会自动发布到 GitHub Pages
- 访问 `https://jiangnan030-del.github.io/ai-daily-news/` 查看

## 🏗️ 项目结构

```
ai-daily-news/
├── .github/workflows/
│   └── daily-news.yml          # GitHub Actions 定时工作流
├── scripts/
│   ├── fetch_github_trending.py # 抓取 GitHub Trending
│   ├── fetch_hacker_news.py     # 抓取 Hacker News
│   ├── fetch_arxiv.py           # 抓取 arXiv 论文
│   ├── ai_summarize.py          # Gemini AI 摘要生成
│   ├── generate_report.py       # 日报 Markdown 生成
│   └── build_site.py            # 静态站点构建
├── main.py                      # 主入口脚本
├── docs/daily/                  # 日报 Markdown 归档
├── data/                        # 原始 JSON 数据归档
├── site/                        # 构建产物 (GitHub Pages)
├── requirements.txt             # Python 依赖
└── README.md
```

## 🔧 本地运行

```bash
# 克隆仓库
git clone https://github.com/jiangnan030-del/ai-daily-news.git
cd ai-daily-news

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export GEMINI_API_KEY="your_api_key_here"

# 运行
python main.py
```

> 💡 即使不设置 `GEMINI_API_KEY`，脚本也能运行，只是会跳过 AI 摘要生成，使用原始英文内容。

## ⚙️ 自定义配置

### 修改运行时间

编辑 `.github/workflows/daily-news.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC 0:00 = 北京时间 8:00
```

### 添加更多数据源

在 `scripts/` 目录下创建新的抓取脚本，然后在 `main.py` 中集成即可。

### 自定义 AI 关键词

编辑各抓取脚本中的 `AI_KEYWORDS` 列表，调整 AI 相关关键词匹配规则。

## 📄 License

MIT License - 自由使用和修改。
