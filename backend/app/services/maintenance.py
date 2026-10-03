"""Keeping the database small: old syncs keep their prices and analysis but drop bulky detail."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Sync

logger = logging.getLogger(__name__)

# Large per-sync fields that only matter for recent syncs
DETAIL_COLUMNS = ("raw_news", "llm_prompt", "insider_transactions", "financials", "earnings_dates", "analyst_ratings")


def prune_history(db: Session, days: float, now: Optional[datetime] = None) -> int:
    """Clear DETAIL_COLUMNS on syncs older than `days`, except each company's newest sync.

    Returns the number of syncs pruned. days <= 0 keeps everything.
    """
    if days <= 0:
        return 0
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
    db.commit()
    if pruned and db.bind.dialect.name == "sqlite":
        with db.bind.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM"))
    if pruned:
        logger.info(f"Pruned detail from {pruned} old sync(s)")
    return pruned
