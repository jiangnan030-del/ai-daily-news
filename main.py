"""
AI 前沿日报 - 主入口脚本
串联所有流程: 抓取 → AI摘要 → 生成报告 → 构建站点
"""
import os
import sys
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch_github_trending import fetch_ai_trending
from scripts.fetch_hacker_news import fetch_ai_news
from scripts.fetch_arxiv import fetch_ai_papers
from scripts.ai_summarize import (
    summarize_github_projects,
    summarize_hn_posts,
    summarize_arxiv_papers,
    generate_daily_overview,
)
from scripts.generate_report import (
    generate_markdown,
    save_markdown,
    save_json_data,
)
from scripts.build_site import build_site

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ai-daily-news")

BJT = timezone(timedelta(hours=8))


def main():
    """主流程"""
    start_time = time.time()
    date_str = datetime.now(BJT).strftime("%Y-%m-%d")

    logger.info(f"========== AI 前沿日报生成开始 | {date_str} ==========")

    # ========== Step 1: 数据抓取 ==========
    logger.info("📡 Step 1/5: 抓取多源数据...")

    logger.info("  → 抓取 GitHub Trending...")
    github_projects = fetch_ai_trending()
    logger.info(f"  ✅ GitHub Trending: {len(github_projects)} 个项目")

    logger.info("  → 抓取 Hacker News...")
    hn_posts = fetch_ai_news()
    logger.info(f"  ✅ Hacker News: {len(hn_posts)} 条帖子")

    logger.info("  → 抓取 arXiv 论文...")
    arxiv_papers = fetch_ai_papers()
    logger.info(f"  ✅ arXiv: {len(arxiv_papers)} 篇论文")

    total_items = len(github_projects) + len(hn_posts) + len(arxiv_papers)
    if total_items == 0:
        logger.warning("⚠️ 所有数据源均未抓取到内容，跳过生成")
        return

    # ========== Step 2: AI 摘要生成 ==========
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        logger.info("🧠 Step 2/5: 使用 Gemini 生成 AI 摘要...")

        if github_projects:
            logger.info("  → 生成 GitHub 项目摘要...")
            github_projects = summarize_github_projects(github_projects)
            time.sleep(1)  # 避免 API 速率限制

        if hn_posts:
            logger.info("  → 生成 HN 帖子摘要...")
            hn_posts = summarize_hn_posts(hn_posts)
            time.sleep(1)

        if arxiv_papers:
            logger.info("  → 生成 arXiv 论文摘要...")
            arxiv_papers = summarize_arxiv_papers(arxiv_papers)
            time.sleep(1)

        logger.info("  ✅ AI 摘要生成完成")
    else:
        logger.warning("⚠️ 未设置 GEMINI_API_KEY，跳过 AI 摘要生成（将使用原始内容）")
        # 设置默认值
        for p in github_projects:
            p.setdefault("summary_cn", p.get("description", ""))
            p.setdefault("score", 5)
            p.setdefault("category", "其他")
            p.setdefault("one_liner", "")
        for p in hn_posts:
            p.setdefault("title_cn", p.get("title", ""))
            p.setdefault("summary_cn", "")
            p.setdefault("score", 5)
            p.setdefault("category", "其他")
        for p in arxiv_papers:
            p.setdefault("title_cn", p.get("title", ""))
            p.setdefault("summary_cn", p.get("abstract", "")[:200])
            p.setdefault("score", 5)
            p.setdefault("significance", "")

    # ========== Step 3: 生成每日概览 ==========
    logger.info("📌 Step 3/5: 生成每日趋势概览...")
    if gemini_key:
        overview = generate_daily_overview(github_projects, hn_posts, arxiv_papers)
    else:
        overview = (
            f"今日共收录 {len(github_projects)} 个 GitHub 热门 AI 项目、"
            f"{len(hn_posts)} 条 Hacker News AI 热议、"
            f"{len(arxiv_papers)} 篇 arXiv 最新论文。"
        )
    logger.info("  ✅ 概览生成完成")

    # ========== Step 4: 生成日报文件 ==========
    logger.info("📝 Step 4/5: 生成日报 Markdown...")
    md_content = generate_markdown(overview, github_projects, hn_posts, arxiv_papers)
    md_path = save_markdown(md_content, date_str)

    # 保存原始 JSON 数据
    json_path = save_json_data(github_projects, hn_posts, arxiv_papers, date_str)
    logger.info(f"  ✅ Markdown: {md_path}")
    logger.info(f"  ✅ JSON 数据: {json_path}")

    # ========== Step 5: 构建静态站点 ==========
    logger.info("🏗️ Step 5/5: 构建 GitHub Pages 站点...")
    build_site()
    logger.info("  ✅ 站点构建完成")

    # ========== 完成 ==========
    elapsed = time.time() - start_time
    logger.info(f"========== 日报生成完成! 耗时: {elapsed:.1f}s ==========")
    logger.info(f"  📊 GitHub: {len(github_projects)} | HN: {len(hn_posts)} | arXiv: {len(arxiv_papers)}")
    logger.info(f"  📄 日报路径: {md_path}")


if __name__ == "__main__":
    main()
