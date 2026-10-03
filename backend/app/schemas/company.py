from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models.company import CompanyStatus


class CompanyBase(BaseModel):
    name: str
    ticker: Optional[str] = None
    status: CompanyStatus = CompanyStatus.public
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    alert_above: Optional[float] = None
    alert_below: Optional[float] = None
    shares_owned: Optional[float] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    ticker: Optional[str] = None
    status: Optional[CompanyStatus] = None
    description: Optional[str] = None
    website: Optional[str] = None
    alert_above: Optional[float] = None
    alert_below: Optional[float] = None
    shares_owned: Optional[float] = None


class TagInCompany(BaseModel):
    id: str
    name: str
    color: str

    class Config:
        from_attributes = True


class SyncSummary(BaseModel):
    id: str
    synced_at: datetime
    stock_price: Optional[float] = None
    price_change: Optional[float] = None
    ai_sentiment: Optional[str] = None
    ai_summary: Optional[str] = None
    error: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class LatestAnalysis(BaseModel):
    sync_id: str
    synced_at: datetime
    ai_sentiment: Optional[str] = None
    ai_summary: str
    ai_changes: Optional[str] = None
    # Sentiment of the analysis before this one, to spot flips
    previous_sentiment: Optional[str] = None


class CompanyResponse(CompanyBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: List[TagInCompany] = []
    quote_price: Optional[float] = None
    quote_change: Optional[float] = None
    quote_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyListResponse(CompanyResponse):
    latest_sync: Optional[SyncSummary] = None
    latest_analysis: Optional[LatestAnalysis] = None
    is_stale: bool = False
    is_syncing: bool = False
    sync_error: Optional[str] = None
    has_alert: bool = False

    class Config:
        from_attributes = True
