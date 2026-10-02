from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
from ..database import get_db, SessionLocal
from ..models import Sync, Company, Setting
from ..models.sync import SyncStatus
from ..schemas.sync import SyncResponse
from ..services.sync_service import SyncService
from ..config import settings

router = APIRouter(prefix="/api", tags=["syncs"])


def get_setting(db: Session, key: str, default: str) -> str:
    """Get setting from database or return default"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else default


async def _run_sync_background(
    sync_id: str,
    company_id: str,
    ollama_url: str,
    ollama_model: str,
    finnhub_api_key: str,
    news_count: int,
) -> None:
    """Run sync in background with its own DB session."""
    db = SessionLocal()
    try:
        sync = db.query(Sync).filter(Sync.id == sync_id).first()
        if sync:
            service = SyncService(db, ollama_url, ollama_model, finnhub_api_key)
            await service.sync_company(company_id, news_count=news_count, existing_sync=sync)
    finally:
        db.close()


@router.post("/companies/{company_id}/sync", response_model=SyncResponse, status_code=202)
async def trigger_sync(
    company_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger a manual sync for a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get settings from database
    ollama_url = get_setting(db, "ollama_url", settings.ollama_url)
    ollama_model = get_setting(db, "ollama_model", settings.ollama_model)
    news_count = int(get_setting(db, "news_count", str(settings.news_article_count)))

    # Create sync record immediately and return it; do the work in background
    sync = Sync(company_id=company_id, status=SyncStatus.syncing)
    db.add(sync)
    db.commit()
    db.refresh(sync)

    background_tasks.add_task(
        _run_sync_background,
        sync.id,
        company_id,
        ollama_url,
        ollama_model,
        settings.finnhub_api_key,
        news_count,
    )

    return sync


@router.get("/companies/{company_id}/syncs", response_model=List[SyncResponse])
def get_company_syncs(company_id: str, db: Session = Depends(get_db)):
    """Get sync history for a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    syncs = (
        db.query(Sync)
        .filter(Sync.company_id == company_id)
        .order_by(Sync.synced_at.desc())
        .all()
    )

    return syncs


@router.get("/syncs/{sync_id}", response_model=SyncResponse)
def get_sync(sync_id: str, db: Session = Depends(get_db)):
    """Get full sync detail including news articles and AI summary"""
    sync = db.query(Sync).filter(Sync.id == sync_id).first()
    if not sync:
        raise HTTPException(status_code=404, detail="Sync not found")

    return sync


@router.get("/syncs/queue/active")
def get_sync_queue(db: Session = Depends(get_db)):
    """Return list of company IDs currently being synced"""
    rows = (
        db.query(Sync.company_id, Company.name)
        .join(Company, Sync.company_id == Company.id)
        .filter(Sync.status == SyncStatus.syncing)
        .all()
    )
    return [{"company_id": r.company_id, "company_name": r.name} for r in rows]


@router.post("/syncs/sync-stale")
async def sync_stale_companies(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Queue a background sync for every company that hasn't been synced recently."""
    from datetime import timedelta, timezone
    from .settings import get_setting as _get_setting

    try:
        staleness_hours = float(_get_setting(db, "staleness_hours") or "24")
    except ValueError:
        staleness_hours = 24.0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=staleness_hours)

    syncing_ids = {
        row[0]
        for row in db.query(Sync.company_id)
        .filter(Sync.status == SyncStatus.syncing)
        .distinct()
        .all()
    }

    fresh_ids = {
        row[0]
        for row in db.query(Sync.company_id)
        .filter(Sync.status == SyncStatus.completed, Sync.synced_at >= cutoff)
        .distinct()
        .all()
    }

    excluded = syncing_ids | fresh_ids
    stale_companies = (
        db.query(Company)
        .filter(
            Company.id.notin_(excluded),
            Company.status == "public",
            Company.ticker.isnot(None),
        )
        .all()
    )

    if not stale_companies:
        return {"queued": 0, "message": "All companies are up to date"}

    ollama_url = get_setting(db, "ollama_url", settings.ollama_url)
    ollama_model = get_setting(db, "ollama_model", settings.ollama_model)
    news_count = int(get_setting(db, "news_count", str(settings.news_article_count)))

    queued = 0
    for company in stale_companies:
        sync = Sync(company_id=company.id, status=SyncStatus.syncing)
        db.add(sync)
        db.commit()
        db.refresh(sync)
        background_tasks.add_task(
            _run_sync_background,
            sync.id,
            company.id,
            ollama_url,
            ollama_model,
            settings.finnhub_api_key,
            news_count,
        )
        queued += 1

    return {"queued": queued, "message": f"Queued {queued} company sync(s)"}
