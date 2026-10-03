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


def test_interrupted_syncs_are_marked_failed(db):
    c = f.company(db)
    s = f.sync(db, c, status=SyncStatus.syncing)
    recover_interrupted_syncs()
    db.refresh(s)
    assert s.status == SyncStatus.failed
    assert "restart" in s.error


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
