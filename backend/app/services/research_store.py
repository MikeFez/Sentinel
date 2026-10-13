"""Saved Research results (research_items): ad-hoc analyses and theme discoveries.

Each call uses its own session, because discoveries are saved from background tasks. Saving never
raises: a failed save loses history, not the result the person is looking at.
"""
import copy
import logging
from datetime import datetime, timezone
from typing import Optional

from ..database import SessionLocal
from ..models import ResearchItem

logger = logging.getLogger(__name__)


def save(kind: str, title: str, data: dict, item_id: Optional[str] = None) -> Optional[str]:
    """Insert, or replace the item with this id. Returns the id (None if saving failed)."""
    db = SessionLocal()
    try:
        item = db.get(ResearchItem, item_id) if item_id else None
        if item is None:
            item = ResearchItem(kind=kind, title=title[:200], **({"id": item_id} if item_id else {}))
            db.add(item)
        item.data = copy.deepcopy(data)  # a new object, so the JSON column registers the change
        item.updated_at = datetime.now(timezone.utc)
        db.commit()
        return item.id
    except Exception:
        logger.exception(f"Could not save {kind} research")
        db.rollback()
        return None
    finally:
        db.close()


def get(item_id: str) -> Optional[ResearchItem]:
    db = SessionLocal()
    try:
        item = db.get(ResearchItem, item_id)
        if item is not None:
            db.expunge(item)
        return item
    finally:
        db.close()
