"""Starting and running syncs: shared by the API, "sync stale" and the auto-refresh loop."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..config import settings as app_settings
from ..database import SessionLocal
from ..models import Company, Sync
from ..models.sync import SyncStatus
from .sync_service import SyncService

logger = logging.getLogger(__name__)


def active_sync(db: Session, company_id: str) -> Optional[Sync]:
    return (
        db.query(Sync)
        .filter(Sync.company_id == company_id, Sync.status == SyncStatus.syncing)
        .order_by(Sync.synced_at.desc())
        .first()
    )


def start_sync(db: Session, company_id: str) -> tuple[Sync, bool]:
    """Create a "syncing" record for the company, unless one is already running.

    Returns (sync, created). Callers schedule run_sync(sync.id) only when created is True.
    """
    existing = active_sync(db, company_id)
    if existing:
        return existing, False
    sync = Sync(company_id=company_id, status=SyncStatus.syncing)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    return sync, True


async def run_sync(sync_id: str) -> None:
    """Run a sync created by start_sync, in its own DB session."""
    from ..routers.settings import get_setting

    db = SessionLocal()
    try:
        sync = db.query(Sync).filter(Sync.id == sync_id).first()
        if not sync:
            return
        try:
            news_count = int(get_setting(db, "news_count"))
        except ValueError:
            news_count = app_settings.news_article_count
        service = SyncService(
            db,
            get_setting(db, "llm_base_url"),
            get_setting(db, "llm_model"),
            app_settings.finnhub_api_key,
        )
        await service.sync_company(sync.company_id, news_count=news_count, existing_sync=sync)
    except Exception as exc:  # never leave a sync stuck in "syncing"
        logger.exception(f"Sync {sync_id} crashed")
        db.rollback()
        sync = db.query(Sync).filter(Sync.id == sync_id).first()
        if sync and sync.status == SyncStatus.syncing:
            sync.status = SyncStatus.failed
            sync.error = f"Sync crashed: {exc}"
            db.commit()
    finally:
        db.close()


def stale_company_ids(db: Session, hours: float) -> list[str]:
    """Public companies with a ticker, no running sync, and no completed sync within `hours`.

    Only these are refreshed automatically: private/pre-IPO companies only have news to fetch.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    busy = {
        cid
        for (cid,) in db.query(Sync.company_id)
        .filter(
            (Sync.status == SyncStatus.syncing)
            | ((Sync.status == SyncStatus.completed) & (Sync.synced_at >= cutoff))
        )
        .distinct()
    }
    return [
        cid
        for (cid,) in db.query(Company.id).filter(Company.status == "public", Company.ticker.isnot(None))
        if cid not in busy
    ]


def recover_interrupted_syncs() -> None:
    """Syncs still marked "syncing" at startup were cut off by a restart; mark them failed."""
    db = SessionLocal()
    try:
        n = (
            db.query(Sync)
            .filter(Sync.status == SyncStatus.syncing)
            .update({Sync.status: SyncStatus.failed, Sync.error: "Interrupted by a server restart"})
        )
        db.commit()
        if n:
            logger.warning(f"Marked {n} interrupted sync(s) as failed")
    finally:
        db.close()
