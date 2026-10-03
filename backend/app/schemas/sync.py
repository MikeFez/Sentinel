from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class NewsArticle(BaseModel):
    title: str
    url: str
    published_at: Optional[int] = None
    source: Optional[str] = None


class SyncResponse(BaseModel):
    id: str
    company_id: str
    synced_at: datetime
    stock_price: Optional[float] = None
    price_change: Optional[float] = None
    market_cap: Optional[str] = None
    pe_ratio: Optional[float] = None
    volume: Optional[int] = None
    fifty_two_wk_hi: Optional[float] = None
    fifty_two_wk_lo: Optional[float] = None
    raw_news: Optional[List[Dict[str, Any]]] = None
    ai_summary: Optional[str] = None
    ai_sentiment: Optional[str] = None
    llm_prompt: Optional[str] = None
    analyst_ratings: Optional[Dict[str, Any]] = None
    earnings_dates: Optional[List[Dict[str, Any]]] = None
    insider_transactions: Optional[List[Dict[str, Any]]] = None
    financials: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    ai_key_points: Optional[List[str]] = None
    ai_risks: Optional[List[str]] = None
    ai_changes: Optional[str] = None
    reason: Optional[str] = None
    earnings_history: Optional[List[Dict[str, Any]]] = None
    status: str

    model_config = ConfigDict(from_attributes=True)
