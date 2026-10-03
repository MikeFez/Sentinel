from app.models.sync import SyncStatus
from app.routers import syncs as syncs_router
from tests import factories as f


def test_list_shows_latest_completed_sync_and_failure(client, db):
    c = f.company(db)
    good = f.sync(db, c, hours_ago=2, sentiment="bullish", summary="Fine.", stock_price=5.0)
    f.sync(db, c, hours_ago=1, status=SyncStatus.failed, error="Finnhub down")
    [row] = client.get("/api/companies").json()
    assert row["latest_sync"]["id"] == good.id
    assert row["sync_error"] == "Finnhub down"
    assert row["is_syncing"] is False
    assert row["latest_sync"]["synced_at"].endswith("Z")  # UTC, so browsers don't read it as local time


def test_latest_analysis_survives_a_sync_without_one(client, db):
    c = f.company(db)
    f.sync(db, c, hours_ago=48, sentiment="bearish", summary="Older.")
    f.sync(db, c, hours_ago=24, sentiment="bullish", summary="Analysed.")
    f.sync(db, c, hours_ago=1, error="AI analysis unavailable: down", stock_price=7.0)
    [row] = client.get("/api/companies").json()
    assert row["latest_sync"]["ai_sentiment"] is None
    assert row["latest_analysis"]["ai_summary"] == "Analysed."
    assert row["latest_analysis"]["ai_sentiment"] == "bullish"
    assert row["latest_analysis"]["previous_sentiment"] == "bearish"


def test_edit_can_clear_fields_and_tags(client):
    tag = client.post("/api/tags", json={"name": "Owned"}).json()
    c = client.post("/api/companies", json={"name": "Acme", "ticker": "ACME", "alert_above": 50, "shares_owned": 10}).json()
    client.post(f"/api/companies/{c['id']}/tags", json={"tag_ids": [tag["id"]]})
    client.put(f"/api/companies/{c['id']}", json={"alert_above": None, "shares_owned": None})
    client.post(f"/api/companies/{c['id']}/tags", json={"tag_ids": []})
    after = client.get(f"/api/companies/{c['id']}").json()
    assert after["alert_above"] is None and after["shares_owned"] is None and after["tags"] == []


def test_triggering_twice_returns_the_running_sync(client, db, monkeypatch):
    started = []

    async def fake_run(sync_id):
        started.append(sync_id)

    monkeypatch.setattr(syncs_router, "run_sync", fake_run)
    c = f.company(db)
    first = client.post(f"/api/companies/{c.id}/sync")
    second = client.post(f"/api/companies/{c.id}/sync")
    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert len(started) == 1


def test_sync_stale_queues_only_stale_companies(client, db, monkeypatch):
    async def fake_run(sync_id):
        pass

    monkeypatch.setattr(syncs_router, "run_sync", fake_run)
    old = f.company(db, "Old", "OLD")
    f.sync(db, old, hours_ago=48)
    fresh = f.company(db, "Fresh", "NEW")
    f.sync(db, fresh, hours_ago=1)
    assert client.post("/api/syncs/sync-stale").json()["queued"] == 1
    assert client.post("/api/syncs/sync-stale").json()["queued"] == 0  # already running
