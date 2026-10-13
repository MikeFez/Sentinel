from datetime import datetime, timedelta, timezone

from app.models import Sync
from app.models.sync import SyncStatus
from app.services.sync_runner import start_sync, recover_interrupted_syncs, stale_company_ids, Thresholds
from tests import factories as f


def test_start_sync_reuses_a_running_sync(db):
    c = f.company(db)
    first, created = start_sync(db, c.id)
    second, created_again = start_sync(db, c.id)
    assert created and not created_again
    assert first.id == second.id


def test_restart_requeues_waiting_syncs_and_retries_interrupted_ones(db):
    from app.services import sync_runner

    c, d = f.company(db, "Waiting", "WAIT"), f.company(db, "Running", "RUN")
    waiting = f.sync(db, c, status=SyncStatus.syncing, reason="Scheduled refresh")
    running = f.sync(db, d, status=SyncStatus.syncing, reason="Manual sync", started_at=datetime.now(timezone.utc))
    recover_interrupted_syncs()
    db.expire_all()
    assert db.get(Sync, waiting.id).status == SyncStatus.syncing  # untouched, back in the queue
    assert db.get(Sync, running.id).status == SyncStatus.failed and "restart" in db.get(Sync, running.id).error
    retry = db.query(Sync).filter(Sync.company_id == d.id, Sync.status == SyncStatus.syncing).one()
    assert retry.reason == "Manual sync"
    q = sync_runner.sync_queue
    assert [q.pop(), q.pop(), q.pop()] == [retry.id, waiting.id, None]  # the manual retry goes first


def test_queue_runs_manual_then_owned_then_the_rest_and_bumps_on_request():
    from app.services.sync_runner import SyncQueue, MANUAL, OWNED, OTHER

    q = SyncQueue()
    q.put("other-1", OTHER)
    q.put("owned", OWNED)
    q.put("other-2", OTHER)
    q.put("other-2", MANUAL)  # asked for by hand: moves to the front
    q.put("owned", OTHER)  # a lower priority never demotes
    assert len(q) == 3
    assert [q.pop(), q.pop(), q.pop(), q.pop()] == ["other-2", "owned", "other-1", None]


def test_manual_sync_of_an_owned_company_and_priority(db):
    from app.services.sync_runner import priority_for, MANUAL, OWNED, OTHER

    owned, watched = f.company(db, "Owned", "OWN", shares_owned=10), f.company(db, "Watched", "WAT")
    assert priority_for(db, owned.id, manual=False) == OWNED
    assert priority_for(db, watched.id, manual=False) == OTHER
    assert priority_for(db, watched.id, manual=True) == MANUAL


def test_staleness_rules():
    now = datetime.now(timezone.utc)
    t = Thresholds(public_hours=24, private_hours=7 * 24)

    class C:
        def __init__(self, status, ticker):
            self.status, self.ticker = status, ticker

    public, private = C("public", "X"), C("private", None)
    assert t.is_stale(public, None)
    assert t.is_stale(public, now - timedelta(hours=25))
    assert not t.is_stale(public, now - timedelta(hours=23))
    assert not t.is_stale(private, now - timedelta(days=6))
    assert t.is_stale(private, now - timedelta(days=8))
    # A public company without a ticker has nothing to price, so it follows the private schedule
    assert not t.is_stale(C("public", None), now - timedelta(days=2))
    assert not Thresholds(24, None).is_stale(private, None)


def test_stale_company_ids_skips_running_and_fresh(db):
    stale = f.company(db, "Stale", "OLD")
    f.sync(db, stale, hours_ago=48)
    fresh = f.company(db, "Fresh", "NEW")
    f.sync(db, fresh, hours_ago=1)
    running = f.company(db, "Running", "RUN")
    f.sync(db, running, hours_ago=48)
    f.sync(db, running, status=SyncStatus.syncing)
    never = f.company(db, "Never", "NVR")
    private_old = f.company(db, "Private", None, status="private")
    f.sync(db, private_old, hours_ago=24 * 10)

    ids = set(stale_company_ids(db, Thresholds(24, 7 * 24)))
    assert ids == {stale.id, never.id, private_old.id}
    assert private_old.id not in stale_company_ids(db, Thresholds(24, None))


def test_a_crashing_sync_is_marked_failed_and_never_raises(db, monkeypatch):
    import asyncio
    from app.services import sync_runner

    async def boom(self, *a, **k):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(sync_runner.SyncService, "sync_company", boom)
    c = f.company(db)
    sync, _ = start_sync(db, c.id)
    asyncio.run(sync_runner.run_sync(sync.id))  # must not raise
    db.expire_all()
    assert db.get(Sync, sync.id).status == SyncStatus.failed
    assert "database is locked" in db.get(Sync, sync.id).error


def test_run_sync_survives_even_when_marking_the_failure_fails(db, monkeypatch):
    import asyncio
    from app.services import sync_runner

    async def boom(self, *a, **k):
        raise RuntimeError("first failure")

    def broken_session():
        raise RuntimeError("database is locked")

    monkeypatch.setattr(sync_runner.SyncService, "sync_company", boom)
    c = f.company(db)
    sync, _ = start_sync(db, c.id)
    real = sync_runner.SessionLocal
    calls = []
    def session_factory():
        calls.append(1)
        return real() if len(calls) == 1 else broken_session()
    monkeypatch.setattr(sync_runner, "SessionLocal", session_factory)
    asyncio.run(sync_runner.run_sync(sync.id))  # must not raise
