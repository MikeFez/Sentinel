from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..database import get_db
from ..models import Setting
from ..schemas.setting import SettingResponse, SettingUpdate
from ..services.llm_service import LLMService
from ..config import settings as app_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTING_DEFAULTS: dict[str, str] = {
    "llm_base_url": app_settings.llm_base_url,
    "llm_model": app_settings.llm_model,
    "news_count": str(app_settings.news_article_count),
    "auto_refresh_enabled": str(app_settings.auto_refresh_enabled).lower(),
    "auto_refresh_hours": str(app_settings.auto_refresh_hours),
    "staleness_hours": str(app_settings.staleness_hours),
    "ai_prompt_instructions": app_settings.ai_prompt_instructions,
}


def get_setting(db: Session, key: str) -> str:
    """Get a setting value by key, falling back to SETTING_DEFAULTS."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else SETTING_DEFAULTS.get(key, "")


def set_setting(db: Session, key: str, value: str):
    """Set a setting value"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


@router.get("", response_model=Dict[str, str])
def get_all_settings(db: Session = Depends(get_db)):
    """Get all settings"""
    result = {s.key: s.value for s in db.query(Setting).all()}
    for key, default_value in SETTING_DEFAULTS.items():
        if key not in result:
            result[key] = default_value
    return result


@router.put("", response_model=Dict[str, str])
def update_settings(updates: Dict[str, str], db: Session = Depends(get_db)):
    """Update multiple settings"""
    for key, value in updates.items():
        set_setting(db, key, value)

    return get_all_settings(db)


@router.get("/llm/models", response_model=List[str])
async def get_llm_models(db: Session = Depends(get_db)):
    """Get available LLM models"""
    llm_base_url = get_setting(db, "llm_base_url")

    # Create a temporary LLM service to query models
    llm_service = LLMService(llm_base_url, "")

    models = await llm_service.list_models()

    if not models:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to reach the LLM endpoint at {llm_base_url}. Check the URL (it should end in /v1) and that the server is running.",
        )

    return models


@router.get("/llm/health")
async def check_llm_health(db: Session = Depends(get_db)):
    """Check if the LLM endpoint is accessible"""
    llm_base_url = get_setting(db, "llm_base_url")

    llm_service = LLMService(llm_base_url, "")
    is_healthy = await llm_service.check_health()

    return {
        "healthy": is_healthy,
        "url": llm_base_url,
    }
