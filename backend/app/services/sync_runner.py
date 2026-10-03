"""Starting and running syncs: shared by the API, "sync stale" and the auto-refresh loop."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
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


class Thresholds:
    """How old a company's newest completed sync may be before it needs a refresh.

    Public companies use an hour threshold. Private / pre-IPO / acquired companies only have news,
    so they use a slower one (private_refresh_days); None means they're never refreshed automatically.
    """

    def __init__(self, public_hours: float, private_hours: Optional[float]):
        self.public_hours = public_hours
        self.private_hours = private_hours

    @classmethod
    def for_display(cls, db: Session) -> "Thresholds":
        """What counts as stale in the UI and for "Sync stale"."""
        from ..routers.settings import get_float

        days = get_float(db, "private_refresh_days")
        return cls(get_float(db, "staleness_hours"), days * 24 if days > 0 else None)

    @classmethod
    def for_auto_refresh(cls, db: Session) -> "Thresholds":
        from ..routers.settings import get_float

        days = get_float(db, "private_refresh_days")
        return cls(get_float(db, "auto_refresh_hours"), days * 24 if days > 0 else None)

    def is_stale(self, company: Company, last_completed: Optional[datetime], now: Optional[datetime] = None) -> bool:
        public = company.status == "public" and bool(company.ticker)
        hours = self.public_hours if public else self.private_hours
        if hours is None:
            return False
        if last_completed is None:
            return True
        if last_completed.tzinfo is None:
            last_completed = last_completed.replace(tzinfo=timezone.utc)
        return last_completed < (now or datetime.now(timezone.utc)) - timedelta(hours=hours)


def last_completed_by_company(db: Session) -> dict:
    return dict(
        db.query(Sync.company_id, func.max(Sync.synced_at))
        .filter(Sync.status == SyncStatus.completed)
        .group_by(Sync.company_id)
        .all()
    )


def stale_company_ids(db: Session, thresholds: Thresholds) -> list[str]:
    """Companies that are stale under `thresholds` and have no sync running."""
    running = {cid for (cid,) in db.query(Sync.company_id).filter(Sync.status == SyncStatus.syncing).distinct()}
    last = last_completed_by_company(db)
    return [
        c.id
        for c in db.query(Company)
        if c.id not in running and thresholds.is_stale(c, _as_datetime(last.get(c.id)))
    ]


def _as_datetime(value) -> Optional[datetime]:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


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
