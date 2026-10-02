from sqlalchemy.orm import Session
from typing import Optional
import logging

from ..models import Company, Sync, SyncStatus
from .stock_service import StockService
from .news_service import NewsService
from .ollama_service import OllamaService

logger = logging.getLogger(__name__)


class SyncService:
    """Service for orchestrating company data synchronization"""

    def __init__(self, db: Session, ollama_url: str, ollama_model: str, finnhub_api_key: str):
        self.db = db
        self.stock_service = StockService(finnhub_api_key)
        self.news_service = NewsService()
        self.ollama_service = OllamaService(ollama_url, ollama_model)

    async def sync_company(self, company_id: str, news_count: int = 10, existing_sync: Optional[Sync] = None) -> Optional[Sync]:
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

        try:
            stock_data = {}
            news_articles = []
            analyst_ratings = None
            earnings_dates = None
            insider_transactions = None
            financials = None

            # Fetch data for public companies
            if company.status == "public" and company.ticker:
                logger.info(f"Fetching comprehensive data for {company.ticker}")

                # Fetch stock data
                stock_data = self.stock_service.get_stock_data(company.ticker) or {}

                # Fetch news from Finnhub (better quality than RSS)
                news_articles = self.stock_service.get_company_news(company.ticker, days=7)

                # Fetch analyst recommendations
                analyst_ratings = self.stock_service.get_analyst_recommendations(company.ticker)

                # Fetch earnings calendar
                earnings_dates = self.stock_service.get_earnings_calendar(company.ticker)

                # Fetch insider transactions
                insider_transactions = self.stock_service.get_insider_transactions(company.ticker)

                # Fetch basic financials
                financials = self.stock_service.get_basic_financials(company.ticker)
            else:
                # For non-public companies, fall back to Google News RSS
                news_query = f"{company.name} IPO" if company.status == "pre_ipo" else company.name
                logger.info(f"Fetching news for: {news_query}")
                news_articles = self.news_service.get_news(news_query, max_articles=news_count)

            # Update sync record with stock data
            sync.stock_price = stock_data.get("stock_price")
            sync.price_change = stock_data.get("price_change")
            sync.market_cap = stock_data.get("market_cap")
            sync.pe_ratio = stock_data.get("pe_ratio")
            sync.volume = stock_data.get("volume")
            sync.fifty_two_wk_hi = stock_data.get("fifty_two_wk_hi")
            sync.fifty_two_wk_lo = stock_data.get("fifty_two_wk_lo")

            # Persist industry to the company record (update if we got a value)
            if stock_data.get("industry"):
                company.industry = stock_data["industry"]

            # Update sync record with new Finnhub data
            sync.raw_news = news_articles
            sync.analyst_ratings = analyst_ratings
            sync.earnings_dates = earnings_dates
            sync.insider_transactions = insider_transactions
            sync.financials = financials

            # Generate AI analysis with enhanced data
            logger.info(f"Generating AI analysis for {company.name}")
            from ..routers.settings import get_setting as _get_setting
            custom_instructions = _get_setting(self.db, "ai_prompt_instructions") or None
            summary, sentiment, prompt = await self.ollama_service.analyze_company(
                company_name=company.name,
                ticker=company.ticker,
                status=company.status.value if hasattr(company.status, 'value') else company.status,
                stock_data=stock_data if stock_data else None,
                news_articles=news_articles,
                analyst_ratings=analyst_ratings,
                insider_transactions=insider_transactions,
                custom_instructions=custom_instructions,
            )

            sync.ai_summary = summary
            sync.llm_prompt = prompt  # Store the actual prompt
            if sentiment:
                # Map sentiment string to enum
                from ..models.sync import SentimentType
                try:
                    sync.ai_sentiment = SentimentType[sentiment]
                except (KeyError, AttributeError):
                    sync.ai_sentiment = SentimentType.neutral

            sync.status = SyncStatus.completed

            self.db.commit()
            self.db.refresh(sync)

            logger.info(f"Sync completed successfully for company: {company.name}")
            return sync

        except Exception as e:
            logger.error(f"Sync failed for company {company.name}: {str(e)}")
            sync.status = SyncStatus.failed
            self.db.commit()
            self.db.refresh(sync)
            return sync
