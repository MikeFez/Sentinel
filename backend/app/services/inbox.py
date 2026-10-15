"""A briefing derived from stored events, with explicit review state."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.orm import joinedload, load_only
from sqlalchemy import func, or_
from ..models import Company, Filing, NewsStory, Sync, InboxReview
from ..models.sync import SyncStatus
from .evidence import safe_url


def change_inbox(db, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    companies = {c.id: c for c in db.query(Company)}
    reviews = {r.key: r for r in db.query(InboxReview)}
    entries = []

    def add(key, cid, kind, title, detail, at, weight, sources=(), tab="overview", href=None):
        c = companies.get(cid)
        if c is None:
            return
        review = reviews.get(key)
        state = "reviewed" if review and review.reviewed_at else (
            "snoozed" if review and review.snoozed_until and review.snoozed_until > now else "active")
        owned = (c.shares_owned or 0) > 0
        entries.append({"key": key, "company_id": cid, "company_name": c.name, "ticker": c.ticker,
                        "owned": owned, "kind": kind, "title": title, "detail": detail, "at": at,
                        "state": state, "snoozed_until": review.snoozed_until if review else None,
                        "href": href or f"/companies/{cid}" + (f"?tab={tab}" if tab != "overview" else ""),
                        "sources": list(sources), "priority": weight + (20 if owned else 0)})

    for s in db.query(NewsStory).options(joinedload(NewsStory.articles)).filter(
        NewsStory.material.is_(True), NewsStory.last_seen_at >= cutoff
    ):
        add(f"story:{s.id}:{s.last_seen_at.isoformat()}", s.company_id, "story", s.title,
            s.summary, s.last_seen_at, 40,
            [{"title": a.title, "url": safe_url(a.url)} for a in s.articles if safe_url(a.url)], "news")
    for f in db.query(Filing).filter(Filing.created_at >= cutoff, Filing.routine.isnot(True)):
        add(f"filing:{f.id}", f.company_id, "risk" if f.new_risks else "filing",
            f"New risk factors in {f.form}" if f.new_risks else f"New {f.form} filing",
            "; ".join(f.new_risks) if f.new_risks else f.summary, f.created_at, 60 if f.new_risks else 40,
            [{"title": f"{f.form} filed {f.filed_on}", "url": safe_url(f.url)}], "filings")

    previous = {}
    latest = {}
    # One predecessor per company is enough to detect the first flip in the lookback window.
    # Retain the latest sync too, even if old, for upcoming earnings calendars.
    ranked = db.query(Sync.id, func.row_number().over(
        partition_by=Sync.company_id, order_by=(Sync.synced_at.desc(), Sync.id.desc())
    ).label("rank")).filter(Sync.status == SyncStatus.completed, Sync.synced_at < cutoff,
                          Sync.ai_summary.isnot(None)).subquery()
    predecessors = db.query(ranked.c.id).filter(ranked.c.rank == 1)
    latest_ranked = db.query(Sync.id, func.row_number().over(
        partition_by=Sync.company_id, order_by=(Sync.synced_at.desc(), Sync.id.desc())
    ).label("rank")).filter(Sync.status == SyncStatus.completed).subquery()
    newest = db.query(latest_ranked.c.id).filter(latest_ranked.c.rank == 1)
    for s in db.query(Sync).options(load_only(
        Sync.id, Sync.company_id, Sync.synced_at, Sync.ai_summary, Sync.ai_sentiment,
        Sync.ai_changes, Sync.earnings_dates
    )).filter(Sync.status == SyncStatus.completed, or_(Sync.synced_at >= cutoff, Sync.id.in_(predecessors),
                                                     Sync.id.in_(newest))).order_by(Sync.synced_at, Sync.id):
        latest[s.company_id] = s
        if not s.ai_summary:
            continue
        prev = previous.get(s.company_id)
        if s.synced_at >= cutoff and prev:
            flipped = s.ai_sentiment and prev.ai_sentiment and s.ai_sentiment != prev.ai_sentiment
            if flipped or s.ai_changes:
                title = (f"Sentiment changed: {prev.ai_sentiment.value} → {s.ai_sentiment.value}"
                         if flipped else "Analysis updated")
                add(f"analysis:{s.id}", s.company_id, "sentiment" if flipped else "analysis",
                    title, s.ai_changes or s.ai_summary, s.synced_at, 50 if flipped else 10,
                    href=f"/companies/{s.company_id}?analysis={s.id}")
        previous[s.company_id] = s

    today = now.astimezone(ZoneInfo("America/New_York")).date()
    for s in latest.values():
        for e in s.earnings_dates or []:
            try:
                day = datetime.strptime(e.get("date", ""), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            if today <= day <= today + timedelta(days=7):
                add(f"earnings:{s.company_id}:{day.isoformat()}", s.company_id, "catalyst",
                    f"Earnings on {day.isoformat()}", "Upcoming catalyst: review the latest analysis before results.",
                    datetime.combine(day, datetime.min.time(), tzinfo=ZoneInfo("America/New_York")), 30)

    # Repeated earnings calendar entries are one catalyst; updated stories have a fresh review key.
    entries = list({e["key"]: e for e in entries}.values())
    entries.sort(key=lambda e: (-e["priority"], -e["at"].timestamp(), e["key"]))
    return entries
