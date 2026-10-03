"""Keeping the database small: old syncs keep their prices and analysis but drop bulky detail."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import ActivityEvent, Filing, NewsArticle, NewsStory, Sync

logger = logging.getLogger(__name__)

# Activity events (the observability log) are kept this long regardless of history_detail_days
ACTIVITY_KEEP_DAYS = 14

# Stored news articles are kept this many times longer than sync detail
NEWS_KEEP_FACTOR = 6

# Large per-sync fields that only matter for recent syncs
DETAIL_COLUMNS = ("raw_news", "llm_prompt", "insider_transactions", "financials", "earnings_dates", "analyst_ratings")


def prune_history(db: Session, days: float, now: Optional[datetime] = None) -> int:
    """Clear DETAIL_COLUMNS on syncs older than `days`, except each company's newest sync, and delete
    news articles older than days * NEWS_KEEP_FACTOR.

    Returns the number of syncs and articles pruned. days <= 0 keeps everything.
    """
    now = now or datetime.now(timezone.utc)
    events = db.query(ActivityEvent).filter(ActivityEvent.at < now - timedelta(days=ACTIVITY_KEEP_DAYS)).delete(
        synchronize_session=False
    )
    db.commit()
    if days <= 0:
        return events
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)

    newest = {}
    for sync_id, company_id in db.query(Sync.id, Sync.company_id).order_by(Sync.synced_at.desc()):
        newest.setdefault(company_id, sync_id)

    has_detail = None
    for col in DETAIL_COLUMNS:
        cond = getattr(Sync, col).isnot(None)
        has_detail = cond if has_detail is None else (has_detail | cond)

    pruned = (
        db.query(Sync)
        .filter(Sync.synced_at < cutoff, Sync.id.notin_(list(newest.values())), has_detail)
        .update({getattr(Sync, col): None for col in DETAIL_COLUMNS}, synchronize_session=False)
    )
    news_cutoff = int(((now or datetime.now(timezone.utc)) - timedelta(days=days * NEWS_KEEP_FACTOR)).timestamp())
    old_news = (
        db.query(NewsArticle)
        .filter(NewsArticle.published_at.isnot(None), NewsArticle.published_at < news_cutoff)
        .delete(synchronize_session=False)
    )
    pruned += old_news + events
    # Stories whose articles are all gone
    db.query(NewsStory).filter(~NewsStory.articles.any()).delete(synchronize_session=False)
    # Only each company's newest 10-K needs its full Risk Factors text (to compare with the next one)
    latest_10k = {}
    for fid, cid in db.query(Filing.id, Filing.company_id).filter(Filing.form == "10-K").order_by(Filing.filed_on.desc()):
        latest_10k.setdefault(cid, fid)
    db.query(Filing).filter(Filing.risk_text.isnot(None), Filing.id.notin_(list(latest_10k.values()))).update(
        {Filing.risk_text: None}, synchronize_session=False
    )
    db.commit()
    if pruned and db.bind.dialect.name == "sqlite":
        with db.bind.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM"))
    if pruned:
        logger.info(f"Pruned {pruned - old_news - events} old sync(s), {old_news} article(s), {events} activity event(s)")
    return pruned
