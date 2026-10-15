"""Daily price history (daily_prices): the last price seen per company per New York trading day."""
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..models import DailyPrice, BenchmarkPrice

NEW_YORK = ZoneInfo("America/New_York")


def record_price(db: Session, company_id: str, price: Optional[float], at: Optional[datetime] = None) -> None:
    """Keep `price` as the company's price for its New York day, unless a later one is already stored.

    Doesn't commit; the caller's commit saves it.
    """
    if price is None:
        return
    at = at or datetime.now(timezone.utc)
    day = at.astimezone(NEW_YORK).date().isoformat()
    row = db.get(DailyPrice, (company_id, day))
    if row is None:
        db.add(DailyPrice(company_id=company_id, day=day, price=price, at=at))
        db.flush()  # so a second call in this session finds it (the session doesn't autoflush)
    elif row.at is None or row.at <= at:
        row.price, row.at = price, at


def record_benchmark(db: Session, price: float, at: datetime, symbol: str = "SPY") -> None:
    if price <= 0:
        return
    day = at.astimezone(NEW_YORK).date().isoformat()
    row = db.get(BenchmarkPrice, (symbol, day))
    if row is None:
        db.add(BenchmarkPrice(symbol=symbol, day=day, price=price, at=at))
        db.flush()
    elif row.at <= at:
        row.price, row.at = price, at
