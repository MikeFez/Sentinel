"""Starting and running syncs: shared by the API, "sync stale" and the auto-refresh loop.

Every sync goes through `queue_sync`, and one worker (`SyncQueue.worker`, started at app startup)
runs them one at a time, highest priority first: syncs a person asked for, then owned companies,
then the rest. The LLM is the bottleneck (one call at a time), so running syncs side by side only
interleaves them and makes each one slower.
"""
import asyncio
import heapq
import itertools
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


def start_sync(db: Session, company_id: str, reason: Optional[str] = None) -> tuple[Sync, bool]:
    """Create a "syncing" record for the company, unless one is already running.

    Returns (sync, created). Callers schedule run_sync(sync.id) only when created is True.
    """
    existing = active_sync(db, company_id)
    if existing:
        return existing, False
    sync = Sync(company_id=company_id, status=SyncStatus.syncing, reason=reason)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    return sync, True


# Priorities: lower runs first
MANUAL, OWNED, OTHER = 0, 1, 2


class SyncQueue:
    """Queued sync ids by priority (FIFO within one). Queueing an id again with a higher priority
    moves it up; the stale heap entry is skipped when it comes out."""

    def __init__(self):
        self._heap: list = []
        self._priority: dict[str, int] = {}
        self._order = itertools.count()
        self._wake: Optional[asyncio.Event] = None
        self.running: Optional[str] = None

    def put(self, sync_id: str, priority: int) -> None:
        if sync_id == self.running or self._priority.get(sync_id, 99) <= priority:
            return
        self._priority[sync_id] = priority
        heapq.heappush(self._heap, (priority, next(self._order), sync_id))
        if self._wake is not None:
            self._wake.set()

    def pop(self) -> Optional[str]:
        while self._heap:
            priority, _, sync_id = heapq.heappop(self._heap)
            if self._priority.get(sync_id) == priority:
                del self._priority[sync_id]
                return sync_id
        return None

    def __len__(self) -> int:
        return len(self._priority)

    async def worker(self) -> None:
        """Run queued syncs forever, one at a time."""
        self._wake = asyncio.Event()
        while True:
            sync_id = self.pop()
            if sync_id is None:
                self._wake.clear()
                await self._wake.wait()
                continue
            self.running = sync_id
            try:
                await run_sync(sync_id)
            except Exception:  # run_sync shouldn't raise; the worker must survive regardless
                logger.exception(f"Sync {sync_id} failed")
            finally:
                self.running = None


sync_queue = SyncQueue()


def priority_for(db: Session, company_id: str, manual: bool) -> int:
    if manual:
        return MANUAL
    owned = db.query(Company.shares_owned).filter(Company.id == company_id).scalar()
    return OWNED if (owned or 0) > 0 else OTHER


def queue_sync(db: Session, company_id: str, reason: Optional[str] = None, manual: bool = False) -> tuple[Sync, bool]:
    """Create a sync (or reuse the one already queued or running) and queue it.

    A manual request for a company that's already queued moves it to the front.
    Returns (sync, created).
    """
    sync, created = start_sync(db, company_id, reason)
    sync_queue.put(sync.id, priority_for(db, company_id, manual))
    return sync, created


async def run_sync(sync_id: str) -> None:
    """Run a sync created by start_sync, in its own DB session. Never raises: callers include the
    queue worker, which must keep going when one sync fails."""
    from ..routers.settings import get_setting

    db = SessionLocal()
    try:
        sync = db.query(Sync).filter(Sync.id == sync_id).first()
        if not sync or sync.status != SyncStatus.syncing:
            return
        # From here on a restart counts as an interruption, not a sync still waiting its turn
        sync.started_at = datetime.now(timezone.utc)
        db.commit()
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
        _mark_crashed(sync_id, exc)
    finally:
        db.close()


def _mark_crashed(sync_id: str, exc: Exception) -> None:
    # A fresh session: the sync's own may be unusable (e.g. after a failed flush)
    db = None
    try:
        db = SessionLocal()
        sync = db.query(Sync).filter(Sync.id == sync_id).first()
        if sync and sync.status == SyncStatus.syncing:
            sync.status = SyncStatus.failed
            sync.error = f"Sync crashed: {exc}"
            db.commit()
    except Exception:
        logger.exception(f"Could not mark sync {sync_id} as failed")
    finally:
        if db is not None:
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
    """Re-queue syncs left in "syncing" by a restart.

    Ones that never started just go back in the queue. Ones that were running are marked failed (so the
    history shows the interruption) and a new sync with the same reason is queued in their place.
    """
    db = SessionLocal()
    try:
        requeued = interrupted = 0
        for sync in db.query(Sync).filter(Sync.status == SyncStatus.syncing).order_by(Sync.synced_at).all():
            manual = (sync.reason or "").startswith(("Manual", "Stale data"))
            if sync.started_at is None:
                sync_queue.put(sync.id, priority_for(db, sync.company_id, manual))
                requeued += 1
                continue
            sync.status, sync.error = SyncStatus.failed, "Interrupted by a server restart"
            db.commit()
            queue_sync(db, sync.company_id, sync.reason, manual)
            interrupted += 1
        db.commit()
        if requeued or interrupted:
            logger.warning(f"Restart: re-queued {requeued} waiting and retrying {interrupted} interrupted sync(s)")
    finally:
        db.close()
