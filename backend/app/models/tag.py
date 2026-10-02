from sqlalchemy import Column, String, Table, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from ..database import Base


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    color = Column(String, nullable=False, default="#6366f1")

    # Relationships
    companies = relationship("Company", secondary="company_tags", back_populates="tags")


class CompanyTag(Base):
    __tablename__ = "company_tags"

    company_id = Column(String, ForeignKey("companies.id"), primary_key=True)
    tag_id = Column(String, ForeignKey("tags.id"), primary_key=True)
