from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ResearchItem

router = APIRouter(prefix="/api/research", tags=["research"])


def _preview(item: ResearchItem) -> dict:
    """The few fields a history list needs, without the whole result."""
    d = item.data or {}
    if item.kind == "analysis":
        r = d.get("result") or {}
        return {"sentiment": r.get("sentiment"), "summary": (r.get("summary") or "")[:160]}
    companies = d.get("companies") or []
    return {
        "status": d.get("status"),
        "companies": len(companies),
        "analyzed": sum(1 for c in companies if c.get("sentiment")),
    }


@router.get("")
def list_research(kind: Optional[str] = None, limit: int = Query(30, le=200), db: Session = Depends(get_db)):
    """Saved analyses and discoveries, newest first."""
    q = db.query(ResearchItem)
    if kind:
        q = q.filter(ResearchItem.kind == kind)
    return [
        {"id": i.id, "kind": i.kind, "title": i.title, "created_at": i.created_at, "updated_at": i.updated_at, **_preview(i)}
        for i in q.order_by(ResearchItem.created_at.desc()).limit(limit)
    ]


@router.get("/{item_id}")
def get_research(item_id: str, db: Session = Depends(get_db)):
    item = db.get(ResearchItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": item.id, "kind": item.kind, "title": item.title, "created_at": item.created_at, "data": item.data}


@router.delete("/{item_id}", status_code=204)
def delete_research(item_id: str, db: Session = Depends(get_db)):
    item = db.get(ResearchItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
