from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.sql import func
import uuid
from ..database import Base, UTCDateTime


class Notification(Base):
    """A notification Sentinel sent (or tried to). `key` names the event, so each is sent only once."""

    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, nullable=False, unique=True)  # e.g. "flip:<sync id>", "alert:<company>:above:70.0:2026-10-13"
    kind = Column(String, nullable=False)  # price_alerts, big_moves, sentiment_flips, ..., digest, test
    company_id = Column(String, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String, nullable=False)  # sent | failed
    error = Column(Text, nullable=True)
    at = Column(UTCDateTime, server_default=func.now(), nullable=False, index=True)
