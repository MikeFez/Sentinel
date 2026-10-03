from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import NewsArticle

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/feed")
def get_news_feed(limit: int = 200, company_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Stored news across all companies (or one), newest first."""
    q = db.query(NewsArticle).options(joinedload(NewsArticle.company))
    if company_id:
        q = q.filter(NewsArticle.company_id == company_id)
    articles = q.order_by(NewsArticle.published_at.desc().nulls_last(), NewsArticle.first_seen_at.desc()).limit(limit)
    return [
        {
            "id": a.id,
            "company_id": a.company_id,
            "company_name": a.company.name,
            "company_ticker": a.company.ticker,
            "title": a.title,
            "url": a.url,
            "source": a.source,
            "published_at": a.published_at,
            "summary": a.summary or "",
            "first_seen_at": a.first_seen_at,
        }
        for a in articles
    ]
