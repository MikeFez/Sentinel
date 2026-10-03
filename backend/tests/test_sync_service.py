import asyncio

from app.models.sync import SyncStatus
from app.services.llm_service import Analysis
from app.services.sync_service import SyncService
from tests import factories as f


class FakeStock:
    def __init__(self, price=10.0):
        self.price = price

    def get_stock_data(self, ticker):
        return {"stock_price": self.price, "price_change": 1.5, "industry": "Rockets"} if self.price else None

    def get_company_news(self, ticker, days=7, limit=10):
        return [{"title": f"News {i}", "url": f"https://news/{i}"} for i in range(limit)]

    def get_analyst_recommendations(self, ticker):
        return {"buy": 3}

    def get_earnings_calendar(self, ticker):
        return []

    def get_insider_transactions(self, ticker):
        return []

    def get_basic_financials(self, ticker):
        return {}

    def get_earnings_history(self, ticker):
        return [{"quarter": 2, "year": 2026, "actual": 0.1, "estimate": 0.08, "surprisePercent": 25.0}]


class FakeLLM:
    def __init__(self, analysis=None, error="connection refused"):
        self.analysis = analysis
        self.last_error = None if analysis else error
        self.calls = []

    async def analyze_company(self, **kwargs):
        self.calls.append(kwargs)
        return self.analysis, "the prompt"


def run(db, company, llm, stock=None, news_count=3):
    service = SyncService(db, "http://llm/v1", "m", "key")
    service.stock_service = stock or FakeStock()
    service.llm_service = llm
    return asyncio.run(service.sync_company(company.id, news_count=news_count))


def test_success_stores_structured_analysis_and_quote(db):
    c = f.company(db)
    llm = FakeLLM(Analysis("Up.", "bullish", ["k"], ["r"], "Price rose."))
    s = run(db, c, llm)
    db.refresh(c)
    assert s.status == SyncStatus.completed and s.error is None
    assert (s.ai_summary, s.ai_sentiment.value, s.ai_key_points, s.ai_risks, s.ai_changes) == ("Up.", "bullish", ["k"], ["r"], "Price rose.")
    assert len(s.raw_news) == 3  # honours news_count
    assert s.earnings_history[0]["actual"] == 0.1
    assert llm.calls[0]["earnings_history"] == s.earnings_history
    from app.models import NewsArticle
    assert db.query(NewsArticle).filter(NewsArticle.company_id == c.id).count() == 3
    assert c.quote_price == 10.0 and c.industry == "Rockets"
    assert llm.calls[0]["previous"] is None


def test_previous_analysis_is_passed_to_the_llm(db):
    c = f.company(db)
    f.sync(db, c, hours_ago=30, sentiment="bearish", summary="Was weak.", stock_price=8.0)
    llm = FakeLLM(Analysis("Better.", "mixed"))
    run(db, c, llm)
    prev = llm.calls[0]["previous"]
    assert prev["summary"] == "Was weak." and prev["sentiment"] == "bearish" and prev["price"] == 8.0


def test_llm_failure_keeps_data_and_records_why(db):
    c = f.company(db)
    s = run(db, c, FakeLLM(None, "timed out"))
    assert s.status == SyncStatus.completed
    assert s.stock_price == 10.0 and s.raw_news
    assert s.ai_sentiment is None and s.ai_summary is None
    assert s.error == "AI analysis unavailable: timed out"


def test_missing_price_fails_the_sync(db):
    c = f.company(db)
    s = run(db, c, FakeLLM(Analysis("x", "neutral")), stock=FakeStock(price=None))
    assert s.status == SyncStatus.failed
    assert "No price data" in s.error
