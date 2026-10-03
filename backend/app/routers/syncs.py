from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Sync, Company
from ..models.sync import SyncStatus
from ..schemas.sync import SyncResponse
from ..services.sync_runner import start_sync, run_sync, stale_company_ids, Thresholds

router = APIRouter(prefix="/api", tags=["syncs"])


@router.post("/companies/{company_id}/sync", response_model=SyncResponse, status_code=202)
async def trigger_sync(company_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start a sync for a company and return its "syncing" record (or the one already running)."""
    if not db.query(Company.id).filter(Company.id == company_id).first():
        raise HTTPException(status_code=404, detail="Company not found")

    sync, created = start_sync(db, company_id)
    if created:
        background_tasks.add_task(run_sync, sync.id)
    return sync


@router.get("/companies/{company_id}/syncs", response_model=List[SyncResponse])
def get_company_syncs(company_id: str, db: Session = Depends(get_db)):
    """Get sync history for a company, newest first"""
    if not db.query(Company.id).filter(Company.id == company_id).first():
        raise HTTPException(status_code=404, detail="Company not found")

    return (
        db.query(Sync)
        .filter(Sync.company_id == company_id)
        .order_by(Sync.synced_at.desc())
        .all()
    )


@router.get("/syncs/{sync_id}", response_model=SyncResponse)
def get_sync(sync_id: str, db: Session = Depends(get_db)):
    """Get full sync detail including news articles and AI summary"""
    sync = db.query(Sync).filter(Sync.id == sync_id).first()
    if not sync:
        raise HTTPException(status_code=404, detail="Sync not found")
    return sync


@router.get("/syncs/queue/active")
def get_sync_queue(db: Session = Depends(get_db)):
    """Companies currently being synced"""
    rows = (
        db.query(Sync.company_id, Company.name)
        .join(Company, Sync.company_id == Company.id)
        .filter(Sync.status == SyncStatus.syncing)
        .all()
    )
    return [{"company_id": r.company_id, "company_name": r.name} for r in rows]


@router.post("/syncs/sync-stale")
async def sync_stale_companies(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Queue a sync for every company whose data is stale (see Thresholds.for_display)."""
    queued = 0
    for company_id in stale_company_ids(db, Thresholds.for_display(db)):
        sync, created = start_sync(db, company_id)
        if created:
            background_tasks.add_task(run_sync, sync.id)
            queued += 1

    if not queued:
        return {"queued": 0, "message": "Everything is up to date"}
    return {"queued": queued, "message": f"Syncing {queued} {'company' if queued == 1 else 'companies'}"}
