from pydantic import BaseModel
from typing import List, Optional


class TagBase(BaseModel):
    name: str
    color: str = "#6366f1"


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class TagResponse(TagBase):
    id: str

    class Config:
        from_attributes = True


class AssignTagsRequest(BaseModel):
    tag_ids: List[str]
