from datetime import datetime, timedelta, timezone

from app.models import Filing, NewsStory, InboxReview
from app.services.inbox import change_inbox
from tests import factories as f

NOW = datetime(2026, 10, 15, 16, tzinfo=timezone.utc)


def story(db, company, **kw):
    row = NewsStory(company_id=company.id, title="New contract", summary="A material contract.",
                    material=kw.pop("material", True), first_seen_at=NOW, last_seen_at=NOW, **kw)
    db.add(row)
    db.commit()
    return row


def test_briefing_prioritizes_holdings_and_ignores_noise_and_routine_filings(db):
    watch = f.company(db, "Watch", "WATCH")
    owned = f.company(db, "Owned", "OWN", shares_owned=5)
    story(db, watch)
    story(db, owned)
    story(db, owned, material=False)
    db.add(Filing(company_id=owned.id, accession="routine", form="8-K", filed_on="2026-10-15",
                  url="https://sec.gov/test", routine=True, created_at=NOW))
    db.add(Filing(company_id=owned.id, accession="risk", form="10-K", filed_on="2026-10-15",
                  url="https://sec.gov/risk", new_risks=["Customer concentration"], created_at=NOW))
    db.commit()
    items = change_inbox(db, NOW)
    assert len(items) == 3
    assert items[0]["kind"] == "risk" and items[0]["detail"] == "Customer concentration"
    assert items[1]["company_id"] == owned.id and items[2]["company_id"] == watch.id


def test_review_snooze_expiry_and_story_updates(db):
    c = f.company(db)
    s = story(db, c)
    [item] = change_inbox(db, NOW)
    state = InboxReview(key=item["key"], company_id=c.id, snoozed_until=NOW + timedelta(days=1))
    db.add(state)
    db.commit()
    assert change_inbox(db, NOW)[0]["state"] == "snoozed"
    assert change_inbox(db, NOW + timedelta(days=1))[0]["state"] == "active"
    state.reviewed_at = NOW
    state.snoozed_until = None
    db.commit()
    assert change_inbox(db, NOW)[0]["state"] == "reviewed"
    s.last_seen_at = NOW + timedelta(hours=1)
    db.commit()
    [updated] = change_inbox(db, NOW + timedelta(hours=1))
    assert updated["state"] == "active" and updated["key"] != item["key"]


def test_changes_compare_to_predecessor_before_window_and_earnings_are_deduplicated(db):
    c = f.company(db)
    f.sync(db, c, synced_at=NOW - timedelta(days=40), summary="Old", sentiment="bullish")
    f.sync(db, c, synced_at=NOW - timedelta(days=2), summary="Changed", sentiment="bearish", ai_changes="Demand weakened.")
    latest = f.sync(db, c, synced_at=NOW, earnings_dates=[{"date": "2026-10-16"}, {"date": "2026-10-16"},
                                                       {"date": "2026-11-30"}, {"date": "invalid"}])
    items = change_inbox(db, NOW)
    assert [e["kind"] for e in items] == ["sentiment", "catalyst"]
    assert "bullish → bearish" in items[0]["title"] and "?analysis=" in items[0]["href"]
    assert items[1]["company_id"] == latest.company_id


def test_review_api_persists_and_can_reopen_without_reading_marking_reviewed(client, db):
    c = f.company(db)
    row = story(db, c)
    # Use real wall time for the API lookback.
    row.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    [item] = client.get("/api/inbox").json()["items"]
    assert item["state"] == "active"
    assert client.post("/api/inbox/review", json={"key": item["key"], "action": "review"}).status_code == 200
    assert client.get("/api/inbox").json()["items"][0]["state"] == "reviewed"
    assert client.post("/api/inbox/review", json={"key": item["key"], "action": "reopen"}).status_code == 200
    assert client.get("/api/inbox").json()["items"][0]["state"] == "active"
    assert client.post("/api/inbox/review", json={"key": "fake", "action": "review"}).status_code == 404
    assert client.post("/api/inbox/review", json={"key": item["key"], "action": "delete"}).status_code == 422
