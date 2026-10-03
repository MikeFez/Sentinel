"""Syncs triggered by events: a big price move, or results coming out after an earnings date."""
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Company, Sync
from ..models.sync import SyncStatus
from .quote_service import NEW_YORK

# Earnings are reported before the open or after the close; by this time on the day both are out
RESULTS_OUT = time(16, 30)
# Don't chase earnings older than this
EARNINGS_WINDOW_DAYS = 3


def session_open(now: datetime) -> datetime:
    """09:30 New York on `now`'s New York date (UTC)."""
    ny = now.astimezone(NEW_YORK)
    return datetime.combine(ny.date(), time(9, 30), tzinfo=NEW_YORK).astimezone(timezone.utc)


def move_reason(company: Company, last_sync_at: Optional[datetime], threshold: float, now: datetime) -> Optional[str]:
    """A sync is due if today's move is at least `threshold`% and nothing has synced since today's open."""
    change = company.quote_change
    if threshold <= 0 or change is None or abs(change) < threshold or company.quote_at is None:
        return None
    opened = session_open(now)
    if company.quote_at < opened:  # the move is from a previous session
        return None
    if last_sync_at is not None and last_sync_at >= opened:
        return None
    return f"Price moved {'+' if change >= 0 else '−'}{abs(change):.1f}% today"


def earnings_reason(earnings_dates: list, last_completed_at: Optional[datetime], now: datetime) -> Optional[str]:
    """A sync is due once results for a recent earnings date are out and we haven't synced since."""
    today = now.astimezone(NEW_YORK).date()
    for entry in earnings_dates or []:
        try:
            day = date.fromisoformat(entry.get("date", ""))
        except ValueError:
            continue
        if not (today - timedelta(days=EARNINGS_WINDOW_DAYS) <= day <= today):
            continue
        out = datetime.combine(day, RESULTS_OUT, tzinfo=NEW_YORK).astimezone(timezone.utc)
        if now >= out and (last_completed_at is None or last_completed_at < out):
            return f"Earnings reported {day.isoformat()}"
    return None


def due_event_syncs(db: Session, move_threshold: float, earnings: bool, now: Optional[datetime] = None) -> list[tuple[str, str]]:
    """[(company_id, reason)] for public companies that should sync because of an event."""
    now = now or datetime.now(timezone.utc)
    newest: dict = {}
    newest_completed: dict = {}
    for s in db.query(Sync).order_by(Sync.synced_at.desc()):
        newest.setdefault(s.company_id, s)
        if s.status == SyncStatus.completed:
            newest_completed.setdefault(s.company_id, s)

    due = []
    for c in db.query(Company).filter(Company.status == "public", Company.ticker.isnot(None)):
        last = newest.get(c.id)
        if last is not None and last.status == SyncStatus.syncing:
            continue
        done = newest_completed.get(c.id)
        reason = move_reason(c, last.synced_at if last else None, move_threshold, now)
        if not reason and earnings and done is not None:
            reason = earnings_reason(done.earnings_dates, done.synced_at, now)
        if reason:
            due.append((c.id, reason))
    return due
