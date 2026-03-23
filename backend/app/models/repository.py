"""
Repository database model
"""
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database.postgresql import Base


class RepositoryStatus(str, enum.Enum):
    """Repository processing status"""
    PENDING = "pending"
    VALIDATING = "validating"
    CLONING = "cloning"
    ANALYZING = "analyzing"
    ACTIVE = "active"
    FAILED = "failed"
    ARCHIVED = "archived"


class Repository(Base):
    """Repository dependency model"""
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_url = Column(String(500), nullable=False)
    owner = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    branch = Column(String(255), nullable=False, default="main")
    version = Column(String(100), nullable=True)
    status = Column(
        SQLEnum(RepositoryStatus),
        nullable=False,
        default=RepositoryStatus.PENDING,
        index=True
    )
    description = Column(String(500), nullable=True)
    auto_update = Column(Boolean, default=False)
    last_synced = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Store additional metadata as JSON
    metadata = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    # creator = relationship("User", back_populates="repositories")

    def __repr__(self):
        return f"<Repository {self.owner}/{self.name}@{self.branch}>"
