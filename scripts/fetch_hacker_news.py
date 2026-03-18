"""
从 Hacker News 抓取 AI 相关热门帖子
使用官方 Firebase API: https://github.com/HackerNewsAPI/API
"""
import re
import requests
from datetime import datetime, timezone, timedelta
import logging
import concurrent.futures

logger = logging.getLogger(__name__)

HN_API = "https://hacker-news.firebaseio.com/v0"
# 精确匹配的短语（直接子串匹配）
AI_PHRASES = [
    "artificial intelligence", "machine learning", "deep learning",
    "large language model", "language model", "computer vision",
    "neural network", "stable diffusion", "vector database",
    "model context protocol", "fine-tune", "fine-tuning",
    "ai agent", "ai model", "ai tool", "ai system",
    "agentic ai", "generative ai", "gen ai",
]

# 需要单词边界匹配的关键词（避免 "agent" 匹配 "Secret Agent" 等）
AI_WORD_PATTERNS = [
    r"\bllm\b", r"\bgpt[-\s]?\d", r"\bopenai\b", r"\banthropic\b",
    r"\bclaude\b", r"\bgemini\b", r"\bmistral\b", r"\btransformer[s]?\b",
    r"\bnlp\b", r"\bdiffusion\b", r"\bchatbot\b", r"\bmultimodal\b",
    r"\bllama\b", r"\bqwen\b", r"\bdeepseek\b", r"\bcopilot\b",
    r"\bmidjourney\b", r"\bembedding[s]?\b", r"\binference\b",
    r"\bagentic\b", r"\b(?:chat|code)\s*assist",
    r"\bai\b",  # 单独的 "AI" 需要边界匹配
]

# 排除关键词：包含这些词时大概率不是 AI 内容
EXCLUDE_PATTERNS = [
    r"secret agent", r"real estate", r"travel agent",
    r"insurance agent", r"fbi agent", r"cia agent",
]


def _is_ai_related(title: str, text: str = "") -> bool:
    """判断帖子是否与 AI 相关（精确匹配）"""
    combined = f"{title} {text}".lower()

    # 先检查排除词
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, combined):
            return False

    # 短语匹配
    if any(phrase in combined for phrase in AI_PHRASES):
        return True

    # 正则单词边界匹配
    return any(re.search(pat, combined) for pat in AI_WORD_PATTERNS)


def _fetch_item(item_id: int) -> dict | None:
    """获取单个 HN 条目"""
    try:
        resp = requests.get(f"{HN_API}/item/{item_id}.json", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def fetch_top_stories(limit: int = 200) -> list[int]:
    """获取热门故事 ID 列表"""
    try:
        resp = requests.get(f"{HN_API}/topstories.json", timeout=10)
        resp.raise_for_status()
        return resp.json()[:limit]
    except Exception as e:
        logger.error(f"获取 HN Top Stories 失败: {e}")
        return []


def fetch_ai_news(max_items: int = 200, max_results: int = 15) -> list[dict]:
    """
    抓取 HN 上 AI 相关的热门帖子

    Args:
        max_items: 最多检查的帖子数量
        max_results: 最多返回的结果数量

    Returns:
        帖子列表 [{title, url, score, comments, author, time, hn_url, source}]
    """
    story_ids = fetch_top_stories(limit=max_items)
    if not story_ids:
        return []

    # 并发获取帖子详情
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_item, sid): sid for sid in story_ids}
        for future in concurrent.futures.as_completed(futures):
            item = future.result()
            if item:
                items.append(item)

    # 过滤 AI 相关 + 24小时内的帖子
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=36)
    ai_posts = []

    for item in items:
        if item.get("type") != "story" or item.get("dead") or item.get("deleted"):
            continue

        title = item.get("title", "")
        text = item.get("text", "")
        item_time = datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc)

        if item_time < cutoff:
            continue

        if not _is_ai_related(title, text):
            continue

        post_url = item.get("url", "")
        hn_url = f"https://news.ycombinator.com/item?id={item['id']}"

        ai_posts.append({
            "title": title,
            "url": post_url or hn_url,
            "score": item.get("score", 0),
            "comments": item.get("descendants", 0),
            "author": item.get("by", ""),
            "time": item_time.isoformat(),
            "hn_url": hn_url,
            "source": "hacker_news",
        })

    # 按得分排序
    ai_posts.sort(key=lambda x: x["score"], reverse=True)

    logger.info(f"从 Hacker News 筛选出 {len(ai_posts)} 条 AI 相关帖子")
    return ai_posts[:max_results]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = fetch_ai_news()
    for r in results:
        print(f"🔥 {r['score']}pts | {r['title']}")
