"""
User model for the Enterprise RBAC Authentication System.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .enums import Role


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class User(Base):
    """User entity with authentication and role information."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SQLEnum(Role, values_callable=lambda x: [e.value.lower() for e in x]), nullable=False, default=Role.USER
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    github_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    owned_projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="owner", foreign_keys="Project.owner_id"
    )
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user", cascade="all, delete-orphan")  # noqa: F821
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")  # noqa: F821
    project_accesses: Mapped[list["ProjectAccess"]] = relationship(  # noqa: F821
        "ProjectAccess", back_populates="user", foreign_keys="ProjectAccess.user_id", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
