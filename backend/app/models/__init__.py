"""
SQLAlchemy models for database tables
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database.postgresql import Base


class UserRole(str, enum.Enum):
    """User role enum"""
    admin = "admin"
    developer = "developer"
    reviewer = "reviewer"
    compliance_officer = "compliance_officer"
    manager = "manager"


class PRStatus(str, enum.Enum):
    """Pull request status enum"""
    pending = "pending"
    analyzing = "analyzing"
    reviewed = "reviewed"
    approved = "approved"
    rejected = "rejected"


class AuditAction(str, enum.Enum):
    """Audit action enum"""
    create = "create"
    update = "update"
    delete = "delete"
    approve = "approve"
    reject = "reject"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.developer)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    projects = relationship("Project", back_populates="owner")
    pull_requests = relationship("PullRequest", back_populates="author")


class Project(Base):
    """Project model"""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    github_repo_url = Column(String(500), unique=True)
    github_webhook_secret = Column(String(255))
    language = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    pull_requests = relationship("PullRequest", back_populates="project")


class PullRequest(Base):
    """Pull Request model"""
    __tablename__ = "pull_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    github_pr_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(SQLEnum(PRStatus), nullable=False, default=PRStatus.pending)
    risk_score = Column(Float)
    branch_name = Column(String(255))
    commit_sha = Column(String(40))
    files_changed = Column(Integer, default=0)
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed_at = Column(DateTime(timezone=True))
    reviewed_at = Column(DateTime(timezone=True))
    
    # Relationships
    project = relationship("Project", back_populates="pull_requests")
    author = relationship("User", back_populates="pull_requests")
    review_result = relationship("ReviewResult", back_populates="pull_request", uselist=False)


class ReviewResult(Base):
    """Review Result model"""
    __tablename__ = "review_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pull_request_id = Column(UUID(as_uuid=True), ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False, unique=True)
    ai_suggestions = Column(JSONB)
    architectural_impact = Column(JSONB)
    security_issues = Column(JSONB)
    compliance_status = Column(JSONB)
    confidence_score = Column(Float)
    total_issues = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pull_request = relationship("PullRequest", back_populates="review_result")


class AuditLog(Base):
    """Audit Log model"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(SQLEnum(AuditAction), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    changes = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class ArchitecturalBaseline(Base):
    """Architectural Baseline model"""
    __tablename__ = "architectural_baselines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text)
    graph_snapshot = Column(JSONB, nullable=False)
    metrics = Column(JSONB)
    commit_sha = Column(String(40))
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TokenBlacklist(Base):
    """Token blacklist for logout"""
    __tablename__ = "token_blacklist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(500), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    blacklisted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
