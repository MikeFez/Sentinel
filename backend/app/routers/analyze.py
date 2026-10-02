from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from ..database import get_db
from ..services.stock_service import StockService
from ..services.llm_service import LLMService
from ..config import settings as app_settings
from .settings import get_setting

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    ticker: Optional[str] = None
    company_name: Optional[str] = None
    notes: Optional[str] = None


class AnalyzeResponse(BaseModel):
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    prompt: Optional[str] = None
    stock_data: Optional[Dict[str, Any]] = None


@router.post("", response_model=AnalyzeResponse)
async def run_analysis(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Run an ad-hoc AI analysis on a ticker or company name without creating a sync record.
    If a ticker is provided, live stock data and news are fetched first.
    """
    llm_base_url = get_setting(db, "llm_base_url")
    llm_model = get_setting(db, "llm_model")

    stock_data = None
    news_articles = []
    analyst_ratings = None
    insider_transactions = None

    if request.ticker:
        stock_service = StockService(app_settings.finnhub_api_key)
        stock_data = stock_service.get_stock_data(request.ticker)
        news_articles = stock_service.get_company_news(request.ticker, days=7)
        analyst_ratings = stock_service.get_analyst_recommendations(request.ticker)
        insider_transactions = stock_service.get_insider_transactions(request.ticker)

    # Optionally prepend user notes as extra context
    if request.notes:
        news_articles = [{"title": "Analyst notes", "summary": request.notes, "source": "User", "published_at": 0, "url": ""}] + list(news_articles)

    custom_instructions = get_setting(db, "ai_prompt_instructions") or None

    llm = LLMService(llm_base_url, llm_model)
    summary, sentiment, prompt = await llm.analyze_company(
        company_name=request.company_name or request.ticker or "Unknown",
        ticker=request.ticker,
        status="public" if request.ticker else "private",
        stock_data=stock_data,
        news_articles=news_articles,
        analyst_ratings=analyst_ratings,
        insider_transactions=insider_transactions,
        custom_instructions=custom_instructions,
    )

    return AnalyzeResponse(
        summary=summary,
        sentiment=sentiment,
        prompt=prompt,
        stock_data=stock_data,
    )
