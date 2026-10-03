from sqlalchemy import Column, String, Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from ..database import Base, UTCDateTime


class NewsArticle(Base):
    """A news article seen for a company, stored once no matter how many syncs return it."""

    __tablename__ = "news_articles"
    __table_args__ = (UniqueConstraint("company_id", "url", name="uq_news_company_url"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    title = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    published_at = Column(Integer, nullable=True, index=True)  # unix seconds
    first_seen_at = Column(UTCDateTime, server_default=func.now(), nullable=False)
    story_id = Column(String, ForeignKey("news_stories.id", ondelete="SET NULL"), nullable=True, index=True)

    company = relationship("Company", back_populates="news")
    story = relationship("NewsStory", back_populates="articles")
