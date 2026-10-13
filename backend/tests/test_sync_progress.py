from app.models import NewsArticle
from app.models.sync import SyncStatus
from app.services import activity, sync_progress
from tests import factories as f


def test_steps_advance_and_only_forward():
    sync_progress.begin("c1", public=True, debate=True)
    with activity.context(company_id="c1"):
        sync_progress.step("bull case", waiting=True)
        assert sync_progress.get("c1") == {
            "steps": ["Fetching prices, ratings and news", "Grouping news into stories",
                      "Writing the bull case", "Writing the bear case", "Writing the analysis"],
            "current": 2, "waiting": True,
        }
        sync_progress.step("story grouping")  # a late or retried call never moves it back
        sync_progress.step("filing summary")  # not a sync step: ignored
        assert sync_progress.get("c1")["current"] == 2
    sync_progress.end("c1")
    assert sync_progress.get("c1") is None


def test_steps_outside_a_sync_are_ignored():
    sync_progress.step("analysis")  # no company context, nothing running: must not raise


def test_list_reports_progress_while_syncing_and_latest_news(client, db):
    c = f.company(db)
    f.sync(db, c, status=SyncStatus.syncing)
    db.add(NewsArticle(company_id=c.id, url="https://n/1", title="One"))
    db.commit()
    sync_progress.begin(c.id, public=True, debate=False)
    try:
        [row] = client.get("/api/companies").json()
    finally:
        sync_progress.end(c.id)
    assert row["sync_progress"]["steps"][-1] == "Writing the analysis"
    assert row["latest_news_at"].endswith("Z")
