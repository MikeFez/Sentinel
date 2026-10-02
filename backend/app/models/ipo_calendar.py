from sqlalchemy import Column, String, DateTime, Float, Integer
from sqlalchemy.sql import func
import uuid
from ..database import Base


class IPOEntry(Base):
    __tablename__ = "ipo_calendar"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # Company name
    symbol = Column(String, nullable=True)  # Ticker symbol (if assigned)
    date = Column(String, nullable=False)  # IPO date
    price_range_low = Column(Float, nullable=True)  # Expected price range low
    price_range_high = Column(Float, nullable=True)  # Expected price range high
    shares = Column(Integer, nullable=True)  # Number of shares
    exchange = Column(String, nullable=True)  # Exchange (NYSE, NASDAQ, etc.)
    status = Column(String, nullable=True)  # Status (expected, priced, etc.)
    total_shares_value = Column(Float, nullable=True)  # Total offering size in dollars
    debut_price = Column(Float, nullable=True)  # Opening price on first trading day
    current_price = Column(Float, nullable=True)  # Latest market price
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
