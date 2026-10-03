import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.models import ActivityEvent
from app.services import activity
from app.services.llm_service import LLMService
from app.services.maintenance import prune_history
from app.services.stock_service import StockService


def events(db):
    db.expire_all()
    return db.query(ActivityEvent).order_by(ActivityEvent.at).all()


def test_track_records_success_and_errors(db):
    with activity.track("job", "quote refresh") as t:
        t.note("2 updated")
    with pytest.raises(ValueError):
        with activity.track("job", "prune"):
            raise ValueError("disk full")
    ok, bad = events(db)
    assert (ok.kind, ok.name, ok.status, ok.detail) == ("job", "quote refresh", "ok", "2 updated")
    assert bad.status == "error" and "disk full" in bad.detail
    assert activity.running() == []


def test_company_context_reaches_worker_threads(db):
    def work():
        with activity.track("finnhub", "quote"):
            pass

    async def main():
        with activity.context(company_id="c1"):
            await asyncio.to_thread(work)

    asyncio.run(main())
    assert events(db)[0].company_id == "c1"


def test_llm_calls_record_purpose_tokens_and_failures(db, monkeypatch):
    replies = [
        httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}], "usage": {"prompt_tokens": 12, "completion_tokens": 34}}),
        httpx.Response(500, text="boom"),
    ]

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers=None, json=None):
            r = replies.pop(0)
            r.request = httpx.Request("POST", url)
            return r

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    llm = LLMService("http://llm/v1", "qwen", api_key="", reasoning_effort="")
    assert asyncio.run(llm.generate("x", purpose="story grouping")) == "hi"
    assert asyncio.run(llm.generate("x", purpose="analysis")) is None
    ok, bad = events(db)
    assert (ok.kind, ok.name, ok.prompt_tokens, ok.completion_tokens, ok.detail) == ("llm", "story grouping", 12, 34, "qwen")
    assert (bad.name, bad.status) == ("analysis", "error") and "HTTP 500" in bad.detail


def test_finnhub_requests_are_recorded_by_endpoint(db, monkeypatch):
    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def get(self, url, params=None, timeout=None):
            return httpx.Response(200, json={"c": 1}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "Client", FakeClient)
    StockService("key")._request("https://finnhub.io/api/v1/stock/profile2", {})
    [e] = events(db)
    assert (e.kind, e.name, e.status) == ("finnhub", "stock/profile2", "ok")


def test_summary_events_and_metrics_endpoints(client, db):
    now = datetime.now(timezone.utc)
    db.add_all([
        ActivityEvent(at=now - timedelta(hours=1), kind="llm", name="analysis", status="ok", duration_ms=60000, prompt_tokens=100, completion_tokens=50),
        ActivityEvent(at=now - timedelta(hours=2), kind="llm", name="analysis", status="error", duration_ms=1000, detail="timed out"),
        ActivityEvent(at=now - timedelta(hours=30), kind="finnhub", name="quote", status="ok", duration_ms=100),
    ])
    db.commit()
    s = client.get("/api/activity/summary?hours=24").json()
    assert s["totals"]["llm"] == {"count": 2, "errors": 1, "busy_seconds": 61.0}
    assert s["totals"]["finnhub"]["count"] == 0  # older than 24h
    assert s["llm_tokens"] == {"prompt": 100, "completion": 50}
    [op] = s["operations"]
    assert (op["name"], op["count"], op["errors"], op["last_error"]) == ("analysis", 2, 1, "timed out")
    assert sum(s["series"]["llm"]) == 2 and len(s["series"]["llm"]) == 24
    assert any(a["route"] == "/api/activity/summary" for a in client.get("/api/activity/summary").json()["api"])

    errors = client.get("/api/activity/events?errors_only=true").json()
    assert [e["detail"] for e in errors] == ["timed out"]
    assert "sentinel_api_requests_total" in client.get("/metrics").text


def test_old_events_are_pruned(db):
    now = datetime.now(timezone.utc)
    db.add_all([
        ActivityEvent(at=now - timedelta(days=20), kind="job", name="x", status="ok", duration_ms=1),
        ActivityEvent(at=now - timedelta(days=1), kind="job", name="y", status="ok", duration_ms=1),
    ])
    db.commit()
    prune_history(db, days=0)  # events are pruned even when sync history is kept forever
    assert [e.name for e in events(db)] == ["y"]


def test_llm_calls_never_overlap(monkeypatch):
    """Sentinel-wide: concurrent generate() calls run one at a time (llm_max_concurrent = 1)."""
    active, peak = 0, 0

    async def fake(self, prompt, timeout, json_mode, t):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        return "ok"

    monkeypatch.setattr(LLMService, "_generate", fake)

    async def main():
        llm = LLMService("http://llm/v1", "m", api_key="", reasoning_effort="")
        return await asyncio.gather(*(llm.generate("x", purpose=f"p{i}") for i in range(4)))

    assert asyncio.run(main()) == ["ok"] * 4
    assert peak == 1
