"""
Project and ProjectAccess models for the Enterprise RBAC Authentication System.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .user import Base


class Project(Base):
    """Project entity representing a code asset or workspace."""
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    access_grants: Mapped[list["ProjectAccess"]] = relationship("ProjectAccess", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, owner_id={self.owner_id})>"


class ProjectAccess(Base):
    """ProjectAccess entity representing explicit access grants to projects."""
    __tablename__ = "project_accesses"
    
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    granted_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="access_grants")
    user: Mapped["User"] = relationship("User", back_populates="project_accesses", foreign_keys=[user_id])
    granter: Mapped["User"] = relationship("User", foreign_keys=[granted_by])
    
    def __repr__(self) -> str:
        return f"<ProjectAccess(project_id={self.project_id}, user_id={self.user_id})>"
