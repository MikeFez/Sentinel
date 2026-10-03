from sqlalchemy import Column, Integer, String, Text
import uuid
from ..database import Base, UTCDateTime


class ActivityEvent(Base):
    """One outbound call (LLM, Finnhub, SEC), sync, or background job run, for the Activity page."""

    __tablename__ = "activity_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    at = Column(UTCDateTime, nullable=False, index=True)  # when it started
    kind = Column(String, nullable=False, index=True)  # llm | finnhub | sec | sync | job
    name = Column(String, nullable=False)  # e.g. "analysis", "quote", "filing summary", "quote refresh"
    status = Column(String, nullable=False)  # ok | error
    duration_ms = Column(Integer, nullable=False)
    company_id = Column(String, nullable=True, index=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)  # error message or a short note
