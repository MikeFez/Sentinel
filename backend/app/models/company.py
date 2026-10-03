from sqlalchemy import Column, String, Text, DateTime, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from ..database import Base, UTCDateTime


class CompanyStatus(str, enum.Enum):
    public = "public"
    pre_ipo = "pre_ipo"
    private = "private"
    acquired = "acquired"


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=True)
    status = Column(Enum(CompanyStatus), nullable=False, default=CompanyStatus.public)
    description = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    created_at = Column(UTCDateTime, server_default=func.now())
    updated_at = Column(UTCDateTime, onupdate=func.now())

    # Industry (populated from Finnhub profile during sync)
    industry = Column(String, nullable=True)

    # Price alerts
    alert_above = Column(Float, nullable=True)
    alert_below = Column(Float, nullable=True)

    # Portfolio
    shares_owned = Column(Float, nullable=True)

    # Latest quote, refreshed on its own schedule (much more often than full syncs)
    quote_price = Column(Float, nullable=True)
    quote_change = Column(Float, nullable=True)  # percent change on the day
    quote_at = Column(UTCDateTime, nullable=True)

    # Relationships
    syncs = relationship("Sync", back_populates="company", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="company_tags", back_populates="companies")
    news = relationship("NewsArticle", back_populates="company", cascade="all, delete-orphan")
