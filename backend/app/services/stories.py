"""Grouping a company's news articles into stories, marking what's material, and tagging themes."""
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models import NewsArticle, NewsStory
from .llm_service import LLMService

logger = logging.getLogger(__name__)

MAX_ARTICLES = 40  # per run, newest first
RECENT_STORY_DAYS = 7  # stories new articles may be added to
THEME_DAYS = 120  # themes offered for reuse


def build_prompt(company_name: str, articles: list[NewsArticle], stories: list[NewsStory], themes: list[str]) -> str:
    lines = [
        f"Group these news articles about {company_name} into stories: articles from different outlets "
        "about the same event belong to one story.",
        "",
        "Existing stories (add articles to these when they're about the same event):",
    ]
    lines += [f"S{i}: {s.title}" for i, s in enumerate(stories, 1)] or ["(none)"]
    lines += ["", "New articles:"]
    for i, a in enumerate(articles, 1):
        lines.append(f"A{i}: {a.title}" + (f" ({a.source})" if a.source else ""))
    lines += [
        "",
        "Recurring themes for this company (reuse these labels when they fit):",
        ", ".join(themes) if themes else "(none yet)",
        "",
        "For each story, decide if it is material: could it move the stock or change an investor's view "
        "(results, guidance, contracts, leadership, financing, regulation, accidents)? Listicles, price recaps, "
        "'stocks to watch' and opinion pieces are not material.",
        "",
        "Respond with one JSON object and nothing else:",
        '{"stories": [{"existing": "S1" or null, "title": "short neutral headline for the event", '
        '"summary": "one sentence", "material": true or false, "themes": ["1-2 short labels; [] if not material"], '
        '"articles": ["A1", "A4"]}]}',
        "Every new article must appear in exactly one story.",
    ]
    return "\n".join(lines)


def parse_reply(text: str) -> list[dict]:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    stories = data.get("stories") if isinstance(data, dict) else None
    return [s for s in stories or [] if isinstance(s, dict) and isinstance(s.get("articles"), list)]


def apply_groups(db: Session, company_id: str, groups: list[dict], articles: list[NewsArticle], stories: list[NewsStory]) -> int:
    """Attach articles to existing or new stories. Returns how many articles were assigned."""
    by_ref = {f"A{i}": a for i, a in enumerate(articles, 1)}
    existing = {f"S{i}": s for i, s in enumerate(stories, 1)}
    now = datetime.now(timezone.utc)
    assigned = 0
    for g in groups:
        members = [by_ref[r] for r in g["articles"] if r in by_ref and by_ref[r].story_id is None]
        if not members:
            continue
        story = existing.get(g.get("existing") or "")
        if story is None:
            title = str(g.get("title") or members[0].title).strip()
            story = NewsStory(company_id=company_id, title=title, first_seen_at=min(m.first_seen_at or now for m in members))
            db.add(story)
            db.flush()
        if g.get("summary") and not story.summary:
            story.summary = str(g["summary"]).strip()
        story.material = bool(story.material) or g.get("material") is True
        themes = [str(t).strip() for t in g.get("themes") or [] if str(t).strip()][:2]
        story.themes = sorted(set(story.themes or []) | set(themes)) or None
        story.last_seen_at = now
        for m in members:
            m.story_id = story.id
            assigned += 1
    db.commit()
    return assigned


async def group_new_articles(db: Session, llm: LLMService, company_id: str, company_name: str) -> int:
    """Group the company's unassigned articles. Returns how many were assigned (0 on LLM failure)."""
    now = datetime.now(timezone.utc)
    articles = (
        db.query(NewsArticle)
        .filter(NewsArticle.company_id == company_id, NewsArticle.story_id.is_(None),
                NewsArticle.first_seen_at >= now - timedelta(days=14))
        .order_by(NewsArticle.published_at.desc().nulls_last())
        .limit(MAX_ARTICLES)
        .all()
    )
    if not articles:
        return 0
    stories = (
        db.query(NewsStory)
        .filter(NewsStory.company_id == company_id, NewsStory.last_seen_at >= now - timedelta(days=RECENT_STORY_DAYS))
        .order_by(NewsStory.last_seen_at.desc())
        .limit(15)
        .all()
    )
    themes = sorted({
        t
        for (ts,) in db.query(NewsStory.themes).filter(
            NewsStory.company_id == company_id, NewsStory.first_seen_at >= now - timedelta(days=THEME_DAYS)
        )
        for t in ts or []
    })
    reply = await llm.generate(build_prompt(company_name, articles, stories, themes), timeout=120, json_mode=True)
    if reply is None:
        logger.warning(f"Story grouping skipped for {company_name}: {llm.last_error}")
        return 0
    return apply_groups(db, company_id, parse_reply(reply), articles, stories)


def theme_trends(db: Session, company_id: str, weeks: int = 8, now: Optional[datetime] = None) -> list[dict]:
    """Per theme: material stories per week (oldest first) over the last `weeks` weeks, most frequent first."""
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(weeks=weeks)
    counts: dict[str, list[int]] = {}
    stories = db.query(NewsStory).filter(
        NewsStory.company_id == company_id, NewsStory.first_seen_at >= start, NewsStory.material.is_(True)
    )
    for story in stories:
        week = min(weeks - 1, int((story.first_seen_at - start).days // 7))
        for t in story.themes or []:
            counts.setdefault(t, [0] * weeks)[week] += 1
    trends = [
        {"theme": t, "weekly": c, "total": sum(c), "rising": sum(c[-2:]) > sum(c[-4:-2]) and sum(c[-2:]) >= 2}
        for t, c in counts.items()
    ]
    return sorted(trends, key=lambda x: (-x["total"], x["theme"]))[:8]
