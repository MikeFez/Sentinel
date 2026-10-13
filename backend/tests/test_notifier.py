import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.config import settings as app_settings
from app.models import DailyPrice, Filing, NewsStory, Notification
from app.models.sync import SyncStatus
from app.services import notifier
from tests import factories as f


@pytest.fixture
def sent(monkeypatch):
    """Capture notifications instead of sending them."""
    out = []
    monkeypatch.setattr(app_settings, "notify_urls", "ntfy://secret-token@ntfy.example/sentinel")
    monkeypatch.setattr(notifier, "_send", lambda title, body: out.append((title, body)))
    return out


def test_price_alert_fires_on_crossing_only(db, sent):
    c = f.company(db, "Rocket Lab", "RKLB", alert_above=70.0, quote_price=71.0, quote_change=2.0)
    now = datetime(2026, 10, 13, 15, tzinfo=timezone.utc)
    notifier.after_quote(db, c, 69.0, 0, now)  # crossed
    notifier.after_quote(db, c, 71.0, 0, now)  # still above: nothing new
    c.quote_price = 69.0
    notifier.after_quote(db, c, 71.0, 0, now)  # back below: nothing
    c.quote_price = 70.5
    notifier.after_quote(db, c, 69.0, 0, now)  # crossed again the same day: once per level per day
    assert [t for t, _ in sent] == ["RKLB is above $70.00"]


def test_big_move_once_a_day_and_switches_are_respected(db, sent, client):
    c = f.company(db, quote_price=50.0, quote_change=-8.4)
    now = datetime(2026, 10, 13, 15, tzinfo=timezone.utc)
    notifier.after_quote(db, c, 54.0, 5, now)
    notifier.after_quote(db, c, 54.0, 5, now)
    assert [t for t, _ in sent] == ["ACME −8.4% today"]
    client.put("/api/settings", json={"notify_big_moves": "false"})
    notifier.after_quote(db, c, 54.0, 5, now + timedelta(days=1))
    assert len(sent) == 1


def test_after_sync_flip_earnings_material_news_and_problems(db, sent):
    c = f.company(db, "Rocket Lab", "RKLB")
    f.sync(db, c, hours_ago=48, sentiment="bullish", summary="Before.")
    started = datetime.now(timezone.utc) - timedelta(minutes=5)
    s = f.sync(db, c, hours_ago=0, sentiment="bearish", summary="After.", ai_changes="Neutron slipped.",
               reason="Earnings reported 2026-10-12", started_at=started,
               earnings_history=[{"actual": 0.05, "estimate": 0.04, "surprisePercent": 25.0}])
    db.add(NewsStory(company_id=c.id, title="Neutron delayed", summary="First launch moves to 2027.", material=True,
                     themes=["Neutron"], last_seen_at=datetime.now(timezone.utc)))
    db.add(NewsStory(company_id=c.id, title="Stocks to watch", material=False, last_seen_at=datetime.now(timezone.utc)))
    db.commit()
    notifier.after_sync(s.id)
    notifier.after_sync(s.id)  # reported twice: still sent once
    titles = [t for t, _ in sent]
    assert titles == ["RKLB: bullish → bearish", "RKLB reported results", "RKLB: Neutron delayed"]
    assert "EPS 0.050 vs. 0.040 expected (beat 25.0%)" in sent[1][1]

    failed = f.sync(db, c, status=SyncStatus.failed, error="No price data from Finnhub")
    notifier.after_sync(failed.id)
    notifier.after_sync(f.sync(db, c, status=SyncStatus.failed, error="again").id)  # problems: once a day
    assert titles + ["Syncs are failing (Rocket Lab)"] == [t for t, _ in sent]


def test_routine_filings_are_not_sent(db, sent):
    c = f.company(db)
    routine = Filing(company_id=c.id, accession="a1", form="8-K", filed_on="2026-10-01", url="u", summary="Vote results.", routine=True)
    news = Filing(company_id=c.id, accession="a2", form="8-K", filed_on="2026-10-02", url="u", summary="The CFO resigned.")
    db.add_all([routine, news])
    db.commit()
    notifier.after_filing(routine.id)
    notifier.after_filing(news.id)
    assert sent == [("ACME filed a 8-K", "The CFO resigned.")]


def test_weekly_digest_once_on_its_day(db, sent):
    c = f.company(db, "Rocket Lab", "RKLB", shares_owned=10, quote_price=110.0)
    db.add(DailyPrice(company_id=c.id, day="2026-10-05", price=100.0, at=datetime(2026, 10, 5, 20, tzinfo=timezone.utc)))
    db.commit()
    monday_9am = datetime(2026, 10, 12, 13, tzinfo=timezone.utc)  # 9 AM in New York
    notifier.maybe_send_digest(monday_9am - timedelta(hours=2))  # before 8 AM: not yet
    notifier.maybe_send_digest(monday_9am)
    notifier.maybe_send_digest(monday_9am + timedelta(hours=3))  # already sent this week
    notifier.maybe_send_digest(monday_9am + timedelta(days=1))  # not the digest day
    [(title, body)] = sent
    assert title == "Sentinel weekly: portfolio +10.0%"
    assert "Portfolio: $1,100.00 (+10.0% this week)" in body and "RKLB +10.0%" in body


def test_digest_ignores_prices_from_before_a_data_gap_and_compares_sentiment_to_last_week(db):
    now = datetime(2026, 10, 12, 13, tzinfo=timezone.utc)
    c = f.company(db, "Rocket Lab", "RKLB", shares_owned=10, quote_price=65.71)
    db.add(DailyPrice(company_id=c.id, day="2026-06-04", price=119.95, at=datetime(2026, 6, 4, 20, tzinfo=timezone.utc)))
    f.sync(db, c, sentiment="bullish", synced_at=datetime(2026, 6, 4, 20, tzinfo=timezone.utc))
    f.sync(db, c, sentiment="mixed", synced_at=now - timedelta(hours=3))
    f.sync(db, c, sentiment="mixed", synced_at=now - timedelta(hours=1))
    db.commit()
    title, body = notifier.build_digest(db, now)
    assert title == "Sentinel weekly"  # no price from a week ago: no portfolio change, not "−45%"
    assert "Moves" not in body and "RKLB bullish → mixed" in body


def test_api_shows_services_but_never_tokens(client, monkeypatch):
    monkeypatch.setattr(app_settings, "notify_urls", "ntfy://secret-token@ntfy.example/x, discord://123/abc")
    r = client.get("/api/notifications").json()
    assert r["services"] == ["discord", "ntfy"] and "secret" not in json.dumps(r)
    monkeypatch.setattr(app_settings, "notify_urls", "")
    assert client.post("/api/notifications/test").json() == {"ok": False, "error": "No destinations: set the NOTIFY_URLS environment variable"}
    assert client.get("/api/notifications").json()["recent"] == []  # nothing was attempted, so nothing recorded


def test_real_apprise_delivery_to_a_json_endpoint(db, client, monkeypatch):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    monkeypatch.setattr(app_settings, "notify_urls", f"json://127.0.0.1:{server.server_port}/hook")
    assert client.post("/api/notifications/test").json() == {"ok": True, "error": None}
    assert received[0]["title"] == "Sentinel test notification"
    assert db.query(Notification).one().status == "sent"
    server.server_close()
