"""Export and import companies, tags and settings as JSON (no sync history)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Company, Setting, Tag
from ..models.company import CompanyStatus
from .settings import SETTING_DEFAULTS, set_setting

router = APIRouter(prefix="/api", tags=["transfer"])

FORMAT = "sentinel-export"
VERSION = 1
COMPANY_FIELDS = ("name", "ticker", "status", "description", "website", "shares_owned", "alert_above", "alert_below")


class ExportTag(BaseModel):
    name: str
    color: str = "#6366f1"


class ExportCompany(BaseModel):
    name: str
    ticker: Optional[str] = None
    status: CompanyStatus = CompanyStatus.public
    description: Optional[str] = None
    website: Optional[str] = None
    shares_owned: Optional[float] = None
    alert_above: Optional[float] = None
    alert_below: Optional[float] = None
    tags: List[str] = []


class ExportFile(BaseModel):
    format: str
    version: int
    exported_at: Optional[str] = None
    tags: List[ExportTag] = []
    companies: List[ExportCompany] = []
    settings: Dict[str, str] = {}


@router.get("/export")
def export_data(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Everything you've set up: companies (with positions, alerts, notes, tags), tags and settings."""
    companies = db.query(Company).options(joinedload(Company.tags)).order_by(Company.name).all()
    return {
        "format": FORMAT,
        "version": VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tags": [{"name": t.name, "color": t.color} for t in db.query(Tag).order_by(Tag.name)],
        "companies": [
            {
                **{f: getattr(c, f) for f in COMPANY_FIELDS},
                "status": c.status.value if hasattr(c.status, "value") else c.status,
                "tags": sorted(t.name for t in c.tags),
            }
            for c in companies
        ],
        "settings": {s.key: s.value for s in db.query(Setting) if s.key in SETTING_DEFAULTS},
    }


class ImportRequest(BaseModel):
    data: ExportFile
    include_settings: bool = True
    dry_run: bool = False


def _find(db: Session, c: ExportCompany) -> Optional[Company]:
    """Match an imported company by ticker, else by name (case-insensitive)."""
    if c.ticker:
        found = db.query(Company).filter(Company.ticker.ilike(c.ticker.strip())).first()
        if found:
            return found
    return db.query(Company).filter(Company.name.ilike(c.name.strip())).first()


@router.post("/import")
def import_data(req: ImportRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Merge an export into this instance: existing companies (same ticker or name) are updated,
    others are added; nothing is deleted. With dry_run, report what would change without saving."""
    data = req.data
    if data.format != FORMAT or data.version > VERSION:
        raise HTTPException(status_code=400, detail="This isn't a Sentinel export file (or it's from a newer version).")

    tags = {t.name.lower(): t for t in db.query(Tag)}
    tags_created = 0
    for t in data.tags:
        if t.name.lower() not in tags:
            tags[t.name.lower()] = Tag(name=t.name, color=t.color)
            db.add(tags[t.name.lower()])
            tags_created += 1
    db.flush()

    created, updated = [], []
    for item in data.companies:
        company = _find(db, item)
        fields = item.model_dump(include=set(COMPANY_FIELDS))
        if fields.get("ticker"):
            fields["ticker"] = fields["ticker"].strip().upper()
        if company is None:
            company = Company(**fields)
            db.add(company)
            created.append(item.name)
        else:
            changed = any(getattr(company, k) != v for k, v in fields.items())
            for k, v in fields.items():
                setattr(company, k, v)
            if changed:
                updated.append(item.name)
        wanted = []
        for name in item.tags:
            tag = tags.get(name.lower())
            if tag is None:
                tag = tags[name.lower()] = Tag(name=name)
                db.add(tag)
                tags_created += 1
            wanted.append(tag)
        if {t.name for t in company.tags} != {t.name for t in wanted}:
            company.tags = wanted
            if item.name not in created and item.name not in updated:
                updated.append(item.name)

    settings_changed = 0
    if req.include_settings:
        for key, value in data.settings.items():
            if key in SETTING_DEFAULTS:
                current = db.query(Setting).filter(Setting.key == key).first()
                if (current.value if current else SETTING_DEFAULTS[key]) != value:
                    settings_changed += 1
                    if not req.dry_run:
                        set_setting(db, key, value)

    summary = {"created": created, "updated": updated, "tags_created": tags_created, "settings_changed": settings_changed}
    if req.dry_run:
        db.rollback()
    else:
        db.commit()
    return summary
