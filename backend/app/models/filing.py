from sqlalchemy import Boolean, Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from ..database import Base, UTCDateTime


class Filing(Base):
    """An SEC filing (8-K, 10-Q, 10-K) for a tracked public company, with an AI summary."""

    __tablename__ = "filings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    accession = Column(String, nullable=False, unique=True)  # SEC accession number
    form = Column(String, nullable=False)  # 8-K, 10-Q, 10-K
    filed_on = Column(String, nullable=False)  # YYYY-MM-DD
    items = Column(String, nullable=True)  # 8-K item numbers, e.g. "2.02,9.01"
    url = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    # 10-K only: risk-factor paragraphs that are new since the previous 10-K (summarized), and the
    # full Risk Factors text, kept so next year's 10-K can be compared with it
    new_risks = Column(JSON, nullable=True)
    risk_text = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    # An 8-K with nothing new for investors (exhibits, vote tallies...): dimmed, and left out of analyses
    routine = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(UTCDateTime, server_default=func.now())

    company = relationship("Company", back_populates="filings")
