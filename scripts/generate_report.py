"""
生成每日 AI 日报的 Markdown 和 HTML 文件
"""
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 北京时间
BJT = timezone(timedelta(hours=8))

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def generate_markdown(
    overview: str,
    github_projects: list[dict],
    hn_posts: list[dict],
    arxiv_papers: list[dict],
) -> str:
    """
    生成 Markdown 格式的日报

    Returns:
        Markdown 文本
    """
    now = datetime.now(BJT)
    date_str = now.strftime("%Y-%m-%d")
    weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]

    lines = []
    lines.append(f"# 🤖 AI 前沿日报 | {date_str} {weekday_cn}")
    lines.append("")
    lines.append(f"> 自动生成于 {now.strftime('%Y-%m-%d %H:%M')} (北京时间)")
    lines.append("")

    # 每日总览
    lines.append("## 📌 今日概览")
    lines.append("")
    lines.append(overview)
    lines.append("")

    # GitHub Trending
    if github_projects:
        lines.append("---")
        lines.append("")
        lines.append("## 🔥 GitHub 热门 AI 项目")
        lines.append("")
        for i, p in enumerate(github_projects, 1):
            score = p.get("score", 5)
            score_stars = "⭐" * min(score // 2, 5)
            category = p.get("category", "")
            cat_badge = f"`{category}`" if category else ""

            lines.append(f"### {i}. [{p['name']}]({p['url']}) {cat_badge}")
            lines.append("")

            if p.get("one_liner"):
                lines.append(f"> {p['one_liner']}")
                lines.append("")

            lines.append(
                f"⭐ **{p['stars']:,}** Stars | "
                f"📈 今日 +{p['stars_today']} | "
                f"🔤 {p.get('language', 'N/A')} | "
                f"推荐: {score_stars} ({score}/10)"
            )
            lines.append("")

            if p.get("summary_cn"):
                lines.append(p["summary_cn"])
                lines.append("")

    # Hacker News
    if hn_posts:
        lines.append("---")
        lines.append("")
        lines.append("## 📰 Hacker News AI 热议")
        lines.append("")
        for i, p in enumerate(hn_posts, 1):
            title_display = p.get("title_cn", p["title"])
            category = p.get("category", "")
            cat_badge = f"`{category}`" if category else ""

            lines.append(f"### {i}. [{title_display}]({p['url']}) {cat_badge}")
            lines.append("")

            if title_display != p["title"]:
                lines.append(f"*原标题: {p['title']}*")
                lines.append("")

            lines.append(
                f"🔺 **{p['score']}** Points | "
                f"💬 [{p['comments']} 评论]({p['hn_url']}) | "
                f"👤 {p['author']}"
            )
            lines.append("")

            if p.get("summary_cn"):
                lines.append(p["summary_cn"])
                lines.append("")

    # arXiv Papers
    if arxiv_papers:
        lines.append("---")
        lines.append("")
        lines.append("## 📄 arXiv 最新 AI 论文")
        lines.append("")
        for i, p in enumerate(arxiv_papers, 1):
            title_display = p.get("title_cn", p["title"])
            cats = ", ".join(p.get("categories", [])[:3])

            lines.append(f"### {i}. [{title_display}]({p['url']})")
            lines.append("")
            lines.append(f"*{p['title']}*")
            lines.append("")

            authors = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors += " et al."

            lines.append(f"📝 {authors} | 📂 `{cats}`")
            lines.append("")

            if p.get("summary_cn"):
                lines.append(p["summary_cn"])
                lines.append("")

            if p.get("significance"):
                lines.append(f"💡 **为什么重要**: {p['significance']}")
                lines.append("")

            lines.append(f"📥 [PDF]({p.get('pdf_url', p['url'])})")
            lines.append("")

    # 页脚
    lines.append("---")
    lines.append("")
    lines.append(
        "*本日报由 [AI Daily News](https://github.com) 自动生成，"
        "数据来源: GitHub Trending, Hacker News, arXiv*"
    )
    lines.append("")

    return "\n".join(lines)


def save_markdown(content: str, date_str: str | None = None) -> Path:
    """保存 Markdown 文件"""
    if date_str is None:
        date_str = datetime.now(BJT).strftime("%Y-%m-%d")

    # 按年月分目录
    year_month = date_str[:7]  # YYYY-MM
    output_dir = PROJECT_ROOT / "docs" / "daily" / year_month
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / f"{date_str}.md"
    filepath.write_text(content, encoding="utf-8")

    logger.info(f"日报 Markdown 已保存: {filepath}")
    return filepath


def save_json_data(
    github_projects: list[dict],
    hn_posts: list[dict],
    arxiv_papers: list[dict],
    date_str: str | None = None,
) -> Path:
    """保存原始 JSON 数据"""
    if date_str is None:
        date_str = datetime.now(BJT).strftime("%Y-%m-%d")

    data_dir = PROJECT_ROOT / "data" / date_str[:7]
    data_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "date": date_str,
        "generated_at": datetime.now(BJT).isoformat(),
        "github_trending": github_projects,
        "hacker_news": hn_posts,
        "arxiv_papers": arxiv_papers,
    }

    filepath = data_dir / f"{date_str}.json"
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"原始数据已保存: {filepath}")
    return filepath


def get_recent_reports(days: int = 30) -> list[dict]:
    """获取最近的日报列表（用于生成首页索引）"""
    daily_dir = PROJECT_ROOT / "docs" / "daily"
    reports = []

    if not daily_dir.exists():
        return reports

    for md_file in sorted(daily_dir.rglob("*.md"), reverse=True):
        if md_file.name.startswith("20"):
            date_str = md_file.stem
            rel_path = md_file.relative_to(PROJECT_ROOT / "docs")
            reports.append({
                "date": date_str,
                "path": str(rel_path).replace("\\", "/"),
                "filename": md_file.name,
            })

        if len(reports) >= days:
            break

    return reports
