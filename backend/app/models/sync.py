from sqlalchemy import Column, String, Text, DateTime, Float, Integer, JSON, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from ..database import Base, UTCDateTime


class SyncStatus(str, enum.Enum):
    pending = "pending"
    syncing = "syncing"
    completed = "completed"
    failed = "failed"


class SentimentType(str, enum.Enum):
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"
    mixed = "mixed"


class Sync(Base):
    __tablename__ = "syncs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    synced_at = Column(UTCDateTime, server_default=func.now())
    stock_price = Column(Float, nullable=True)
    price_change = Column(Float, nullable=True)
    market_cap = Column(String, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    fifty_two_wk_hi = Column(Float, nullable=True)
    fifty_two_wk_lo = Column(Float, nullable=True)
    raw_news = Column(JSON, nullable=True)
    ai_summary = Column(Text, nullable=True)
    ai_sentiment = Column(Enum(SentimentType), nullable=True)
    status = Column(Enum(SyncStatus), nullable=False, default=SyncStatus.pending)

    # New Finnhub data fields
    analyst_ratings = Column(JSON, nullable=True)  # {buy, hold, sell, strong_buy, strong_sell}
    earnings_dates = Column(JSON, nullable=True)  # List of upcoming earnings
    insider_transactions = Column(JSON, nullable=True)  # Recent insider trades
    financials = Column(JSON, nullable=True)  # Basic financial metrics

    # Store the actual LLM prompt for transparency
    llm_prompt = Column(Text, nullable=True)

    # Why the sync failed, or why part of it (e.g. the AI analysis) didn't complete
    error = Column(Text, nullable=True)

    # Relationships
    company = relationship("Company", back_populates="syncs")
