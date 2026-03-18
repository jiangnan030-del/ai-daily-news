"""
从 GitHub Trending 抓取 AI/ML 相关热门项目
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending"
AI_LANGUAGES = ["python", "jupyter-notebook"]
AI_KEYWORDS = [
    "ai", "artificial-intelligence", "machine-learning", "deep-learning",
    "llm", "large-language-model", "gpt", "transformer", "neural-network",
    "nlp", "natural-language-processing", "computer-vision", "diffusion",
    "agent", "rag", "fine-tuning", "mcp", "embedding", "vector",
    "generative", "chatbot", "multimodal", "reasoning", "inference",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _is_ai_related(name: str, description: str) -> bool:
    """判断项目是否与 AI 相关"""
    text = f"{name} {description}".lower()
    return any(kw in text for kw in AI_KEYWORDS)


def fetch_trending(since: str = "daily", language: str = "") -> list[dict]:
    """
    抓取 GitHub Trending 页面

    Args:
        since: 时间范围 daily/weekly/monthly
        language: 编程语言过滤

    Returns:
        项目列表 [{name, url, description, stars, forks, language, stars_today}]
    """
    params = {"since": since}
    if language:
        params["spoken_language_code"] = ""

    url = f"{TRENDING_URL}/{language}" if language else TRENDING_URL
    projects = []

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        articles = soup.select("article.Box-row")
        for article in articles:
            # 项目名称和链接
            h2 = article.select_one("h2 a")
            if not h2:
                continue
            repo_path = h2.get("href", "").strip("/")
            name = repo_path
            repo_url = f"https://github.com/{repo_path}"

            # 描述
            desc_tag = article.select_one("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            # 编程语言
            lang_tag = article.select_one("[itemprop='programmingLanguage']")
            lang = lang_tag.get_text(strip=True) if lang_tag else ""

            # 星标数
            star_links = article.select("a.Link--muted")
            stars = 0
            forks = 0
            if len(star_links) >= 1:
                stars_text = star_links[0].get_text(strip=True).replace(",", "")
                stars = int(stars_text) if stars_text.isdigit() else 0
            if len(star_links) >= 2:
                forks_text = star_links[1].get_text(strip=True).replace(",", "")
                forks = int(forks_text) if forks_text.isdigit() else 0

            # 今日新增星标
            stars_today = 0
            today_tag = article.select_one("span.d-inline-block.float-sm-right")
            if today_tag:
                match = re.search(r"([\d,]+)", today_tag.get_text())
                if match:
                    stars_today = int(match.group(1).replace(",", ""))

            projects.append({
                "name": name,
                "url": repo_url,
                "description": description,
                "stars": stars,
                "forks": forks,
                "language": lang,
                "stars_today": stars_today,
                "source": "github_trending",
            })

        logger.info(f"从 GitHub Trending 抓取到 {len(projects)} 个项目")
    except Exception as e:
        logger.error(f"抓取 GitHub Trending 失败: {e}")

    return projects


def fetch_ai_trending() -> list[dict]:
    """抓取 AI 相关的 Trending 项目"""
    all_projects = []

    # 抓取总榜
    projects = fetch_trending(since="daily")
    ai_projects = [p for p in projects if _is_ai_related(p["name"], p["description"])]
    all_projects.extend(ai_projects)

    # 抓取 Python 榜（AI 项目集中的语言）
    py_projects = fetch_trending(since="daily", language="python")
    for p in py_projects:
        if p["url"] not in {x["url"] for x in all_projects}:
            if _is_ai_related(p["name"], p["description"]):
                all_projects.append(p)

    # 按今日星标排序
    all_projects.sort(key=lambda x: x["stars_today"], reverse=True)

    logger.info(f"筛选出 {len(all_projects)} 个 AI 相关 Trending 项目")
    return all_projects[:15]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_ai_trending()
    for r in results:
        print(f"⭐ {r['stars_today']} | {r['name']} - {r['description'][:60]}")
