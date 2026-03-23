"""
SQLAlchemy models for library management
"""
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Boolean,
    Enum,
    func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database.postgresql import Base


class RegistryType(str, PyEnum):
    """Package registry type enum"""
    NPM = "npm"
    PYPI = "pypi"
    MAVEN = "maven"


class ProjectContext(str, PyEnum):
    """Project context enum"""
    BACKEND = "backend"
    FRONTEND = "frontend"
    SERVICES = "services"


class Library(Base):
    """Library model for tracking installed libraries"""
    __tablename__ = "libraries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    registry_type = Column(Enum(RegistryType), nullable=False)
    project_context = Column(Enum(ProjectContext), nullable=False, index=True)
    description = Column(Text, nullable=True)
    license = Column(String(100), nullable=True)
    installed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    installed_by = Column(String(255), nullable=False)
    uri = Column(Text, nullable=False)
    # Use 'library_metadata' to avoid conflict with SQLAlchemy's reserved 'metadata' attribute
    library_metadata = Column("metadata", JSONB, nullable=True)

    # Relationships
    dependencies = relationship(
        "LibraryDependency",
        back_populates="library",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Library {self.name}@{self.version} ({self.registry_type.value})>"


class LibraryDependency(Base):
    """Library dependency model for tracking library dependencies"""
    __tablename__ = "library_dependencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    library_id = Column(
        Integer,
        ForeignKey("libraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    dependency_name = Column(String(255), nullable=False, index=True)
    dependency_version = Column(String(50), nullable=False)
    is_direct = Column(Boolean, server_default="true", nullable=False)

    # Relationships
    library = relationship("Library", back_populates="dependencies")

    def __repr__(self):
        return f"<LibraryDependency {self.dependency_name}@{self.dependency_version}>"
