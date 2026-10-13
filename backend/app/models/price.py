from sqlalchemy import Column, String, Float, ForeignKey
from ..database import Base, UTCDateTime


class DailyPrice(Base):
    """The last price seen for a company on each New York trading day (from quote refreshes and syncs).

    The quote refresh runs once after each close, so a finished day holds its closing price. Kept
    forever (one small row per day) so the AI scorecard can grade any call, not just ones near a sync.
    """

    __tablename__ = "daily_prices"

    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True)
    day = Column(String, primary_key=True)  # YYYY-MM-DD in New York
    price = Column(Float, nullable=False)
    at = Column(UTCDateTime, nullable=False)  # when the price was seen
