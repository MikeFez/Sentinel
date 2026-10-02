from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class IPOEntryBase(BaseModel):
    name: str
    symbol: Optional[str] = None
    date: str
    price_range_low: Optional[float] = None
    price_range_high: Optional[float] = None
    shares: Optional[int] = None
    exchange: Optional[str] = None
    status: Optional[str] = None
    total_shares_value: Optional[float] = None
    debut_price: Optional[float] = None
    current_price: Optional[float] = None


class IPOEntryResponse(IPOEntryBase):
    id: str
    fetched_at: datetime

    class Config:
        from_attributes = True
