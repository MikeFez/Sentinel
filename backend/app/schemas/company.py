from pydantic import BaseModel, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)


class SyncSummary(BaseModel):
    id: str
    synced_at: datetime
    stock_price: Optional[float] = None
    price_change: Optional[float] = None
    ai_sentiment: Optional[str] = None
    ai_summary: Optional[str] = None
    error: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class LatestAnalysis(BaseModel):
    sync_id: str
    synced_at: datetime
    ai_sentiment: Optional[str] = None
    ai_summary: str
    ai_changes: Optional[str] = None
    # The price when the analysis was written, to show how far it has moved since
    stock_price: Optional[float] = None
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

    model_config = ConfigDict(from_attributes=True)


class Headline(BaseModel):
    title: str
    url: str
    published_at: Optional[int] = None  # unix seconds


class SyncProgress(BaseModel):
    steps: List[str]
    current: int
    # True while waiting for a free LLM slot (another sync or job is using it)
    waiting: bool = False


class CompanyListResponse(CompanyResponse):
    latest_sync: Optional[SyncSummary] = None
    latest_analysis: Optional[LatestAnalysis] = None
    is_stale: bool = False
    is_syncing: bool = False
    sync_progress: Optional[SyncProgress] = None
    latest_news_at: Optional[datetime] = None
    latest_headline: Optional[Headline] = None
    sync_error: Optional[str] = None
    has_alert: bool = False

    model_config = ConfigDict(from_attributes=True)
