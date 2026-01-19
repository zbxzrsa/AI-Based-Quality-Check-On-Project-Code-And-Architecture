"""
GDPR Compliance Module
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Project, PullRequest, ReviewResult
import zipfile
import io
import json


class GDPRComplianceService:
    """Service for GDPR compliance operations"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def export_user_data(self, user_id: str) -> bytes:
        """
        Export all user data (GDPR Article 15 - Right of Access)
        
        Args:
            user_id: User ID to export data for
            
        Returns:
            ZIP file bytes containing all user data
        """
        # Collect all user data
        user_data = await self._collect_user_data(user_id)
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add user profile
            zip_file.writestr(
                'profile.json',
                json.dumps(user_data['profile'], indent=2)
            )
            
            # Add projects
            zip_file.writestr(
                'projects.json',
                json.dumps(user_data['projects'], indent=2)
            )
            
            # Add pull requests
            zip_file.writestr(
                'pull_requests.json',
                json.dumps(user_data['pull_requests'], indent=2)
            )
            
            # Add audit logs
            zip_file.writestr(
                'audit_logs.json',
                json.dumps(user_data['audit_logs'], indent=2)
            )
            
            # Add data processing consent
            zip_file.writestr(
                'consent_history.json',
                json.dumps(user_data['consent'], indent=2)
            )
            
            # Add README
            readme = self._generate_export_readme(user_data)
            zip_file.writestr('README.txt', readme)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    async def delete_user_data(self, user_id: str, reason: str = "user_request") -> Dict[str, Any]:
        """
        Delete all user data (GDPR Article 17 - Right to Erasure)
        
        Args:
            user_id: User ID to delete
            reason: Reason for deletion
            
        Returns:
            Deletion report
        """
        from sqlalchemy import delete
        
        deletion_report = {
            "user_id": user_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "items_deleted": {},
        }
        
        # Log deletion request (before deleting)
        await self._log_deletion_request(user_id, reason)
        
        # Delete review results
        result = await self.db.execute(
            delete(ReviewResult).where(ReviewResult.user_id == user_id)
        )
        deletion_report["items_deleted"]["review_results"] = result.rowcount
        
        # Delete pull requests
        result = await self.db.execute(
            delete(PullRequest).where(PullRequest.created_by == user_id)
        )
        deletion_report["items_deleted"]["pull_requests"] = result.rowcount
        
        # Transfer or delete projects
        result = await self.db.execute(
            delete(Project).where(Project.owner_id == user_id)
        )
        deletion_report["items_deleted"]["projects"] = result.rowcount
        
        # Anonymize audit logs (don't delete for compliance)
        await self._anonymize_audit_logs(user_id)
        deletion_report["items_deleted"]["audit_logs"] = "anonymized"
        
        # Delete user account
        result = await self.db.execute(
            delete(User).where(User.id == user_id)
        )
        deletion_report["items_deleted"]["user_account"] = result.rowcount
        
        await self.db.commit()
        
        return deletion_report
    
    async def anonymize_data(self, user_id: str) -> Dict[str, Any]:
        """
        Anonymize user data instead of deletion
        (for cases where deletion would break data integrity)
        
        Args:
            user_id: User ID to anonymize
            
        Returns:
            Anonymization report
        """
        from sqlalchemy import update
        
        # Generate anonymous identifier
        anonymous_email = f"deleted_user_{user_id[:8]}@deleted.local"
        
        # Anonymize user profile
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                email=anonymous_email,
                full_name="Deleted User",
                hashed_password="DELETED",
                is_active=False,
                deleted_at=datetime.now(timezone.utc),
            )
        )
        
        # Anonymize audit logs
        await self._anonymize_audit_logs(user_id)
        
        await self.db.commit()
        
        return {
            "user_id": user_id,
            "anonymized_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        }
    
    async def update_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        purpose: str,
    ) -> Dict[str, Any]:
        """
        Record user consent (GDPR Article 7)
        
        Args:
            user_id: User ID
            consent_type: Type of consent (marketing, analytics, etc.)
            granted: Whether consent was granted
            purpose: Purpose of data processing
            
        Returns:
            Consent record
        """
        # Store in consent table (would need to create this table)
        consent_record = {
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "purpose": purpose,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip_address": None,  # Would get from request
        }
        
        # Log consent change
        await self._log_consent_change(user_id, consent_type, granted)
        
        return consent_record
    
    async def check_data_retention(self) -> List[Dict[str, Any]]:
        """
        Check for data that exceeds retention period
        
        Returns:
            List of data items to be deleted
        """
        from sqlalchemy import select, and_
        
        items_to_delete = []
        
        # Check old audit logs (default: 7 years)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=2555)
        
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.timestamp < cutoff_date)
            .limit(100)
        )
        old_logs = result.scalars().all()
        
        for log in old_logs:
            items_to_delete.append({
                "type": "audit_log",
                "id": str(log.id),
                "age_days": (datetime.now(timezone.utc) - log.timestamp).days,
                "action": "archive_or_delete",
            })
        
        # Check inactive users (e.g., not logged in for 2 years)
        inactive_cutoff = datetime.now(timezone.utc) - timedelta(days=730)
        
        result = await self.db.execute(
            select(User)
            .where(
                and_(
                    User.last_login < inactive_cutoff,
                    User.is_active == True
                )
            )
        )
        inactive_users = result.scalars().all()
        
        for user in inactive_users:
            items_to_delete.append({
                "type": "inactive_user",
                "id": str(user.id),
                "email": user.email,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "action": "notify_or_anonymize",
            })
        
        return items_to_delete
    
    async def _collect_user_data(self, user_id: str) -> Dict[str, Any]:
        """Collect all data for a user"""
        from sqlalchemy import select
        
        # User profile
        user = await self.db.get(User, user_id)
        profile = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
        }
        
        # Projects
        result = await self.db.execute(
            select(Project).where(Project.owner_id == user_id)
        )
        projects = [
            {
                "id": str(p.id),
                "name": p.name,
                "created_at": p.created_at.isoformat(),
            }
            for p in result.scalars().all()
        ]
        
        # Pull requests (simplified)
        pull_requests = []  # Would query from database
        
        # Audit logs
        audit_logs = []  # Would query from audit_logs table
        
        # Consent history
        consent = []  # Would query from consent table
        
        return {
            "profile": profile,
            "projects": projects,
            "pull_requests": pull_requests,
            "audit_logs": audit_logs,
            "consent": consent,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _generate_export_readme(self, user_data: Dict[str, Any]) -> str:
        """Generate README for data export"""
        return f"""
AI Code Review Platform - Personal Data Export
===============================================

Export Date: {user_data['exported_at']}
User ID: {user_data['profile']['id']}
Email: {user_data['profile']['email']}

This archive contains all your personal data stored in our system,
as required by GDPR Article 15 (Right of Access).

Contents:
---------
- profile.json: Your user profile information
- projects.json: Projects you own or collaborate on
- pull_requests.json: Pull requests you've created or reviewed
- audit_logs.json: Activity logs related to your account
- consent_history.json: History of your data processing consents

Data Format:
-----------
All files are in JSON format for easy parsing and portability.

Rights:
-------
Under GDPR, you have the right to:
- Request correction of inaccurate data (Article 16)
- Request deletion of your data (Article 17)
- Object to data processing (Article 21)
- Data portability (Article 20)

Contact:
--------
For questions or to exercise your rights, contact: privacy@your-domain.com
"""
    
    async def _anonymize_audit_logs(self, user_id: str):
        """Anonymize user info in audit logs while preserving records"""
        from sqlalchemy import update
        
        await self.db.execute(
            update(AuditLog)
            .where(AuditLog.user_id == user_id)
            .values(
                user_email="anonymized@deleted.local",
                ip_address="0.0.0.0",
                user_agent="DELETED",
            )
        )
    
    async def _log_deletion_request(self, user_id: str, reason: str):
        """Log deletion request before deleting"""
        # Would use AuditTrailService here
        pass
    
    async def _log_consent_change(self, user_id: str, consent_type: str, granted: bool):
        """Log consent changes"""
        # Would use AuditTrailService here
        pass
