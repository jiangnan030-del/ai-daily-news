"""
构建 GitHub Pages 静态站点
将 Markdown 日报转换为精美的 HTML 页面
"""
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

BJT = timezone(timedelta(hours=8))
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
SITE_DIR = PROJECT_ROOT / "site"


def markdown_to_html(md_text: str) -> str:
    """简易 Markdown -> HTML 转换（不依赖额外库）"""
    lines = md_text.split("\n")
    html_parts = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # 空行
        if not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append("")
            continue

        # 标题
        if stripped.startswith("# "):
            html_parts.append(f'<h1>{_inline(stripped[2:])}</h1>')
            continue
        if stripped.startswith("## "):
            html_parts.append(f'<h2>{_inline(stripped[3:])}</h2>')
            continue
        if stripped.startswith("### "):
            html_parts.append(f'<h3>{_inline(stripped[4:])}</h3>')
            continue

        # 分隔线
        if stripped == "---":
            html_parts.append("<hr>")
            continue

        # 引用
        if stripped.startswith("> "):
            html_parts.append(f'<blockquote>{_inline(stripped[2:])}</blockquote>')
            continue

        # 斜体行
        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            html_parts.append(f'<p class="italic-note">{_inline(stripped)}</p>')
            continue

        # 列表项
        if stripped.startswith("- "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_inline(stripped[2:])}</li>")
            continue

        # 普通段落
        if in_list:
            html_parts.append("</ul>")
            in_list = False
        html_parts.append(f"<p>{_inline(stripped)}</p>")

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def _inline(text: str) -> str:
    """处理内联 Markdown 格式"""
    # 链接 [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    # 粗体
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 斜体
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # 行内代码
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # emoji 保留
    return text


def get_all_reports() -> list[dict]:
    """获取所有日报文件"""
    daily_dir = DOCS_DIR / "daily"
    reports = []

    if not daily_dir.exists():
        return reports

    for md_file in sorted(daily_dir.rglob("*.md"), reverse=True):
        if md_file.name.startswith("20"):
            date_str = md_file.stem
            reports.append({
                "date": date_str,
                "path": str(md_file),
                "rel_path": f"daily/{md_file.parent.name}/{md_file.name}",
            })

    return reports


def build_daily_page(md_path: str, date_str: str) -> str:
    """构建单个日报的 HTML 页面"""
    md_content = Path(md_path).read_text(encoding="utf-8")
    body_html = markdown_to_html(md_content)

    weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        wd = weekday_cn[dt.weekday()]
    except ValueError:
        wd = ""

    return HTML_TEMPLATE.replace("{{TITLE}}", f"AI 前沿日报 | {date_str} {wd}").replace(
        "{{CONTENT}}", body_html
    ).replace("{{DATE}}", date_str).replace("{{NAV_ACTIVE}}", "daily")


def build_index_page(reports: list[dict]) -> str:
    """构建首页"""
    cards_html = ""
    for r in reports[:60]:
        date_str = r["date"]
        html_name = f"{date_str}.html"
        year_month = date_str[:7]
        link = f"daily/{year_month}/{html_name}"

        weekday_cn = ["一", "二", "三", "四", "五", "六", "日"]
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            wd = weekday_cn[dt.weekday()]
            month_day = f"{dt.month}月{dt.day}日"
        except ValueError:
            wd = ""
            month_day = date_str

        cards_html += f'''
        <a href="{link}" class="report-card">
            <div class="card-date">
                <span class="card-day">{date_str[-2:]}</span>
                <span class="card-month">{date_str[:7]}</span>
                <span class="card-weekday">周{wd}</span>
            </div>
            <div class="card-title">AI 前沿日报 · {month_day}</div>
            <div class="card-arrow">→</div>
        </a>'''

    return INDEX_TEMPLATE.replace("{{CARDS}}", cards_html).replace(
        "{{TOTAL}}", str(len(reports))
    )


def build_site():
    """构建整个静态站点"""
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    reports = get_all_reports()
    logger.info(f"找到 {len(reports)} 份日报")

    # 构建首页
    index_html = build_index_page(reports)
    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")
    logger.info("首页构建完成")

    # 构建每份日报页面
    for r in reports:
        date_str = r["date"]
        year_month = date_str[:7]
        output_dir = SITE_DIR / "daily" / year_month
        output_dir.mkdir(parents=True, exist_ok=True)

        page_html = build_daily_page(r["path"], date_str)
        (output_dir / f"{date_str}.html").write_text(page_html, encoding="utf-8")

    logger.info(f"站点构建完成: {SITE_DIR}")

    # 复制 CNAME 等文件（如果有）
    cname = DOCS_DIR / "CNAME"
    if cname.exists():
        (SITE_DIR / "CNAME").write_text(cname.read_text(), encoding="utf-8")

    # 创建 .nojekyll
    (SITE_DIR / ".nojekyll").touch()


# ========== HTML 模板 ==========

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>">
    <style>
        :root {
            --bg: #0d1117; --bg-secondary: #161b22; --bg-card: #1c2333;
            --text: #e6edf3; --text-secondary: #8b949e; --text-muted: #6e7681;
            --accent: #58a6ff; --accent-hover: #79c0ff;
            --border: #30363d; --border-light: #21262d;
            --green: #3fb950; --orange: #d29922; --red: #f85149; --purple: #bc8cff;
            --max-width: 860px;
        }
        [data-theme="light"] {
            --bg: #ffffff; --bg-secondary: #f6f8fa; --bg-card: #ffffff;
            --text: #1f2328; --text-secondary: #656d76; --text-muted: #8b949e;
            --accent: #0969da; --accent-hover: #0550ae;
            --border: #d0d7de; --border-light: #e8ecf0;
            --green: #1a7f37; --orange: #9a6700; --red: #cf222e; --purple: #8250df;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", Helvetica, Arial, sans-serif;
            background: var(--bg); color: var(--text);
            line-height: 1.7; -webkit-font-smoothing: antialiased;
        }
        .top-bar {
            position: sticky; top: 0; z-index: 100;
            background: var(--bg-secondary); border-bottom: 1px solid var(--border);
            backdrop-filter: blur(12px);
        }
        .top-bar-inner {
            max-width: var(--max-width); margin: 0 auto;
            padding: 12px 24px; display: flex; justify-content: space-between; align-items: center;
        }
        .logo { font-size: 18px; font-weight: 700; color: var(--text); text-decoration: none; }
        .logo:hover { color: var(--accent); }
        .nav-links { display: flex; gap: 16px; align-items: center; }
        .nav-links a {
            color: var(--text-secondary); text-decoration: none; font-size: 14px;
            padding: 4px 8px; border-radius: 6px; transition: all 0.2s;
        }
        .nav-links a:hover { color: var(--text); background: var(--border-light); }
        .theme-toggle {
            background: none; border: 1px solid var(--border); color: var(--text-secondary);
            cursor: pointer; padding: 6px 10px; border-radius: 6px; font-size: 16px;
            transition: all 0.2s;
        }
        .theme-toggle:hover { border-color: var(--accent); color: var(--accent); }
        .container { max-width: var(--max-width); margin: 0 auto; padding: 32px 24px 80px; }
        h1 { font-size: 28px; margin-bottom: 8px; background: linear-gradient(135deg, var(--accent), var(--purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        h2 { font-size: 22px; margin: 32px 0 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); color: var(--text); }
        h3 { font-size: 17px; margin: 20px 0 8px; color: var(--text); }
        h3 a { color: var(--accent); text-decoration: none; }
        h3 a:hover { text-decoration: underline; }
        h3 code {
            font-size: 12px; padding: 2px 8px; border-radius: 12px;
            background: var(--accent); color: #fff; font-weight: 500;
            margin-left: 6px; vertical-align: middle;
        }
        p { margin-bottom: 12px; color: var(--text-secondary); font-size: 15px; }
        blockquote {
            border-left: 3px solid var(--accent); padding: 8px 16px; margin: 12px 0;
            background: var(--bg-secondary); border-radius: 0 8px 8px 0;
            color: var(--text); font-size: 15px;
        }
        hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
        a { color: var(--accent); }
        a:hover { color: var(--accent-hover); }
        strong { color: var(--text); }
        code { background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
        .italic-note { font-style: italic; color: var(--text-muted); font-size: 13px; }
        ul { margin: 8px 0 16px 20px; }
        li { margin: 4px 0; color: var(--text-secondary); font-size: 15px; }
        .footer {
            text-align: center; padding: 24px; color: var(--text-muted);
            font-size: 13px; border-top: 1px solid var(--border);
        }
        @media (max-width: 640px) {
            .container { padding: 20px 16px 60px; }
            h1 { font-size: 22px; }
            h2 { font-size: 18px; }
        }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="top-bar-inner">
            <a href="/" class="logo">🤖 AI Daily News</a>
            <div class="nav-links">
                <a href="/">首页</a>
                <button class="theme-toggle" onclick="toggleTheme()" title="切换主题">🌓</button>
            </div>
        </div>
    </div>
    <div class="container">
        {{CONTENT}}
    </div>
    <div class="footer">
        <p>AI Daily News · 每日自动生成 · Powered by GitHub Actions + AI</p>
    </div>
    <script>
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            const next = current === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        }
        (function() {
            const saved = localStorage.getItem('theme');
            if (saved) document.documentElement.setAttribute('data-theme', saved);
        })();
    </script>
</body>
</html>'''

INDEX_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 前沿日报 - 每日自动生成的 AI 资讯</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>">
    <style>
        :root {
            --bg: #0d1117; --bg-secondary: #161b22; --bg-card: #1c2333;
            --text: #e6edf3; --text-secondary: #8b949e; --text-muted: #6e7681;
            --accent: #58a6ff; --accent-hover: #79c0ff;
            --border: #30363d; --border-light: #21262d;
            --green: #3fb950; --purple: #bc8cff;
            --max-width: 860px;
        }
        [data-theme="light"] {
            --bg: #ffffff; --bg-secondary: #f6f8fa; --bg-card: #ffffff;
            --text: #1f2328; --text-secondary: #656d76; --text-muted: #8b949e;
            --accent: #0969da; --accent-hover: #0550ae;
            --border: #d0d7de; --border-light: #e8ecf0;
            --green: #1a7f37; --purple: #8250df;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", Helvetica, Arial, sans-serif;
            background: var(--bg); color: var(--text);
            line-height: 1.6; -webkit-font-smoothing: antialiased;
        }
        .top-bar {
            position: sticky; top: 0; z-index: 100;
            background: var(--bg-secondary); border-bottom: 1px solid var(--border);
            backdrop-filter: blur(12px);
        }
        .top-bar-inner {
            max-width: var(--max-width); margin: 0 auto;
            padding: 12px 24px; display: flex; justify-content: space-between; align-items: center;
        }
        .logo { font-size: 18px; font-weight: 700; color: var(--text); text-decoration: none; }
        .theme-toggle {
            background: none; border: 1px solid var(--border); color: var(--text-secondary);
            cursor: pointer; padding: 6px 10px; border-radius: 6px; font-size: 16px;
            transition: all 0.2s;
        }
        .theme-toggle:hover { border-color: var(--accent); color: var(--accent); }
        .hero {
            max-width: var(--max-width); margin: 0 auto; padding: 60px 24px 40px;
            text-align: center;
        }
        .hero h1 {
            font-size: 36px; margin-bottom: 12px;
            background: linear-gradient(135deg, var(--accent), var(--purple));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .hero p { color: var(--text-secondary); font-size: 16px; max-width: 500px; margin: 0 auto 20px; }
        .hero-stats { display: flex; justify-content: center; gap: 32px; margin-top: 20px; }
        .stat { text-align: center; }
        .stat-num { font-size: 28px; font-weight: 700; color: var(--accent); }
        .stat-label { font-size: 13px; color: var(--text-muted); }
        .container { max-width: var(--max-width); margin: 0 auto; padding: 0 24px 80px; }
        .section-title {
            font-size: 18px; color: var(--text-secondary); margin-bottom: 16px;
            padding-bottom: 8px; border-bottom: 1px solid var(--border);
        }
        .reports-grid { display: flex; flex-direction: column; gap: 8px; }
        .report-card {
            display: flex; align-items: center; gap: 16px;
            padding: 16px 20px; background: var(--bg-secondary);
            border: 1px solid var(--border-light); border-radius: 10px;
            text-decoration: none; color: var(--text);
            transition: all 0.2s ease;
        }
        .report-card:hover {
            border-color: var(--accent); background: var(--bg-card);
            transform: translateX(4px);
        }
        .card-date { text-align: center; min-width: 60px; }
        .card-day { display: block; font-size: 24px; font-weight: 700; color: var(--accent); line-height: 1.2; }
        .card-month { display: block; font-size: 12px; color: var(--text-muted); }
        .card-weekday { display: block; font-size: 12px; color: var(--text-muted); margin-top: 2px; }
        .card-title { flex: 1; font-size: 15px; font-weight: 500; }
        .card-arrow { color: var(--text-muted); font-size: 18px; transition: transform 0.2s; }
        .report-card:hover .card-arrow { transform: translateX(4px); color: var(--accent); }
        .footer {
            text-align: center; padding: 24px; color: var(--text-muted);
            font-size: 13px; border-top: 1px solid var(--border); margin-top: 40px;
        }
        .sources { display: flex; justify-content: center; gap: 16px; flex-wrap: wrap; margin-top: 12px; }
        .source-badge {
            padding: 4px 12px; border-radius: 16px; font-size: 13px;
            background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-secondary);
        }
        @media (max-width: 640px) {
            .hero { padding: 40px 16px 24px; }
            .hero h1 { font-size: 26px; }
            .container { padding: 0 16px 60px; }
            .hero-stats { gap: 20px; }
        }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="top-bar-inner">
            <a href="/" class="logo">🤖 AI Daily News</a>
            <button class="theme-toggle" onclick="toggleTheme()" title="切换主题">🌓</button>
        </div>
    </div>
    <div class="hero">
        <h1>🤖 AI 前沿日报</h1>
        <p>每天自动聚合 GitHub Trending、Hacker News、arXiv 的 AI 前沿资讯，由 AI 智能摘要</p>
        <div class="hero-stats">
            <div class="stat"><div class="stat-num">{{TOTAL}}</div><div class="stat-label">已发布日报</div></div>
            <div class="stat"><div class="stat-num">3</div><div class="stat-label">数据来源</div></div>
            <div class="stat"><div class="stat-num">24h</div><div class="stat-label">更新周期</div></div>
        </div>
        <div class="sources">
            <span class="source-badge">🔥 GitHub Trending</span>
            <span class="source-badge">📰 Hacker News</span>
            <span class="source-badge">📄 arXiv Papers</span>
        </div>
    </div>
    <div class="container">
        <h2 class="section-title">📅 历史日报</h2>
        <div class="reports-grid">
            {{CARDS}}
        </div>
    </div>
    <div class="footer">
        <p>AI Daily News · Powered by GitHub Actions + Claude/Gemini AI</p>
        <p style="margin-top:4px">数据来源: GitHub Trending · Hacker News · arXiv</p>
    </div>
    <script>
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            const next = current === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        }
        (function() {
            const saved = localStorage.getItem('theme');
            if (saved) document.documentElement.setAttribute('data-theme', saved);
        })();
    </script>
</body>
</html>'''


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_site()
