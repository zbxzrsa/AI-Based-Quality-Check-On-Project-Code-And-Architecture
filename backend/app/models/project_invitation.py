"""
Project invitation models for invitation-based access control
"""
import enum
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.postgresql import Base


class InvitationStatus(str, enum.Enum):
    """Invitation status enum"""
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"


class ProjectRole(str, enum.Enum):
    """Project role enum for invitation-based system"""
    owner = "owner"
    maintainer = "maintainer"
    member = "member"


class ProjectInvitation(Base):
    """Project invitation model"""
    __tablename__ = "project_invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    inviter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invitee_email = Column(String(255), nullable=False, index=True)
    invitee_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    invitation_token = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(String(50), nullable=False, default=ProjectRole.member.value)
    status = Column(String(20), nullable=False, default=InvitationStatus.pending.value, index=True)
    message = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[inviter_id], back_populates="sent_invitations")
    invitee = relationship("User", foreign_keys=[invitee_id], back_populates="received_invitations")
    
    @classmethod
    def create_invitation_token(cls) -> str:
        """Generate a secure invitation token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @classmethod
    def create_with_expiry(cls, project_id: uuid.UUID, inviter_id: uuid.UUID, 
                          invitee_email: str, role: str = ProjectRole.member.value,
                          message: str = None, days_valid: int = 7) -> 'ProjectInvitation':
        """Create a new invitation with expiry"""
        expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        invitation_token = cls.create_invitation_token()
        
        return cls(
            project_id=project_id,
            inviter_id=inviter_id,
            invitee_email=invitee_email,
            invitation_token=invitation_token,
            role=role,
            message=message,
            expires_at=expires_at
        )
    
    def is_expired(self) -> bool:
        """Check if invitation is expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def can_be_accepted(self) -> bool:
        """Check if invitation can be accepted"""
        return (self.status == InvitationStatus.pending.value and 
                not self.is_expired())


class ProjectMember(Base):
    """Project member model for tracking project access"""
    __tablename__ = "project_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default=ProjectRole.member.value, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")
    
    __table_args__ = (
        # Ensure unique project-user combination
        {'sqlite_autoincrement': True},
    )