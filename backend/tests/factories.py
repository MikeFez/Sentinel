from datetime import datetime, timedelta, timezone

from app.models import Company, Sync
from app.models.sync import SyncStatus, SentimentType


def company(db, name="Acme", ticker="ACME", status="public", **kw):
    c = Company(name=name, ticker=ticker, status=status, **kw)
    db.add(c)
    db.commit()
    return c


def sync(db, company, hours_ago=0.0, status=SyncStatus.completed, sentiment=None, summary=None, **kw):
    s = Sync(
        company_id=company.id,
        status=status,
        synced_at=kw.pop("synced_at", None) or datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        ai_sentiment=SentimentType(sentiment) if sentiment else None,
        ai_summary=summary,
        **kw,
    )
    db.add(s)
    db.commit()
    return s
