from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Company, Filing, NewsStory
from ..services.scorecard import scorecard
from ..services.stories import theme_trends

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/scorecard")
def get_scorecard(horizon: int = Query(30, ge=1, le=365), company_id: Optional[str] = None, db: Session = Depends(get_db)):
    """How the AI's bullish/bearish calls played out `horizon` days later."""
    return scorecard(db, horizon, company_id)


@router.get("/companies/{company_id}/filings")
def get_filings(company_id: str, db: Session = Depends(get_db)):
    if not db.get(Company, company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    filings = db.query(Filing).filter(Filing.company_id == company_id).order_by(Filing.filed_on.desc()).limit(50)
    return [
        {"id": f.id, "form": f.form, "filed_on": f.filed_on, "items": f.items, "url": f.url,
         "summary": f.summary, "new_risks": f.new_risks, "routine": bool(f.routine)}
        for f in filings
    ]


@router.get("/companies/{company_id}/themes")
def get_themes(company_id: str, weeks: int = Query(8, ge=2, le=52), db: Session = Depends(get_db)):
    return theme_trends(db, company_id, weeks)


@router.get("/news/stories")
def get_stories(company_id: Optional[str] = None, material_only: bool = False, limit: int = Query(100, le=500),
                db: Session = Depends(get_db)):
    """News grouped into stories, most recently active first, with their articles."""
    q = db.query(NewsStory).options(joinedload(NewsStory.articles), joinedload(NewsStory.company))
    if company_id:
        q = q.filter(NewsStory.company_id == company_id)
    if material_only:
        q = q.filter(NewsStory.material.is_(True))
    stories = q.order_by(NewsStory.last_seen_at.desc()).limit(limit).all()
    return [
        {
            "id": s.id, "company_id": s.company_id, "company_name": s.company.name, "company_ticker": s.company.ticker,
            "title": s.title, "summary": s.summary, "material": s.material, "themes": s.themes or [],
            "first_seen_at": s.first_seen_at, "last_seen_at": s.last_seen_at,
            "articles": sorted(
                ({"id": a.id, "title": a.title, "url": a.url, "source": a.source, "published_at": a.published_at}
                 for a in s.articles),
                key=lambda a: -(a["published_at"] or 0),
            ),
        }
        for s in stories
    ]
