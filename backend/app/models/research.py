from sqlalchemy import Column, String, JSON
from sqlalchemy.sql import func
import uuid
from ..database import Base, UTCDateTime


class ResearchItem(Base):
    """A saved Research result: an ad-hoc analysis or a theme discovery, kept whole as JSON."""

    __tablename__ = "research_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    kind = Column(String, nullable=False, index=True)  # "analysis" | "discovery"
    title = Column(String, nullable=False)
    created_at = Column(UTCDateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(UTCDateTime, server_default=func.now(), nullable=False)
    data = Column(JSON, nullable=False)
