from sqlalchemy import Boolean, Column, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from ..database import Base, UTCDateTime


class NewsStory(Base):
    """Articles from different outlets about the same event, grouped by the LLM."""

    __tablename__ = "news_stories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    material = Column(Boolean, nullable=False, default=False)  # could move the stock / change the thesis
    themes = Column(JSON, nullable=True)  # short recurring labels, e.g. ["SpaceX competition"]
    first_seen_at = Column(UTCDateTime, server_default=func.now())
    last_seen_at = Column(UTCDateTime, server_default=func.now())

    company = relationship("Company", back_populates="stories")
    articles = relationship("NewsArticle", back_populates="story")
