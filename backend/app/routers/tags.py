from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Tag
from ..schemas.tag import TagCreate, TagUpdate, TagResponse

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=List[TagResponse])
def list_tags(db: Session = Depends(get_db)):
    """List all tags"""
    return db.query(Tag).all()


@router.post("", response_model=TagResponse, status_code=201)
def create_tag(tag: TagCreate, db: Session = Depends(get_db)):
    """Create a new tag"""
    # Check if tag with same name already exists
    existing_tag = db.query(Tag).filter(Tag.name == tag.name).first()
    if existing_tag:
        raise HTTPException(status_code=400, detail="Tag with this name already exists")

    db_tag = Tag(**tag.model_dump())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(tag_id: str, tag_update: TagUpdate, db: Session = Depends(get_db)):
    """Update a tag"""
    db_tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    update_data = tag_update.model_dump(exclude_unset=True)

    # Check if name is being updated and if it conflicts
    if "name" in update_data:
        existing_tag = db.query(Tag).filter(Tag.name == update_data["name"]).first()
        if existing_tag and existing_tag.id != tag_id:
            raise HTTPException(
                status_code=400, detail="Tag with this name already exists"
            )

    for key, value in update_data.items():
        setattr(db_tag, key, value)

    db.commit()
    db.refresh(db_tag)
    return db_tag


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: str, db: Session = Depends(get_db)):
    """Delete a tag"""
    db_tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.delete(db_tag)
    db.commit()
    return None
