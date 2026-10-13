import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import Optional
import logging

from ..models import Company, Sync, SyncStatus
from ..models.sync import SentimentType
from .stock_service import StockService
from .news_service import NewsService
from . import activity, sync_progress
from .news_store import store_articles
from .price_history import record_price
from .stories import group_new_articles
from .llm_service import LLMService

logger = logging.getLogger(__name__)


class SyncService:
    """Service for orchestrating company data synchronization"""

    def __init__(self, db: Session, llm_base_url: str, llm_model: str, finnhub_api_key: str):
        self.db = db
        self.stock_service = StockService(finnhub_api_key)
        self.news_service = NewsService()
        self.llm_service = LLMService(llm_base_url, llm_model)

    async def sync_company(self, company_id: str, news_count: int = 10, existing_sync: Optional[Sync] = None) -> Optional[Sync]:
        """Run a sync (see _sync_company), recorded on the Activity page with its company and reason."""
        reason = (existing_sync.reason if existing_sync else None) or "sync"
        with activity.context(company_id=company_id), activity.track("sync", reason) as t:
            try:
                sync = await self._sync_company(company_id, news_count, existing_sync)
            finally:
                sync_progress.end(company_id)
            if sync is not None:
                from . import notifier

                await asyncio.to_thread(notifier.after_sync, sync.id)
            if sync is None:
                t.fail("company not found")
            elif sync.status == SyncStatus.failed:
                t.fail(sync.error or "failed")
            elif sync.error:
                t.note(sync.error)
            return sync

    async def _sync_company(self, company_id: str, news_count: int = 10, existing_sync: Optional[Sync] = None) -> Optional[Sync]:
        """
        Synchronize data for a company.

        Args:
            company_id: UUID of the company to sync
            news_count: Number of news articles to fetch
            existing_sync: Pre-created Sync record to update (skips creation)

        Returns:
            Sync object with results or None if company not found
        """
        # Get the company
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            logger.error(f"Company not found: {company_id}")
            return None

        if existing_sync:
            sync = existing_sync
        else:
            # Create sync record with "syncing" status
            sync = Sync(
                company_id=company_id,
                status=SyncStatus.syncing,
            )
            self.db.add(sync)
            self.db.commit()
            self.db.refresh(sync)

        from ..routers.settings import get_setting as _get_setting
        public = company.status == "public" and bool(company.ticker)
        sync_progress.begin(company_id, public, debate=_get_setting(self.db, "analysis_mode") == "debate")

        try:
            if public:
                logger.info(f"Fetching comprehensive data for {company.ticker}")
                # Finnhub calls are blocking (with retry back-off); keep them off the event loop
                data = await asyncio.to_thread(self._fetch_public_data, company.ticker, news_count)
            else:
                # For non-public companies, fall back to Google News RSS
                news_query = f"{company.name} IPO" if company.status == "pre_ipo" else company.name
                logger.info(f"Fetching news for: {news_query}")
                data = {"stock_data": {}, "news": await asyncio.to_thread(self.news_service.get_news, news_query, news_count)}

            stock_data = data["stock_data"]
            news_articles = data["news"]
            analyst_ratings = data.get("analyst_ratings")
            insider_transactions = data.get("insider_transactions")

            if company.status == "public" and company.ticker and not stock_data:
                raise RuntimeError(f"No price data from Finnhub for {company.ticker} (check the ticker and FINNHUB_API_KEY)")

            sync.stock_price = stock_data.get("stock_price")
            sync.price_change = stock_data.get("price_change")
            sync.market_cap = stock_data.get("market_cap")
            sync.pe_ratio = stock_data.get("pe_ratio")
            sync.volume = stock_data.get("volume")
            sync.fifty_two_wk_hi = stock_data.get("fifty_two_wk_hi")
            sync.fifty_two_wk_lo = stock_data.get("fifty_two_wk_lo")
            if stock_data.get("industry"):
                company.industry = stock_data["industry"]
            if stock_data.get("stock_price") is not None:
                company.quote_price = stock_data["stock_price"]
                company.quote_change = stock_data.get("price_change")
                company.quote_at = datetime.now(timezone.utc)
                record_price(self.db, company.id, company.quote_price, company.quote_at)

            sync.raw_news = news_articles
            sync.analyst_ratings = analyst_ratings
            sync.earnings_dates = data.get("earnings_dates")
            sync.insider_transactions = insider_transactions
            sync.financials = data.get("financials")
            sync.earnings_history = data.get("earnings_history") or None
            sync.peers = data.get("peers") or None
            store_articles(self.db, company.id, news_articles)
            # Save the market data now, so it survives even if the analysis below fails
            self.db.commit()

            # Group new articles into stories first, so material ones reach the analysis prompt
            try:
                await group_new_articles(self.db, self.llm_service, company.id, company.name)
            except Exception as e:
                self.db.rollback()
                logger.warning(f"Story grouping failed for {company.name}: {e}")

            logger.info(f"Generating AI analysis for {company.name}")
            custom_instructions = _get_setting(self.db, "ai_prompt_instructions") or None
            previous = (
                self.db.query(Sync)
                .filter(
                    Sync.company_id == company.id,
                    Sync.id != sync.id,
                    Sync.status == SyncStatus.completed,
                    Sync.ai_summary.isnot(None),
                )
                .order_by(Sync.synced_at.desc())
                .first()
            )
            analysis, prompt = await self.llm_service.analyze_company(
                company_name=company.name,
                ticker=company.ticker,
                status=company.status.value if hasattr(company.status, "value") else company.status,
                stock_data=stock_data or None,
                news_articles=news_articles,
                analyst_ratings=analyst_ratings,
                insider_transactions=insider_transactions,
                earnings_history=sync.earnings_history,
                peers=sync.peers,
                extra_context=self.extra_context(company),
                debate=_get_setting(self.db, "analysis_mode") == "debate",
                custom_instructions=custom_instructions,
                previous=previous and {
                    "date": previous.synced_at.strftime("%Y-%m-%d"),
                    "sentiment": previous.ai_sentiment.value if previous.ai_sentiment else None,
                    "summary": previous.ai_summary,
                    "price": previous.stock_price,
                },
            )

            sync.llm_prompt = prompt
            sync.llm_model = self.llm_service.model
            if analysis is None:
                # Market data is still good; record why there's no analysis instead of a fake "neutral"
                sync.error = f"AI analysis unavailable: {self.llm_service.last_error or 'no response from the LLM'}"
            else:
                sync.ai_summary = analysis.summary
                sync.ai_sentiment = SentimentType(analysis.sentiment)
                sync.ai_key_points = analysis.key_points
                sync.ai_risks = analysis.risks
                sync.ai_changes = analysis.changes
                sync.ai_bull = analysis.bull_case
                sync.ai_bear = analysis.bear_case

            sync.status = SyncStatus.completed
            self.db.commit()
            self.db.refresh(sync)
            logger.info(f"Sync completed for company: {company.name}")
            return sync

        except Exception as e:
            logger.error(f"Sync failed for company {company.name}: {e}")
            self.db.rollback()
            sync.status = SyncStatus.failed
            sync.error = str(e) or e.__class__.__name__
            self.db.commit()
            self.db.refresh(sync)
            return sync

    def extra_context(self, company: Company) -> Optional[str]:
        """Recent SEC filings and material news stories, as extra prompt context."""
        from ..models import Filing, NewsStory

        lines = []
        filings = (
            self.db.query(Filing)
            .filter(Filing.company_id == company.id, Filing.summary.isnot(None), Filing.routine.isnot(True))
            .order_by(Filing.filed_on.desc())
            .limit(3)
            .all()
        )
        if filings:
            lines.append("Recent SEC filings:")
            lines += [f"- {f.form} filed {f.filed_on}: {f.summary}" for f in filings]
            for f in filings:
                if f.new_risks:
                    lines.append(f"New risk factors in the {f.form} filed {f.filed_on}: " + "; ".join(f.new_risks))
        stories = (
            self.db.query(NewsStory)
            .filter(NewsStory.company_id == company.id, NewsStory.material.is_(True))
            .order_by(NewsStory.last_seen_at.desc())
            .limit(5)
            .all()
        )
        if stories:
            lines.append("Material news stories recently:")
            lines += [f"- {s.title}" + (f": {s.summary}" if s.summary else "") for s in stories]
        return "\n".join(lines) or None

    def _fetch_public_data(self, ticker: str, news_count: int) -> dict:
        """Blocking Finnhub fetches for a public company (run in a worker thread)."""
        svc = self.stock_service
        return {
            "stock_data": svc.get_stock_data(ticker) or {},
            "news": svc.get_company_news(ticker, days=7, limit=news_count),
            "analyst_ratings": svc.get_analyst_recommendations(ticker),
            "earnings_dates": svc.get_earnings_calendar(ticker),
            "earnings_history": svc.get_earnings_history(ticker),
            "peers": svc.get_peers(ticker),
            "insider_transactions": svc.get_insider_transactions(ticker),
            "financials": svc.get_basic_financials(ticker),
        }
