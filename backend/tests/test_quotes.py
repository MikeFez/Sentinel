from datetime import datetime, timedelta, timezone

from app.models import Company
from app.services.quote_service import market_open, last_close, quote_due
from tests import factories as f


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_market_hours_in_new_york():
    # 2026-10-05 is a Monday; New York is UTC-4 in October
    assert not market_open(utc(2026, 10, 5, 13, 29))  # 09:29 ET
    assert market_open(utc(2026, 10, 5, 13, 30))  # 09:30 ET
    assert market_open(utc(2026, 10, 5, 19, 59))  # 15:59 ET
    assert not market_open(utc(2026, 10, 5, 20, 0))  # 16:00 ET
    assert not market_open(utc(2026, 10, 3, 15, 0))  # Saturday


def test_last_close_skips_the_weekend():
    assert last_close(utc(2026, 10, 4, 12, 0)) == utc(2026, 10, 2, 20, 0)  # Sunday -> Friday close
    assert last_close(utc(2026, 10, 5, 19, 0)) == utc(2026, 10, 2, 20, 0)  # Monday before close
    assert last_close(utc(2026, 10, 5, 20, 1)) == utc(2026, 10, 5, 20, 0)  # Monday after close


def test_quote_due():
    weekend = utc(2026, 10, 4, 12, 0)
    assert quote_due(Company(quote_at=None), weekend)
    # One refresh after Friday's close, then nothing until Monday
    assert quote_due(Company(quote_at=utc(2026, 10, 2, 19, 55)), weekend)
    assert not quote_due(Company(quote_at=utc(2026, 10, 2, 20, 3)), weekend)
    assert quote_due(Company(quote_at=utc(2026, 10, 5, 14, 0)), utc(2026, 10, 5, 14, 5))  # market open


def test_record_price_keeps_the_latest_per_new_york_day(db):
    from app.models import DailyPrice
    from app.services.price_history import record_price
    c = f.company(db)
    close = datetime(2026, 10, 9, 20, 5, tzinfo=timezone.utc)  # Fri 4:05 PM in New York
    record_price(db, c.id, 10.0, close - timedelta(hours=3))
    record_price(db, c.id, 11.0, close)
    record_price(db, c.id, 9.0, close - timedelta(hours=1))  # older than what's stored: ignored
    db.commit()
    [row] = db.query(DailyPrice).all()
    assert (row.day, row.price) == ("2026-10-09", 11.0)


def test_quote_refresh_collects_benchmark_without_watching_spy(db, monkeypatch):
    from app.models import BenchmarkPrice
    from app.services import quote_service
    called = []

    class Quotes:
        def __init__(self, key): pass
        def get_quote(self, ticker):
            called.append(ticker)
            return {"price": 500 if ticker == "SPY" else 10, "change": 1}

    monkeypatch.setattr(quote_service, "StockService", Quotes)
    f.company(db)
    now = utc(2026, 10, 5, 20, 5)
    assert quote_service.refresh_quotes(db, "key", now) == 1
    assert called == ["SPY", "ACME"]
    assert db.query(BenchmarkPrice).one().price == 500
    quote_service.refresh_quotes(db, "key", now + timedelta(minutes=1))
    assert called == ["SPY", "ACME"]  # no repeated refresh after close
