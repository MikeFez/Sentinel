from sqlalchemy import Column, String, Float, ForeignKey
from ..database import Base, UTCDateTime


class InboxReview(Base):
    """Review state shared across browsers; each changed event has its own key."""
    __tablename__ = "inbox_reviews"
    key = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    reviewed_at = Column(UTCDateTime, nullable=True)
    snoozed_until = Column(UTCDateTime, nullable=True)


class BenchmarkPrice(Base):
    __tablename__ = "benchmark_prices"
    symbol = Column(String, primary_key=True)
    day = Column(String, primary_key=True)
    price = Column(Float, nullable=False)
    at = Column(UTCDateTime, nullable=False)
