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
# After any sync attempt, wait this long before a drift sync (so a failing LLM doesn't retry every check)
DRIFT_RETRY_HOURS = 12


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


def drift_reason(company: Company, analysis_price: Optional[float], last_sync_at: Optional[datetime],
                 threshold: float, now: datetime) -> Optional[str]:
    """A sync is due when the price has moved `threshold`% from the price the last analysis was written at."""
    price = company.quote_price
    if threshold <= 0 or not analysis_price or price is None:
        return None
    if last_sync_at is not None and last_sync_at > now - timedelta(hours=DRIFT_RETRY_HOURS):
        return None
    change = (price / analysis_price - 1) * 100
    if abs(change) < threshold:
        return None
    return f"Price {'+' if change >= 0 else '−'}{abs(change):.0f}% since the last analysis"


def due_event_syncs(db: Session, move_threshold: float, earnings: bool, now: Optional[datetime] = None,
                    drift_threshold: float = 0) -> list[tuple[str, str]]:
    """[(company_id, reason)] for public companies that should sync because of an event."""
    now = now or datetime.now(timezone.utc)
    newest: dict = {}
    newest_completed: dict = {}
    newest_analysis: dict = {}
    for s in db.query(Sync).order_by(Sync.synced_at.desc()):
        newest.setdefault(s.company_id, s)
        if s.status == SyncStatus.completed:
            newest_completed.setdefault(s.company_id, s)
            if s.ai_summary:
                newest_analysis.setdefault(s.company_id, s)

    due = []
    for c in db.query(Company).filter(Company.status == "public", Company.ticker.isnot(None)):
        last = newest.get(c.id)
        if last is not None and last.status == SyncStatus.syncing:
            continue
        done = newest_completed.get(c.id)
        reason = move_reason(c, last.synced_at if last else None, move_threshold, now)
        if not reason and earnings and done is not None:
            reason = earnings_reason(done.earnings_dates, done.synced_at, now)
        if not reason:
            analysis = newest_analysis.get(c.id)
            reason = drift_reason(c, analysis.stock_price if analysis else None,
                                  last.synced_at if last else None, drift_threshold, now)
        if reason:
            due.append((c.id, reason))
    return due


# ── Analyst and insider signals ───────────────────────────────────────────────
# Checked once a day per public company with two cheap Finnhub calls; a meaningful change
# against the last sync triggers a full sync.

ANALYST_MIN_CHANGE = 3  # ratings that must move between buy / hold / sell buckets in total
INSIDER_MIN_VALUE = 1_000_000  # dollars, for open-market purchases (P) and sales (S)
SIGNAL_CHECK_HOURS = 24


def _buckets(r: Optional[dict]) -> Optional[tuple[int, int, int]]:
    if not r:
        return None
    return (
        (r.get("strong_buy") or 0) + (r.get("buy") or 0),
        r.get("hold") or 0,
        (r.get("sell") or 0) + (r.get("strong_sell") or 0),
    )


def analyst_reason(old: Optional[dict], new: Optional[dict]) -> Optional[str]:
    """E.g. "Analyst ratings changed: buy 21→18, hold 5→7, sell 0→1", if enough ratings moved
    or the consensus (the biggest bucket) changed."""
    a, b = _buckets(old), _buckets(new)
    if a is None or b is None or a == b:
        return None
    moved = sum(abs(x - y) for x, y in zip(a, b))
    consensus_changed = sum(a) and sum(b) and a.index(max(a)) != b.index(max(b))
    if moved < ANALYST_MIN_CHANGE and not consensus_changed:
        return None
    parts = [f"{label} {x}→{y}" for label, x, y in zip(("buy", "hold", "sell"), a, b) if x != y]
    return "Analyst ratings changed: " + ", ".join(parts)


def _trade_key(t: dict) -> tuple:
    return (t.get("name"), t.get("transactionDate"), t.get("change"))


def insider_reason(old: Optional[list], new: Optional[list], price: Optional[float]) -> Optional[str]:
    """The largest new open-market insider purchase or sale worth at least INSIDER_MIN_VALUE."""
    seen = {_trade_key(t) for t in old or []}
    best = None
    for t in new or []:
        if _trade_key(t) in seen or t.get("transactionCode") not in ("P", "S"):
            continue
        shares = abs(t.get("change") or 0)
        value = shares * (t.get("transactionPrice") or price or 0)
        if value >= INSIDER_MIN_VALUE and (best is None or value > best[0]):
            best = (value, t, shares)
    if not best:
        return None
    value, t, shares = best
    verb = "bought" if t["transactionCode"] == "P" else "sold"
    return f"Insider {t.get('name', 'unknown').title()} {verb} {shares:,.0f} shares (~${value / 1e6:.1f}M)"


_last_signal_check: dict[str, datetime] = {}


def due_signal_syncs(db: Session, api_key: str, now: Optional[datetime] = None) -> list[tuple[str, str]]:
    """[(company_id, reason)] for analyst or insider changes. Blocking (Finnhub): run in a thread."""
    from .stock_service import StockService

    now = now or datetime.now(timezone.utc)
    service = StockService(api_key)
    newest: dict = {}
    for s in db.query(Sync).filter(Sync.status.in_([SyncStatus.completed, SyncStatus.syncing])).order_by(Sync.synced_at.desc()):
        newest.setdefault(s.company_id, s)

    due = []
    for c in db.query(Company).filter(Company.status == "public", Company.ticker.isnot(None)):
        last = newest.get(c.id)
        checked = _last_signal_check.get(c.id)
        if last is None or last.status == SyncStatus.syncing:
            continue  # nothing to compare with yet, or already syncing
        if checked and now - checked < timedelta(hours=SIGNAL_CHECK_HOURS):
            continue
        _last_signal_check[c.id] = now
        reason = analyst_reason(last.analyst_ratings, service.get_analyst_recommendations(c.ticker)) or insider_reason(
            last.insider_transactions, service.get_insider_transactions(c.ticker), c.quote_price
        )
        if reason:
            due.append((c.id, reason))
    return due
