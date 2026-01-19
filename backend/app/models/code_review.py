"""
Database models for code review and architecture analysis
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Enum,
    Boolean,
    Table,
    func,
    event,
    DDL
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, backref

from app.database.postgresql import Base


class PRStatus(str, PyEnum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


class ReviewStatus(str, PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PullRequest(Base):
    """Pull request model"""
    __tablename__ = "pull_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    github_pr_number = Column(Integer, nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    branch_name = Column(String(256), nullable=True)
    commit_sha = Column(String(64), nullable=True)
    files_changed = Column(Integer, default=0)
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)
    status = Column(Enum(PRStatus), default=PRStatus.PENDING, nullable=False)
    risk_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    merged_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="pull_requests")
    reviews = relationship("CodeReview", back_populates="pull_request", cascade="all, delete-orphan")
    architecture_analyses = relationship("ArchitectureAnalysis", back_populates="pull_request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PullRequest {self.github_pr_number}: {self.title}>"


class CodeReview(Base):
    """Code review model"""
    __tablename__ = "code_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    pull_request_id = Column(UUID(as_uuid=True), ForeignKey("pull_requests.id"), nullable=False)
    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False)
    summary = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    pull_request = relationship("PullRequest", back_populates="reviews")
    comments = relationship("ReviewComment", back_populates="review", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CodeReview {self.id} for PR {self.pull_request_id}>"


class ReviewComment(Base):
    """Code review comment model"""
    __tablename__ = "review_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    review_id = Column(UUID(as_uuid=True), ForeignKey("code_reviews.id"), nullable=False)
    file_path = Column(String(1024), nullable=False)
    line_number = Column(Integer, nullable=True)
    message = Column(Text, nullable=False)
    severity = Column(String(32), nullable=False)  # info, low, medium, high, critical
    category = Column(String(64), nullable=True)  # security, performance, maintainability, etc.
    rule_id = Column(String(128), nullable=True)
    rule_name = Column(String(256), nullable=True)
    suggested_fix = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    review = relationship("CodeReview", back_populates="comments")

    def __repr__(self):
        return f"<ReviewComment {self.id} for review {self.review_id}>"


class ArchitectureAnalysis(Base):
    """Architecture analysis model"""
    __tablename__ = "architecture_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    pull_request_id = Column(UUID(as_uuid=True), ForeignKey("pull_requests.id"), nullable=False)
    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False)
    summary = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    pull_request = relationship("PullRequest", back_populates="architecture_analyses")
    violations = relationship("ArchitectureViolation", back_populates="analysis", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ArchitectureAnalysis {self.id} for PR {self.pull_request_id}>"


class ArchitectureViolation(Base):
    """Architecture violation model"""
    __tablename__ = "architecture_violations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("architecture_analyses.id"), nullable=False)
    type = Column(String(64), nullable=False)  # circular_dependency, dependency_violation, etc.
    component = Column(String(256), nullable=False)
    related_component = Column(String(256), nullable=True)
    message = Column(Text, nullable=False)
    severity = Column(String(32), nullable=False)  # info, low, medium, high, critical
    file_path = Column(String(1024), nullable=True)
    line_number = Column(Integer, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    rule_id = Column(String(128), nullable=True)
    rule_name = Column(String(256), nullable=True)

    # Relationships
    analysis = relationship("ArchitectureAnalysis", back_populates="violations")

    def __repr__(self):
        return f"<ArchitectureViolation {self.id} in {self.component}: {self.message}>"
