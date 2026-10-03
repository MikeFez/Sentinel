from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from ..database import get_db
from ..models import IPOEntry
from ..schemas.ipo import IPOEntryResponse
from ..services.stock_service import StockService
from ..config import settings

router = APIRouter(prefix="/api/ipo", tags=["ipo"])


def _parse_price_range(price_str: str):
    low, high = None, None
    if price_str and "-" in price_str:
        try:
            parts = price_str.split("-")
            low = float(parts[0].strip())
            high = float(parts[1].strip())
        except (ValueError, IndexError):
            pass
    return low, high


def _build_entry(ipo: dict, debut_price: Optional[float], current_price: Optional[float]) -> IPOEntry:
    price_low, price_high = _parse_price_range(ipo.get("price", ""))
    return IPOEntry(
        name=ipo.get("name", ""),
        symbol=ipo.get("symbol"),
        date=ipo.get("date", ""),
        price_range_low=price_low,
        price_range_high=price_high,
        shares=ipo.get("numberOfShares"),
        exchange=ipo.get("exchange"),
        status=ipo.get("status"),
        total_shares_value=ipo.get("totalSharesValue"),
        debut_price=debut_price,
        current_price=current_price,
    )


@router.get("/calendar", response_model=List[IPOEntryResponse])
def get_ipo_calendar(db: Session = Depends(get_db)):
    """
    Get IPO calendar. Fetches from Finnhub and caches for 24 hours.
    Debut prices are preserved across refreshes (historical, fetched once).
    Current prices are refreshed on each fetch for listed IPOs.
    """
    one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_entries = (
        db.query(IPOEntry)
        .filter(IPOEntry.fetched_at >= one_day_ago)
        .all()
    )
    if recent_entries:
        return recent_entries

    stock_service = StockService(settings.finnhub_api_key)
    ipo_data = stock_service.get_ipo_calendar(days_ahead=90)

    # Preserve debut prices already on record (keyed by symbol, then name+date)
    saved_debut: dict = {}
    for row in db.query(IPOEntry).all():
        if row.debut_price is not None:
            if row.symbol:
                saved_debut[row.symbol] = row.debut_price
            saved_debut[(row.name, row.date)] = row.debut_price

    db.query(IPOEntry).delete()

    new_entries = []
    for ipo in ipo_data:
        symbol = ipo.get("symbol")
        name = ipo.get("name", "")
        date = ipo.get("date", "")
        status = (ipo.get("status") or "").lower()
        is_listed = status in ("listed", "priced")

        # Restore saved debut price, or fetch it fresh for newly listed IPOs
        debut_price = (
            saved_debut.get(symbol)
            or saved_debut.get((name, date))
        )
        if debut_price is None and is_listed and symbol:
            debut_price = stock_service.get_debut_price(symbol, date)

        # Always refresh current price for listed/priced IPOs
        current_price = None
        if is_listed and symbol:
            quote = stock_service._fetch_quote(symbol)
            if quote:
                current_price = quote.get("c") or None

        entry = _build_entry(ipo, debut_price, current_price)
        db.add(entry)
        new_entries.append(entry)

    db.commit()
    for entry in new_entries:
        db.refresh(entry)

    return new_entries


@router.post("/refresh")
def refresh_ipo_calendar(db: Session = Depends(get_db)):
    """Force refresh the IPO calendar"""
    db.query(IPOEntry).delete()
    db.commit()
    return {"message": "IPO calendar cleared. Will refresh on next request."}
