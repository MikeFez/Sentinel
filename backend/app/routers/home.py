from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload, load_only

from ..database import get_db
from ..models import Sync, SyncStatus

router = APIRouter(prefix="/api/home", tags=["home"])


@router.get("/summary")
def get_home_summary(db: Session = Depends(get_db)):
    """Dashboard data not already in /api/companies: upcoming earnings from each company's latest sync."""
    latest: dict = {}
    for sync in (
        db.query(Sync)
        .options(load_only(Sync.company_id, Sync.synced_at, Sync.earnings_dates), joinedload(Sync.company))
        .filter(Sync.status == SyncStatus.completed)
        .order_by(Sync.synced_at.desc())
    ):
        latest.setdefault(sync.company_id, sync)

    today = date.today().isoformat()
    upcoming = [
        {
            "company_id": sync.company_id,
            "company_name": sync.company.name,
            "ticker": sync.company.ticker,
            "date": entry["date"],
            "eps_estimate": entry.get("epsEstimate"),
            "quarter": entry.get("quarter"),
            "year": entry.get("year"),
        }
        for sync in latest.values()
        for entry in (sync.earnings_dates or [])
        if entry.get("date", "") >= today
    ]
    upcoming.sort(key=lambda e: e["date"])
    return {"upcoming_earnings": upcoming[:10]}
