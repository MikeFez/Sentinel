from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings as app_settings
from ..routers.settings import get_setting
from ..services import discover_service

router = APIRouter(prefix="/api/discover", tags=["discover"])


class DiscoverRequest(BaseModel):
    theme: str


@router.post("")
async def start_discover(
    request: DiscoverRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Start a domain discovery session.
    Returns a session object immediately; the actual work runs in the background.
    Poll GET /api/discover/{session_id} for progress and results.
    """
    if not request.theme.strip():
        raise HTTPException(status_code=400, detail="Theme cannot be empty")

    ollama_url = get_setting(db, "ollama_url") or app_settings.ollama_url
    ollama_model = get_setting(db, "ollama_model") or app_settings.ollama_model
    custom_instructions = get_setting(db, "ai_prompt_instructions") or app_settings.ai_prompt_instructions

    session = discover_service.create_session(request.theme.strip())

    background_tasks.add_task(
        discover_service.run_discover,
        session["session_id"],
        ollama_url,
        ollama_model,
        app_settings.finnhub_api_key,
        custom_instructions,
    )

    return session


@router.get("/{session_id}")
async def get_discover_session(session_id: str):
    """Poll for discovery progress and results."""
    session = discover_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/analyze/{ticker}")
async def analyze_discover_company(
    session_id: str,
    ticker: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger on-demand sentiment analysis for a single company in a discover session."""
    session = discover_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    company = next((c for c in session["companies"] if c["ticker"] == ticker), None)
    if not company:
        raise HTTPException(status_code=404, detail="Ticker not in session")

    if company["status"] == "analyzing":
        return {"message": "Already analyzing"}

    ollama_url = get_setting(db, "ollama_url") or app_settings.ollama_url
    ollama_model = get_setting(db, "ollama_model") or app_settings.ollama_model
    custom_instructions = get_setting(db, "ai_prompt_instructions") or app_settings.ai_prompt_instructions

    company["status"] = "analyzing"

    background_tasks.add_task(
        discover_service.analyze_one,
        session_id,
        ticker,
        ollama_url,
        ollama_model,
        app_settings.finnhub_api_key,
        custom_instructions,
    )

    return {"message": "Analysis started"}
