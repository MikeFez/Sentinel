"""Storing news articles once per company, across syncs."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models import NewsArticle


def _timestamp(article: dict) -> Optional[int]:
    """Unix seconds from Finnhub's `published_at` or Google News' `date` (ISO or RFC 822)."""
    ts = article.get("published_at")
    if isinstance(ts, (int, float)) and ts > 0:
        return int(ts)
    raw = article.get("date")
    if not raw:
        return None
    for parse in (datetime.fromisoformat, parsedate_to_datetime):
        try:
            dt = parse(str(raw))
        except (ValueError, TypeError):
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    return None


def normalize_article(article: dict) -> Optional[dict]:
    """The stored fields for an article, or None if it has no URL or title."""
    url = (article.get("url") or "").strip()
    title = (article.get("title") or "").strip()
    if not url or not title:
        return None
    return {
        "url": url,
        "title": title,
        "source": (article.get("source") or "").strip() or None,
        "summary": (article.get("summary") or "").strip() or None,
        "published_at": _timestamp(article),
    }


def store_articles(db: Session, company_id: str, articles: list) -> int:
    """Add articles not already stored for this company. Returns how many were new."""
    existing = {url for (url,) in db.query(NewsArticle.url).filter(NewsArticle.company_id == company_id)}
    added = 0
    for article in articles or []:
        a = normalize_article(article)
        if not a or a["url"] in existing:
            continue
        existing.add(a["url"])
        db.add(NewsArticle(company_id=company_id, **a))
        added += 1
    db.flush()  # the session doesn't autoflush; later lookups must see these
    return added
