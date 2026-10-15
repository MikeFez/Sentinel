"""Quote refresh for public companies, on its own schedule (no news, no AI analysis)."""
import logging
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..models import Company, BenchmarkPrice
from .price_history import record_price, record_benchmark
from .stock_service import StockService

logger = logging.getLogger(__name__)

NEW_YORK = ZoneInfo("America/New_York")
OPEN, CLOSE = time(9, 30), time(16, 0)


def market_open(now: Optional[datetime] = None) -> bool:
    """Regular US trading hours (holidays aren't known; refreshing on one is harmless)."""
    ny = (now or datetime.now(timezone.utc)).astimezone(NEW_YORK)
    return ny.weekday() < 5 and OPEN <= ny.time() < CLOSE


def last_close(now: Optional[datetime] = None) -> datetime:
    """The most recent regular-session close at or before `now` (UTC)."""
    ny = (now or datetime.now(timezone.utc)).astimezone(NEW_YORK)
    day = ny.date()
    while True:
        close = datetime.combine(day, CLOSE, tzinfo=NEW_YORK)
        if day.weekday() < 5 and close <= ny:
            return close.astimezone(timezone.utc)
        day -= timedelta(days=1)


def quote_due(company: Company, now: datetime) -> bool:
    """Refresh while the market is open, and once after each close for the closing price."""
    if company.quote_at is None:
        return True
    return market_open(now) or company.quote_at < last_close(now)


def refresh_quotes(db: Session, api_key: str, now: Optional[datetime] = None) -> int:
    """Fetch quotes for public companies that are due. Blocking: run it in a worker thread."""
    now = now or datetime.now(timezone.utc)
    from ..routers.settings import get_float
    from . import notifier

    service = StockService(api_key)
    move_threshold = get_float(db, "move_sync_percent")
    updated = 0
    benchmark = db.query(BenchmarkPrice).filter(BenchmarkPrice.symbol == "SPY").order_by(BenchmarkPrice.at.desc()).first()
    if quote_due(Company(quote_at=benchmark.at if benchmark else None), now):
        quote = service.get_quote("SPY")
        if quote:
            record_benchmark(db, quote["price"], now)
    for company in db.query(Company).filter(Company.status == "public", Company.ticker.isnot(None)):
        if not quote_due(company, now):
            continue
        quote = service.get_quote(company.ticker)
        if not quote:
            continue
        old_price = company.quote_price
        company.quote_price = quote["price"]
        company.quote_change = quote["change"]
        company.quote_at = now
        record_price(db, company.id, quote["price"], now)
        notifier.after_quote(db, company, old_price, move_threshold, now)
        updated += 1
    db.commit()
    return updated
