from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime, timedelta, timezone
from ..database import get_db
from ..models import Company, Sync, CompanyTag
from ..models.sync import SyncStatus
from ..schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse
from ..schemas.tag import AssignTagsRequest
from .settings import get_setting

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=List[CompanyListResponse])
def list_companies(db: Session = Depends(get_db)):
    """List all companies with their latest sync summary and tags"""
    companies = db.query(Company).options(joinedload(Company.tags)).all()

    staleness_hours = float(get_setting(db, "staleness_hours") or "24")
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=staleness_hours)

    # Fetch latest sync per company in a single query
    max_sync_subq = (
        db.query(Sync.company_id, func.max(Sync.synced_at).label("max_synced_at"))
        .group_by(Sync.company_id)
        .subquery()
    )
    latest_syncs = (
        db.query(Sync)
        .join(
            max_sync_subq,
            (Sync.company_id == max_sync_subq.c.company_id)
            & (Sync.synced_at == max_sync_subq.c.max_synced_at),
        )
        .all()
    )
    latest_sync_map = {s.company_id: s for s in latest_syncs}

    # Companies currently syncing
    syncing_ids = {
        s.company_id
        for s in db.query(Sync.company_id)
        .filter(Sync.status == SyncStatus.syncing)
        .all()
    }

    result = []
    for company in companies:
        latest = latest_sync_map.get(company.id)

        # is_stale: no completed sync, or last completed sync is older than staleness_hours
        if latest is None or latest.status != SyncStatus.completed:
            is_stale = True
        else:
            synced_at = latest.synced_at
            if synced_at.tzinfo is None:
                synced_at = synced_at.replace(tzinfo=timezone.utc)
            is_stale = synced_at < stale_cutoff

        has_alert = (company.alert_above is not None) or (company.alert_below is not None)

        company_dict = {
            "id": company.id,
            "name": company.name,
            "ticker": company.ticker,
            "status": company.status,
            "description": company.description,
            "website": company.website,
            "industry": company.industry,
            "alert_above": company.alert_above,
            "alert_below": company.alert_below,
            "shares_owned": company.shares_owned,
            "created_at": company.created_at,
            "updated_at": company.updated_at,
            "tags": company.tags,
            "latest_sync": latest,
            "is_stale": is_stale,
            "is_syncing": company.id in syncing_ids,
            "has_alert": has_alert,
        }
        result.append(company_dict)

    return result


@router.post("", response_model=CompanyResponse, status_code=201)
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Create a new company"""
    db_company = Company(**company.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: str, db: Session = Depends(get_db)):
    """Get company detail"""
    company = (
        db.query(Company)
        .options(joinedload(Company.tags))
        .filter(Company.id == company_id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: str, company_update: CompanyUpdate, db: Session = Depends(get_db)
):
    """Update a company"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = company_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_company, key, value)

    db.commit()
    db.refresh(db_company)
    return db_company


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: str, db: Session = Depends(get_db)):
    """Delete a company and all associated syncs"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(db_company)
    db.commit()
    return None


@router.post("/{company_id}/tags", response_model=CompanyResponse)
def assign_tags(
    company_id: str, tags_request: AssignTagsRequest, db: Session = Depends(get_db)
):
    """Assign tags to a company"""
    db_company = (
        db.query(Company)
        .options(joinedload(Company.tags))
        .filter(Company.id == company_id)
        .first()
    )
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Remove existing tag associations
    db.query(CompanyTag).filter(CompanyTag.company_id == company_id).delete()

    # Add new tag associations
    for tag_id in tags_request.tag_ids:
        company_tag = CompanyTag(company_id=company_id, tag_id=tag_id)
        db.add(company_tag)

    db.commit()
    db.refresh(db_company)
    return db_company


@router.delete("/{company_id}/tags/{tag_id}", status_code=204)
def remove_tag(company_id: str, tag_id: str, db: Session = Depends(get_db)):
    """Remove a tag from a company"""
    db.query(CompanyTag).filter(
        CompanyTag.company_id == company_id, CompanyTag.tag_id == tag_id
    ).delete()
    db.commit()
    return None
