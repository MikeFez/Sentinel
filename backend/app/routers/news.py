from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
from ..database import get_db
from ..models import Company, Sync, SyncStatus

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/feed")
def get_news_feed(limit: int = 100, db: Session = Depends(get_db)):
    """
    Aggregate raw_news from every company's latest completed sync,
    flatten and sort by published_at descending.
    """
    # One query: latest completed sync per company
    max_sync_subq = (
        db.query(Sync.company_id, func.max(Sync.synced_at).label("max_synced_at"))
        .filter(Sync.status == SyncStatus.completed)
        .group_by(Sync.company_id)
        .subquery()
    )
    latest_syncs = (
        db.query(Sync)
        .join(
            max_sync_subq,
            (Sync.company_id == max_sync_subq.c.company_id)
            & (Sync.synced_at == max_sync_subq.c.max_synced_at),
        )
        .options(joinedload(Sync.company))
        .all()
    )

    articles = []
    for sync in latest_syncs:
        if not sync.raw_news:
            continue
        for article in sync.raw_news:
            articles.append({
                "company_id": sync.company_id,
                "company_name": sync.company.name,
                "company_ticker": sync.company.ticker,
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source"),
                "published_at": article.get("published_at", 0),
                "summary": article.get("summary", ""),
            })

    articles.sort(key=lambda a: a["published_at"] or 0, reverse=True)
    return articles[:limit]
