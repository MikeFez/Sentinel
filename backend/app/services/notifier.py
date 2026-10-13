"""Notifications: price alerts, big moves, sentiment flips, earnings, material news, filings, problems
and a weekly digest, sent through Apprise to the NOTIFY_URLS destinations.

Every event has a `key`; one already in the notifications table isn't sent again, so callers can
report the same event as often as they see it. Sending is blocking (call it from a worker thread in
async code) and never raises: a failed notification is logged, not allowed to break a sync.
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..config import settings as app_settings
from ..database import SessionLocal
from ..models import Company, DailyPrice, Filing, NewsStory, Notification, Sync
from ..models.sync import SyncStatus
from . import activity
from .price_history import NEW_YORK

logger = logging.getLogger(__name__)

KINDS = ("price_alerts", "big_moves", "sentiment_flips", "earnings", "material_news", "filings", "problems", "digest")
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DIGEST_HOUR = 8  # New York time, on notify_digest_day


# ── Destinations and sending ─────────────────────────────────────────────────

def destinations() -> list[str]:
    return [u for u in re.split(r"[\s,]+", app_settings.notify_urls or "") if u]


def services() -> list[str]:
    """The destinations' kinds (URL schemes like "ntfy" or "discord"), safe to show: no tokens."""
    return sorted({urlparse(u).scheme or "?" for u in destinations()})


def _send(title: str, body: str) -> Optional[str]:
    """Deliver to every destination. Returns None on success, else an error."""
    urls = destinations()
    if not urls:
        return "No destinations: set the NOTIFY_URLS environment variable"
    try:
        import apprise

        a = apprise.Apprise()
        bad = [u for u in urls if not a.add(u)]
        if len(bad) == len(urls):
            return "None of the NOTIFY_URLS could be understood (check the Apprise URL format)"
        if not a.notify(title=title, body=body):
            return "A destination refused or didn't respond (see the container log)"
        return f"{len(bad)} of the NOTIFY_URLS couldn't be understood" if bad else None
    except Exception as e:  # never let a notification break the caller
        return f"{type(e).__name__}: {e}"


def enabled(db: Session, kind: str) -> bool:
    from ..routers.settings import get_setting

    return get_setting(db, f"notify_{kind}") == "true"


def link(company_id: Optional[str] = None) -> str:
    base = app_settings.sentinel_url.rstrip("/")
    if not base:
        return ""
    return f"\n{base}/companies/{company_id}" if company_id else f"\n{base}/"


def notify(db: Session, kind: str, key: str, title: str, body: str, company_id: Optional[str] = None,
           force: bool = False) -> Optional[Notification]:
    """Send one notification unless it's switched off, nowhere to send it, or `key` was sent before.

    `force` skips those checks (the Settings test button). Returns the recorded row, if it was sent.
    """
    try:
        if not force:
            if not destinations() or not enabled(db, kind):
                return None
            if db.query(Notification.id).filter(Notification.key == key).first():
                return None
        with activity.track("notify", kind, company_id) as t:
            error = _send(title, body + link(company_id))
            if error:
                t.fail(error)
        row = Notification(key=key if not force else f"{key}:{datetime.now(timezone.utc).isoformat()}", kind=kind,
                           company_id=company_id, title=title[:200], body=body, status="failed" if error else "sent",
                           error=error)
        db.add(row)
        db.commit()
        return row
    except Exception:
        logger.exception(f"Notification {key} failed")
        db.rollback()
        return None


def _today(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(NEW_YORK).date().isoformat()


def _name(c: Company) -> str:
    return c.ticker or c.name


def _money(v: Optional[float]) -> str:
    return "—" if v is None else f"${v:,.2f}"


def _pct(v: Optional[float]) -> str:
    return "—" if v is None else f"{'+' if v >= 0 else '−'}{abs(v):.1f}%"


# ── Quote refresh: price alerts and big moves ────────────────────────────────

def after_quote(db: Session, company: Company, old_price: Optional[float], move_threshold: float,
                now: Optional[datetime] = None) -> None:
    """Called with each new quote. Alerts fire when the price crosses a level (not every refresh it stays
    past it), at most once per level per day; a big move at most once per day."""
    price, change, day = company.quote_price, company.quote_change, _today(now)
    if price is None:
        return
    for side, level in (("above", company.alert_above), ("below", company.alert_below)):
        if level is None:
            continue
        past = price >= level if side == "above" else price <= level
        was_past = old_price is not None and (old_price >= level if side == "above" else old_price <= level)
        if past and not was_past:
            notify(db, "price_alerts", f"alert:{company.id}:{side}:{level}:{day}",
                   f"{_name(company)} is {side} {_money(level)}",
                   f"{company.name} is at {_money(price)} ({_pct(change)} today), {side} your {_money(level)} alert.",
                   company.id)
    if move_threshold > 0 and change is not None and abs(change) >= move_threshold:
        notify(db, "big_moves", f"move:{company.id}:{day}", f"{_name(company)} {_pct(change)} today",
               f"{company.name} is at {_money(price)}, {_pct(change)} today."
               + (" A new analysis is queued." if company.status == "public" else ""), company.id)


# ── After a sync: sentiment flips, earnings, material news, problems ────────

def after_sync(sync_id: str) -> None:
    """Notifications for what a finished sync found. Blocking: run it in a worker thread."""
    db = SessionLocal()
    try:
        sync = db.get(Sync, sync_id)
        if sync is None:
            return
        company = db.get(Company, sync.company_id)
        if company is None:
            return
        if sync.status == SyncStatus.failed:
            _problem(db, "sync", f"Syncs are failing ({company.name})", sync.error or "Sync failed")
            return
        if sync.error and sync.error.startswith("AI analysis unavailable"):
            _problem(db, "llm", "AI analysis is failing", f"{company.name}: {sync.error}")

        if sync.ai_sentiment:
            previous = (
                db.query(Sync)
                .filter(Sync.company_id == company.id, Sync.id != sync.id, Sync.status == SyncStatus.completed,
                        Sync.ai_sentiment.isnot(None), Sync.synced_at < sync.synced_at)
                .order_by(Sync.synced_at.desc())
                .first()
            )
            if previous and previous.ai_sentiment != sync.ai_sentiment:
                notify(db, "sentiment_flips", f"flip:{sync.id}",
                       f"{_name(company)}: {previous.ai_sentiment.value} → {sync.ai_sentiment.value}",
                       sync.ai_changes or (sync.ai_summary or "")[:400], company.id)

        if (sync.reason or "").startswith("Earnings reported"):
            q = next((q for q in sync.earnings_history or [] if q.get("actual") is not None), None)
            lines = []
            if q:
                est, s = q.get("estimate"), q.get("surprisePercent")
                lines.append(f"EPS {q['actual']:.3f}" + (f" vs. {est:.3f} expected" if est is not None else "")
                             + (f" ({'beat' if s >= 0 else 'miss'} {abs(s):.1f}%)" if s is not None else "") + ".")
            if sync.ai_sentiment:
                lines.append(f"Sentiment now {sync.ai_sentiment.value}.")
            if sync.ai_changes:
                lines.append(sync.ai_changes)
            notify(db, "earnings", f"earnings:{sync.id}", f"{_name(company)} reported results",
                   " ".join(lines) or "Results are out; the analysis has been updated.", company.id)

        if sync.started_at:
            stories = (
                db.query(NewsStory)
                .filter(NewsStory.company_id == company.id, NewsStory.material.is_(True),
                        NewsStory.last_seen_at >= sync.started_at)
                .all()
            )
            for story in stories:
                themes = f" [{', '.join(story.themes)}]" if story.themes else ""
                notify(db, "material_news", f"story:{story.id}", f"{_name(company)}: {story.title}",
                       (story.summary or story.title) + themes, company.id)
    except Exception:
        logger.exception(f"Notifications after sync {sync_id} failed")
    finally:
        db.close()


def _problem(db: Session, what: str, title: str, body: str) -> None:
    """Problems are sent at most once a day each, however many syncs hit them."""
    notify(db, "problems", f"problem:{what}:{_today()}", title, body[:500])


# ── SEC filings ──────────────────────────────────────────────────────────────

def after_filing(filing_id: str) -> None:
    """A newly summarized filing (routine 8-Ks are skipped). Blocking: run it in a worker thread."""
    db = SessionLocal()
    try:
        filing = db.get(Filing, filing_id)
        company = filing and db.get(Company, filing.company_id)
        if company is None or filing.routine or not filing.summary:
            return
        notify(db, "filings", f"filing:{filing.accession}", f"{_name(company)} filed a {filing.form}",
               filing.summary, company.id)
    except Exception:
        logger.exception(f"Notification for filing {filing_id} failed")
    finally:
        db.close()


# ── Weekly digest ────────────────────────────────────────────────────────────

def maybe_send_digest(now: Optional[datetime] = None) -> None:
    """On the digest day after DIGEST_HOUR (New York), send the week's summary once. Blocking."""
    from ..routers.settings import get_setting

    now = now or datetime.now(timezone.utc)
    ny = now.astimezone(NEW_YORK)
    db = SessionLocal()
    try:
        day = get_setting(db, "notify_digest_day")
        if DAYS[ny.weekday()] != day or ny.hour < DIGEST_HOUR:
            return
        week = ny.isocalendar()
        key = f"digest:{week.year}-W{week.week:02d}"
        if db.query(Notification.id).filter(Notification.key == key).first():
            return
        title, body = build_digest(db, now)
        notify(db, "digest", key, title, body)
    except Exception:
        logger.exception("Weekly digest failed")
    finally:
        db.close()


# How far before the start of the week a "price a week ago" may be (weekends, a missed close)
WEEK_START_SLACK_DAYS = 4


def _price_week_ago(db: Session, company_id: str, day: str) -> Optional[float]:
    """The last price on or before `day`, if it's from within a few days of it; an older one (from a gap
    in the data) would turn a months-long move into "this week"."""
    earliest = (datetime.fromisoformat(day) - timedelta(days=WEEK_START_SLACK_DAYS)).date().isoformat()
    row = (
        db.query(DailyPrice)
        .filter(DailyPrice.company_id == company_id, DailyPrice.day <= day, DailyPrice.day >= earliest)
        .order_by(DailyPrice.day.desc())
        .first()
    )
    return row.price if row else None


def build_digest(db: Session, now: datetime) -> tuple[str, str]:
    """(title, body) for the week ending `now`."""
    week_ago = now - timedelta(days=7)
    start_day = week_ago.astimezone(NEW_YORK).date().isoformat()
    companies = db.query(Company).order_by(Company.name).all()
    lines: list[str] = []

    # Portfolio over the week (positions with a price a week ago and now)
    total_now = total_then = 0.0
    movers = []
    for c in companies:
        now_price = c.quote_price
        then = _price_week_ago(db, c.id, start_day)
        if now_price is None or then is None:
            continue
        change = (now_price / then - 1) * 100
        movers.append((c, change))
        if (c.shares_owned or 0) > 0:
            total_now += now_price * c.shares_owned
            total_then += then * c.shares_owned
    week_change = (total_now / total_then - 1) * 100 if total_then else None
    if total_then:
        lines.append(f"Portfolio: {_money(total_now)} ({_pct(week_change)} this week)")
    if movers:
        movers.sort(key=lambda m: -abs(m[1]))
        lines.append("Moves: " + ", ".join(f"{_name(c)} {_pct(ch)}" for c, ch in movers[:5]))

    # Sentiment now vs. at the start of the week (not just the last two analyses)
    flips = []
    analyses = db.query(Sync).filter(Sync.status == SyncStatus.completed, Sync.ai_sentiment.isnot(None))
    for c in companies:
        mine = analyses.filter(Sync.company_id == c.id)
        latest = mine.order_by(Sync.synced_at.desc()).first()
        before = mine.filter(Sync.synced_at < week_ago).order_by(Sync.synced_at.desc()).first()
        if latest and before and latest.synced_at >= week_ago and latest.ai_sentiment != before.ai_sentiment:
            flips.append(f"{_name(c)} {before.ai_sentiment.value} → {latest.ai_sentiment.value}")
    if flips:
        lines.append("Sentiment changes: " + ", ".join(flips))

    # Material news this week
    stories = (
        db.query(NewsStory)
        .filter(NewsStory.material.is_(True), NewsStory.last_seen_at >= week_ago)
        .order_by(NewsStory.last_seen_at.desc())
        .limit(5)
        .all()
    )
    by_id = {c.id: c for c in companies}
    if stories:
        lines.append("Material news:")
        lines += [f"- {_name(by_id[s.company_id])}: {s.title}" for s in stories if s.company_id in by_id]

    # Earnings in the coming week
    upcoming = []
    today = now.astimezone(NEW_YORK).date()
    for c in companies:
        last = (
            db.query(Sync)
            .filter(Sync.company_id == c.id, Sync.status == SyncStatus.completed, Sync.earnings_dates.isnot(None))
            .order_by(Sync.synced_at.desc())
            .first()
        )
        for e in (last.earnings_dates if last else None) or []:
            try:
                d = datetime.fromisoformat(e.get("date", "")).date()
            except ValueError:
                continue
            if today <= d <= today + timedelta(days=7):
                upcoming.append(f"{_name(c)} {d:%a %b} {d.day}")
    if upcoming:
        lines.append("Earnings this week: " + ", ".join(upcoming))

    title = "Sentinel weekly" + (f": portfolio {_pct(week_change)}" if week_change is not None else "")
    return title, "\n".join(lines) or "A quiet week: no notable moves, sentiment changes or material news."
