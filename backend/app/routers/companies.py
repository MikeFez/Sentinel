from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, load_only
from typing import List
from ..database import get_db
from ..models import Company, Sync, CompanyTag
from ..models.sync import SyncStatus
from ..schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse
from ..schemas.tag import AssignTagsRequest
from ..services.sync_runner import Thresholds

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=List[CompanyListResponse])
def list_companies(db: Session = Depends(get_db)):
    """All companies with their latest data, latest analysis, quote and sync state."""
    companies = db.query(Company).options(joinedload(Company.tags)).all()
    thresholds = Thresholds.for_display(db)

    # Per company: newest sync, newest completed sync, and the two newest analyses
    newest: dict = {}
    newest_completed: dict = {}
    analyses: dict = {}
    light = load_only(
        Sync.id, Sync.company_id, Sync.synced_at, Sync.status, Sync.error,
        Sync.stock_price, Sync.price_change, Sync.ai_sentiment, Sync.ai_summary, Sync.ai_changes,
    )
    for s in db.query(Sync).options(light).order_by(Sync.synced_at.desc()):
        newest.setdefault(s.company_id, s)
        if s.status == SyncStatus.completed:
            newest_completed.setdefault(s.company_id, s)
            if s.ai_summary and len(analyses.setdefault(s.company_id, [])) < 2:
                analyses[s.company_id].append(s)

    result = []
    for company in companies:
        latest = newest_completed.get(company.id)
        last = newest.get(company.id)
        found = analyses.get(company.id, [])
        analysis = found[0] if found else None
        result.append({
            **{col.name: getattr(company, col.name) for col in Company.__table__.columns},
            "tags": company.tags,
            "latest_sync": latest,
            "latest_analysis": analysis and {
                "sync_id": analysis.id,
                "synced_at": analysis.synced_at,
                "ai_sentiment": analysis.ai_sentiment,
                "ai_summary": analysis.ai_summary,
                "ai_changes": analysis.ai_changes,
                "previous_sentiment": found[1].ai_sentiment if len(found) > 1 else None,
            },
            "is_stale": thresholds.is_stale(company, latest.synced_at if latest else None),
            "is_syncing": last is not None and last.status == SyncStatus.syncing,
            # Set when the most recent sync failed (the data shown is then from an older sync)
            "sync_error": (last.error or "Sync failed") if last is not None and last.status == SyncStatus.failed else None,
            "has_alert": company.alert_above is not None or company.alert_below is not None,
        })
    return result


@router.post("", response_model=CompanyResponse, status_code=201)
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Create a new company"""
    db_company = Company(**company.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: str, db: Session = Depends(get_db)):
    """Get company detail"""
    company = (
        db.query(Company)
        .options(joinedload(Company.tags))
        .filter(Company.id == company_id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: str, company_update: CompanyUpdate, db: Session = Depends(get_db)
):
    """Update a company"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = company_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_company, key, value)

    db.commit()
    db.refresh(db_company)
    return db_company


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: str, db: Session = Depends(get_db)):
    """Delete a company and all associated syncs"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(db_company)
    db.commit()
    return None


@router.post("/{company_id}/tags", response_model=CompanyResponse)
def assign_tags(
    company_id: str, tags_request: AssignTagsRequest, db: Session = Depends(get_db)
):
    """Assign tags to a company"""
    db_company = (
        db.query(Company)
        .options(joinedload(Company.tags))
        .filter(Company.id == company_id)
        .first()
    )
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Remove existing tag associations
    db.query(CompanyTag).filter(CompanyTag.company_id == company_id).delete()

    # Add new tag associations
    for tag_id in tags_request.tag_ids:
        company_tag = CompanyTag(company_id=company_id, tag_id=tag_id)
        db.add(company_tag)

    db.commit()
    db.refresh(db_company)
    return db_company


@router.delete("/{company_id}/tags/{tag_id}", status_code=204)
def remove_tag(company_id: str, tag_id: str, db: Session = Depends(get_db)):
    """Remove a tag from a company"""
    db.query(CompanyTag).filter(
        CompanyTag.company_id == company_id, CompanyTag.tag_id == tag_id
    ).delete()
    db.commit()
    return None


# Peer details are fetched on demand (two Finnhub calls each) and cached for a day
_peer_cache: dict = {}
_PEER_CACHE_SECONDS = 24 * 3600


@router.get("/{company_id}/peers")
def get_peers(company_id: str, db: Session = Depends(get_db)):
    """Comparable companies from the latest sync, with name, price and whether they're tracked."""
    import time

    from ..config import settings as app_settings
    from ..services.stock_service import StockService

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    latest = (
        db.query(Sync)
        .options(load_only(Sync.peers))
        .filter(Sync.company_id == company_id, Sync.status == SyncStatus.completed, Sync.peers.isnot(None))
        .order_by(Sync.synced_at.desc())
        .first()
    )
    tickers = (latest.peers if latest else None) or []
    tracked = {c.ticker.upper(): c.id for c in db.query(Company).filter(Company.ticker.isnot(None))}
    service = StockService(app_settings.finnhub_api_key)

    peers = []
    for ticker in tickers:
        cached = _peer_cache.get(ticker)
        if not cached or time.time() - cached[0] > _PEER_CACHE_SECONDS:
            profile = service.get_profile(ticker) or {}
            quote = service.get_quote(ticker) or {}
            cached = (time.time(), {**profile, **quote})
            _peer_cache[ticker] = cached
        info = cached[1]
        peers.append({
            "ticker": ticker,
            "name": info.get("name"),
            "industry": info.get("industry"),
            "price": info.get("price"),
            "change": info.get("change"),
            "tracked_company_id": tracked.get(ticker.upper()),
        })
    return peers
