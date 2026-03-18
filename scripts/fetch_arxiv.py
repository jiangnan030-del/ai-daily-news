"""
从 arXiv 抓取最新 AI 论文
使用 arXiv API: https://arxiv.org/help/api
"""
import requests
import feedparser
from datetime import datetime, timezone, timedelta
import logging
import re

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"

# AI 相关的 arXiv 分类
AI_CATEGORIES = [
    "cs.AI",   # Artificial Intelligence
    "cs.CL",   # Computation and Language (NLP)
    "cs.CV",   # Computer Vision
    "cs.LG",   # Machine Learning
    "cs.MA",   # Multiagent Systems
    "cs.NE",   # Neural and Evolutionary Computing
    "cs.RO",   # Robotics (AI-related)
    "stat.ML", # Machine Learning (Statistics)
]


def fetch_latest_papers(
    categories: list[str] | None = None,
    max_results: int = 50,
    days_back: int = 2,
) -> list[dict]:
    """
    从 arXiv 抓取最新 AI 论文

    Args:
        categories: arXiv 分类列表
        max_results: API 返回的最大数量
        days_back: 回溯天数

    Returns:
        论文列表 [{title, authors, abstract, url, pdf_url, categories, published, source}]
    """
    if categories is None:
        categories = AI_CATEGORIES

    # 构建搜索查询
    cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
    query = f"({cat_query})"

    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    papers = []
    try:
        resp = requests.get(ARXIV_API, params=params, timeout=30)
        resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        for entry in feed.entries:
            # 解析发布时间
            published = datetime.fromisoformat(
                entry.published.replace("Z", "+00:00")
            )
            if published < cutoff:
                continue

            # 提取作者
            authors = [a.get("name", "") for a in entry.get("authors", [])]

            # 提取分类
            cats = [t["term"] for t in entry.get("tags", []) if t.get("term")]

            # 提取 PDF 链接
            pdf_url = ""
            for link in entry.get("links", []):
                if link.get("type") == "application/pdf":
                    pdf_url = link["href"]
                    break
            if not pdf_url:
                pdf_url = entry.id.replace("/abs/", "/pdf/")

            # 清理摘要中的换行
            abstract = re.sub(r"\s+", " ", entry.summary).strip()

            papers.append({
                "title": entry.title.replace("\n", " ").strip(),
                "authors": authors[:5],  # 最多保留5个作者
                "abstract": abstract,
                "url": entry.id,
                "pdf_url": pdf_url,
                "categories": cats,
                "published": published.isoformat(),
                "source": "arxiv",
            })

        logger.info(f"从 arXiv 抓取到 {len(papers)} 篇最新 AI 论文")
    except Exception as e:
        logger.error(f"抓取 arXiv 失败: {e}")

    return papers[:20]


def fetch_ai_papers() -> list[dict]:
    """抓取 AI 相关的最新论文（精选）"""
    papers = fetch_latest_papers()

    # 按主分类排序，优先展示 cs.AI 和 cs.CL
    priority = {"cs.AI": 0, "cs.CL": 1, "cs.LG": 2, "cs.CV": 3}

    def sort_key(paper):
        primary_cat = paper["categories"][0] if paper["categories"] else "zzz"
        return priority.get(primary_cat, 5)

    papers.sort(key=sort_key)
    return papers[:15]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_ai_papers()
    for r in results:
        cats = ", ".join(r["categories"][:3])
        print(f"📄 [{cats}] {r['title'][:70]}")
        print(f"   {', '.join(r['authors'][:3])}")
        print()
