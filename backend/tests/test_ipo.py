from datetime import datetime, timedelta, timezone

import httpx

from app.models import IPOEntry
from app.routers import ipo as ipo_router
from app.services import stock_service


class FakeStock:
    """IPO calendar with one listed IPO; price history refused like Finnhub's free plan."""
    candle_calls = 0

    def __init__(self, key):
        pass

    def get_ipo_calendar(self, days_ahead=90):
        return [{"name": "NewCo", "symbol": "NEW", "date": "2026-10-01", "status": "priced", "price": "10-12"}]

    def get_debut_price(self, symbol, date):
        FakeStock.candle_calls += 1
        return None

    def _fetch_quote(self, symbol):
        return {"c": 14.0}


def test_calendar_replaces_the_cache_after_fetching(client, db, monkeypatch):
    db.add(IPOEntry(name="Old", date="2026-01-01", fetched_at=datetime.now(timezone.utc) - timedelta(days=2)))
    db.commit()
    monkeypatch.setattr(ipo_router, "StockService", FakeStock)
    [row] = client.get("/api/ipo/calendar").json()
    assert (row["name"], row["current_price"], row["price_range_low"]) == ("NewCo", 14.0, 10.0)
    assert [e.name for e in db.query(IPOEntry)] == ["NewCo"]


def test_debut_prices_stop_after_the_plan_refuses_price_history(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(403, json={"error": "You don't have access to this resource."})

    real_client = httpx.Client
    monkeypatch.setattr(stock_service.httpx, "Client", lambda: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(stock_service, "_candles_in_plan", True)
    s = stock_service.StockService("key")
    assert s.get_debut_price("AAA", "2026-10-01") is None
    assert s.get_debut_price("BBB", "2026-10-02") is None
    assert len(calls) == 1
