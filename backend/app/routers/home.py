from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta, date
from ..database import get_db
from ..models import Company, Sync, SyncStatus
from ..schemas.sync import SyncResponse

router = APIRouter(prefix="/api/home", tags=["home"])


@router.get("/summary")
def get_home_summary(db: Session = Depends(get_db)):
    """Get aggregated home dashboard data"""

    # Get total company count
    total_companies = db.query(Company).count()

    # Get companies by status
    companies_by_status = (
        db.query(Company.status, func.count(Company.id))
        .group_by(Company.status)
        .all()
    )
    status_counts = {status: count for status, count in companies_by_status}

    # Get recent syncs (last 10 across all companies)
    recent_syncs = (
        db.query(Sync)
        .filter(Sync.status == SyncStatus.completed)
        .options(joinedload(Sync.company))
        .order_by(desc(Sync.synced_at))
        .limit(10)
        .all()
    )

    # Format recent syncs with company info
    recent_activity = []
    for sync in recent_syncs:
        recent_activity.append({
            "sync_id": sync.id,
            "company_id": sync.company_id,
            "company_name": sync.company.name,
            "company_ticker": sync.company.ticker,
            "synced_at": sync.synced_at.isoformat(),
            "stock_price": sync.stock_price,
            "price_change": sync.price_change,
            "ai_sentiment": sync.ai_sentiment.value if sync.ai_sentiment else None,
            "ai_summary": sync.ai_summary,
        })

    # Find stale companies (no sync in last 7 days or never synced)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    # Get all companies with their latest sync
    companies_with_syncs = (
        db.query(Company)
        .outerjoin(Sync)
        .group_by(Company.id)
        .having(
            (func.max(Sync.synced_at).is_(None)) |
            (func.max(Sync.synced_at) < seven_days_ago)
        )
        .all()
    )

    stale_companies = []
    for company in companies_with_syncs:
        # Get latest sync for this company
        latest_sync = (
            db.query(Sync)
            .filter(Sync.company_id == company.id)
            .order_by(desc(Sync.synced_at))
            .first()
        )

        stale_companies.append({
            "id": company.id,
            "name": company.name,
            "ticker": company.ticker,
            "status": company.status.value if hasattr(company.status, 'value') else company.status,
            "last_sync": latest_sync.synced_at.isoformat() if latest_sync else None,
            "days_since_sync": (
                (datetime.utcnow() - latest_sync.synced_at).days
                if latest_sync
                else None
            ),
        })

    # Sort by staleness (never synced first, then by days)
    stale_companies.sort(
        key=lambda x: (x["last_sync"] is None, x["days_since_sync"] or 9999),
        reverse=True
    )

    # Get sentiment distribution from recent syncs
    sentiment_counts = (
        db.query(Sync.ai_sentiment, func.count(Sync.id))
        .filter(Sync.ai_sentiment.isnot(None))
        .filter(Sync.status == SyncStatus.completed)
        .filter(Sync.synced_at >= seven_days_ago)
        .group_by(Sync.ai_sentiment)
        .all()
    )
    sentiment_distribution = {
        sentiment.value if hasattr(sentiment, 'value') else sentiment: count
        for sentiment, count in sentiment_counts
    }

    # Collect upcoming earnings from latest syncs
    max_sync_subq = (
        db.query(Sync.company_id, func.max(Sync.synced_at).label("max_synced_at"))
        .filter(Sync.status == SyncStatus.completed)
        .group_by(Sync.company_id)
        .subquery()
    )
    latest_syncs_all = (
        db.query(Sync)
        .join(
            max_sync_subq,
            (Sync.company_id == max_sync_subq.c.company_id)
            & (Sync.synced_at == max_sync_subq.c.max_synced_at),
        )
        .options(joinedload(Sync.company))
        .all()
    )

    today_str = date.today().isoformat()
    upcoming_earnings = []
    for sync in latest_syncs_all:
        if not sync.earnings_dates:
            continue
        for entry in sync.earnings_dates:
            entry_date = entry.get("date", "")
            if entry_date and entry_date >= today_str:
                upcoming_earnings.append({
                    "company_id": sync.company_id,
                    "company_name": sync.company.name,
                    "ticker": sync.company.ticker,
                    "date": entry_date,
                    "eps_estimate": entry.get("epsEstimate"),
                    "quarter": entry.get("quarter"),
                    "year": entry.get("year"),
                })

    upcoming_earnings.sort(key=lambda x: x["date"])
    upcoming_earnings = upcoming_earnings[:10]

    return {
        "total_companies": total_companies,
        "status_counts": status_counts,
        "recent_activity": recent_activity,
        "stale_companies": stale_companies,
        "sentiment_distribution": sentiment_distribution,
        "upcoming_earnings": upcoming_earnings,
    }
