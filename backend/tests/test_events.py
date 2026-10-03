from datetime import datetime, timezone

from app.models import Company
from app.models.sync import SyncStatus
from app.services.events import move_reason, earnings_reason, due_event_syncs
from tests import factories as f


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


MON_NOON = utc(2026, 10, 5, 16, 0)  # 12:00 New York, market open since 13:30 UTC


def test_big_move_triggers_once_per_session():
    c = Company(quote_change=-6.2, quote_at=utc(2026, 10, 5, 15, 55))
    assert move_reason(c, utc(2026, 10, 4, 22, 0), 5, MON_NOON) == "Price moved −6.2% today"
    assert move_reason(c, utc(2026, 10, 5, 14, 0), 5, MON_NOON) is None  # already synced since the open
    assert move_reason(c, None, 0, MON_NOON) is None  # turned off
    assert move_reason(Company(quote_change=3.0, quote_at=c.quote_at), None, 5, MON_NOON) is None
    # A big move from Friday's session doesn't trigger on Monday
    assert move_reason(Company(quote_change=9.0, quote_at=utc(2026, 10, 2, 20, 5)), None, 5, MON_NOON) is None


def test_earnings_sync_after_results_are_out():
    dates = [{"date": "2026-10-05"}, {"date": "2026-11-20"}]
    before = utc(2026, 10, 5, 20, 0)  # 16:00 ET on the day
    after = utc(2026, 10, 5, 20, 45)
    assert earnings_reason(dates, utc(2026, 10, 5, 13, 0), before) is None
    assert earnings_reason(dates, utc(2026, 10, 5, 13, 0), after) == "Earnings reported 2026-10-05"
    assert earnings_reason(dates, utc(2026, 10, 5, 21, 0), utc(2026, 10, 6, 14, 0)) is None  # synced since
    assert earnings_reason(dates, utc(2026, 9, 1), utc(2026, 10, 12, 14, 0)) is None  # too long ago
    assert earnings_reason([{"date": "bad"}], None, after) is None


def test_due_event_syncs(db):
    mover = f.company(db, "Mover", "MOV", quote_change=7.5, quote_at=utc(2026, 10, 5, 15, 50))
    f.sync(db, mover, hours_ago=0)
    # The factory's "hours_ago" is relative to now; set an explicit old time instead
    from app.models import Sync
    db.query(Sync).filter(Sync.company_id == mover.id).update({Sync.synced_at: utc(2026, 10, 4, 12, 0)})
    reporter = f.company(db, "Reporter", "REP")
    s = f.sync(db, reporter, earnings_dates=[{"date": "2026-10-05"}])
    db.query(Sync).filter(Sync.id == s.id).update({Sync.synced_at: utc(2026, 10, 5, 13, 0)})
    busy = f.company(db, "Busy", "BSY", quote_change=9.0, quote_at=utc(2026, 10, 5, 15, 50))
    f.sync(db, busy, status=SyncStatus.syncing)
    db.commit()

    due = dict(due_event_syncs(db, 5, True, now=utc(2026, 10, 5, 21, 0)))
    assert due == {mover.id: "Price moved +7.5% today", reporter.id: "Earnings reported 2026-10-05"}
    assert due_event_syncs(db, 0, False, now=utc(2026, 10, 5, 21, 0)) == []
