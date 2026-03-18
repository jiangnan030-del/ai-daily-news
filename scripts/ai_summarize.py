"""
使用 AI API (OpenAI 兼容格式) 对抓取的内容进行智能摘要、评分和翻译
支持双 API 自动降级: Claude (主) → Gemini (备)
"""
import os
import re
import json
import logging
import time
from openai import OpenAI

logger = logging.getLogger(__name__)

# ========== 双 API 配置 ==========
# 主 API: Claude
PRIMARY_API_KEY = os.environ.get("AI_API_KEY", "")
PRIMARY_API_BASE = os.environ.get("AI_API_BASE_URL", "https://aws.ai678.top/v1")
PRIMARY_MODEL = os.environ.get("AI_MODEL", "claude-opus-4-5-20251101")

# 备用 API: Gemini
FALLBACK_API_KEY = os.environ.get("FALLBACK_API_KEY", "")
FALLBACK_API_BASE = os.environ.get("FALLBACK_API_BASE_URL", "https://new.lemonapi.site/v1")
FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "[L]gemini-2.5-pro")

API_TIMEOUT = 120


def _create_client(api_key: str, base_url: str) -> OpenAI:
    """创建 OpenAI 兼容客户端"""
    return OpenAI(api_key=api_key, base_url=base_url, timeout=API_TIMEOUT)


def _call_api(client: OpenAI, model: str, prompt: str) -> str:
    """调用单个 API"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=8192,
    )
    return response.choices[0].message.content.strip()


def _robust_json_parse(text: str) -> list[dict]:
    """健壮的 JSON 解析，处理 LLM 常见的格式问题"""
    # 1. 去除 markdown 代码块
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1)
    text = text.strip()

    # 2. 提取 JSON 数组部分
    arr_match = re.search(r"\[.*\]", text, re.DOTALL)
    if arr_match:
        text = arr_match.group(0)

    # 3. 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 4. 修复尾逗号
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 5. 如果 JSON 被截断，尝试补全
    if text.count("[") > text.count("]"):
        last_brace = text.rfind("}")
        if last_brace > 0:
            truncated = text[:last_brace + 1] + "]"
            truncated = re.sub(r",\s*\]", "]", truncated)
            try:
                return json.loads(truncated)
            except json.JSONDecodeError:
                pass

    # 6. 逐个提取 JSON 对象
    objects = []
    for m in re.finditer(r"\{[^{}]*\}", text):
        try:
            obj = json.loads(m.group(0))
            objects.append(obj)
        except json.JSONDecodeError:
            continue
    if objects:
        return objects

    raise json.JSONDecodeError("无法解析 AI 返回的 JSON", text, 0)


def _chat(prompt: str) -> str:
    """调用 AI API 生成内容（自动降级）

    优先使用 Claude (主)，失败时自动切换到 Gemini (备)
    """
    if PRIMARY_API_KEY:
        try:
            client = _create_client(PRIMARY_API_KEY, PRIMARY_API_BASE)
            result = _call_api(client, PRIMARY_MODEL, prompt)
            logger.debug(f"主 API ({PRIMARY_MODEL}) 调用成功")
            return result
        except Exception as e:
            logger.warning(f"主 API ({PRIMARY_MODEL}) 调用失败: {e}")

    if FALLBACK_API_KEY:
        try:
            client = _create_client(FALLBACK_API_KEY, FALLBACK_API_BASE)
            result = _call_api(client, FALLBACK_MODEL, prompt)
            logger.info(f"备用 API ({FALLBACK_MODEL}) 调用成功")
            return result
        except Exception as e:
            logger.warning(f"备用 API ({FALLBACK_MODEL}) 调用失败: {e}")

    raise ValueError("所有 AI API 均不可用，请检查 API Key 配置")


def summarize_github_projects(projects: list[dict]) -> list[dict]:
    """
    为 GitHub Trending 项目生成中文摘要和评分

    Returns:
        增强后的项目列表，每个项目新增 summary_cn, score, category 字段
    """
    if not projects:
        return []

    projects_text = ""
    for i, p in enumerate(projects):
        projects_text += (
            f"\n项目 {i+1}:\n"
            f"  名称: {p['name']}\n"
            f"  描述: {p['description']}\n"
            f"  语言: {p['language']}\n"
            f"  Stars: {p['stars']}, 今日新增: {p['stars_today']}\n"
        )

    prompt = f"""你是一位专业的 AI 技术编辑。请为以下 GitHub Trending 项目生成中文摘要和评分。

{projects_text}

请以 JSON 数组格式返回，每个元素包含：
- "index": 项目序号(从1开始)
- "summary_cn": 中文摘要(2-3句话，说明项目用途、技术亮点和适用场景)
- "score": 推荐评分(1-10，基于创新性、实用性、热度综合评估)
- "category": 分类(从以下选择: LLM/Agent/CV/NLP/工具/框架/数据/论文实现/教程/其他)
- "one_liner": 一句话中文推荐语

只返回 JSON 数组，不要其他文字。"""

    try:
        text = _chat(prompt)
        summaries = _robust_json_parse(text)

        for s in summaries:
            idx = s.get("index", 0) - 1
            if 0 <= idx < len(projects):
                projects[idx]["summary_cn"] = s.get("summary_cn", "")
                projects[idx]["score"] = s.get("score", 5)
                projects[idx]["category"] = s.get("category", "其他")
                projects[idx]["one_liner"] = s.get("one_liner", "")

        logger.info(f"为 {len(summaries)} 个 GitHub 项目生成了摘要")
    except Exception as e:
        logger.error(f"生成 GitHub 项目摘要失败: {e}")
        for p in projects:
            p.setdefault("summary_cn", p.get("description", ""))
            p.setdefault("score", 5)
            p.setdefault("category", "其他")
            p.setdefault("one_liner", "")

    return projects


def summarize_hn_posts(posts: list[dict]) -> list[dict]:
    """
    为 Hacker News 帖子生成中文摘要和评分
    """
    if not posts:
        return []

    posts_text = ""
    for i, p in enumerate(posts):
        posts_text += (
            f"\n帖子 {i+1}:\n"
            f"  标题: {p['title']}\n"
            f"  链接: {p['url']}\n"
            f"  得分: {p['score']}, 评论数: {p['comments']}\n"
        )

    prompt = f"""你是一位专业的 AI 技术编辑。请为以下 Hacker News 热门帖子生成中文翻译标题和摘要。

{posts_text}

请以 JSON 数组格式返回，每个元素包含：
- "index": 帖子序号(从1开始)
- "title_cn": 中文翻译标题
- "summary_cn": 中文摘要(1-2句话，根据标题推测内容要点)
- "score": 推荐评分(1-10)
- "category": 分类(从以下选择: 行业动态/产品发布/技术突破/开源项目/观点讨论/教程/其他)

只返回 JSON 数组，不要其他文字。"""

    try:
        text = _chat(prompt)
        summaries = _robust_json_parse(text)

        for s in summaries:
            idx = s.get("index", 0) - 1
            if 0 <= idx < len(posts):
                posts[idx]["title_cn"] = s.get("title_cn", "")
                posts[idx]["summary_cn"] = s.get("summary_cn", "")
                posts[idx]["score"] = s.get("score", 5)
                posts[idx]["category"] = s.get("category", "其他")

        logger.info(f"为 {len(summaries)} 条 HN 帖子生成了摘要")
    except Exception as e:
        logger.error(f"生成 HN 帖子摘要失败: {e}")
        for p in posts:
            p.setdefault("title_cn", p.get("title", ""))
            p.setdefault("summary_cn", "")
            p.setdefault("score", 5)
            p.setdefault("category", "其他")

    return posts


def summarize_arxiv_papers(papers: list[dict]) -> list[dict]:
    """
    为 arXiv 论文生成中文摘要和评分
    """
    if not papers:
        return []

    papers_text = ""
    for i, p in enumerate(papers):
        abstract_short = p["abstract"][:300]
        papers_text += (
            f"\n论文 {i+1}:\n"
            f"  标题: {p['title']}\n"
            f"  作者: {', '.join(p['authors'][:3])}\n"
            f"  分类: {', '.join(p['categories'][:3])}\n"
            f"  摘要: {abstract_short}\n"
        )

    prompt = f"""你是一位资深的 AI 研究员和科技编辑。请为以下 arXiv 最新论文生成中文翻译和摘要。

{papers_text}

请以 JSON 数组格式返回，每个元素包含：
- "index": 论文序号(从1开始)
- "title_cn": 中文翻译标题
- "summary_cn": 通俗易懂的中文摘要(2-3句话，说明研究问题、方法和关键发现)
- "score": 推荐评分(1-10，基于创新性、影响力、实用性评估)
- "significance": 一句话说明这篇论文为什么重要

只返回 JSON 数组，不要其他文字。"""

    try:
        text = _chat(prompt)
        summaries = _robust_json_parse(text)

        for s in summaries:
            idx = s.get("index", 0) - 1
            if 0 <= idx < len(papers):
                papers[idx]["title_cn"] = s.get("title_cn", "")
                papers[idx]["summary_cn"] = s.get("summary_cn", "")
                papers[idx]["score"] = s.get("score", 5)
                papers[idx]["significance"] = s.get("significance", "")

        logger.info(f"为 {len(summaries)} 篇 arXiv 论文生成了摘要")
    except Exception as e:
        logger.error(f"生成 arXiv 论文摘要失败: {e}")
        for p in papers:
            p.setdefault("title_cn", p.get("title", ""))
            p.setdefault("summary_cn", p.get("abstract", "")[:200])
            p.setdefault("score", 5)
            p.setdefault("significance", "")

    return papers


def generate_daily_overview(
    github_projects: list[dict],
    hn_posts: list[dict],
    arxiv_papers: list[dict],
) -> str:
    """
    生成每日 AI 趋势总览

    Returns:
        中文趋势总结文本
    """
    context_parts = []

    if github_projects:
        gh_names = [p["name"] for p in github_projects[:10]]
        context_parts.append(f"GitHub Trending AI 项目: {', '.join(gh_names)}")

    if hn_posts:
        hn_titles = [p["title"] for p in hn_posts[:10]]
        context_parts.append(f"Hacker News AI 热帖: {'; '.join(hn_titles)}")

    if arxiv_papers:
        arxiv_titles = [p["title"] for p in arxiv_papers[:10]]
        context_parts.append(f"arXiv 最新论文: {'; '.join(arxiv_titles)}")

    context = "\n\n".join(context_parts)

    prompt = f"""基于今日 AI 领域的以下动态，请生成一段精炼的每日趋势总览（中文，200-300字）：

{context}

要求：
1. 总结 2-3 个今日最值得关注的 AI 趋势或主题
2. 语言简洁有力，像一位资深科技编辑的开场白
3. 让读者快速了解今天 AI 领域发生了什么重要的事
4. 不要使用列表格式，用连贯的段落叙述"""

    try:
        overview = _chat(prompt)
        logger.info("生成每日趋势总览成功")
        return overview
    except Exception as e:
        logger.error(f"生成每日趋势总览失败: {e}")
        return "今日 AI 领域持续活跃，多个前沿方向取得新进展。"
