"""
RBAC service for role and permission management.
"""
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, Project, ProjectAccess, Role, Permission, ROLE_PERMISSIONS


class RBACService:
    """Service for handling role-based access control operations."""
    
    @staticmethod
    async def has_permission(db: AsyncSession, user_id: str, permission: Permission) -> bool:
        """
        Check if a user has a specific permission based on their role.
        
        Args:
            db: Async database session
            user_id: User's unique identifier
            permission: Permission to check
            
        Returns:
            True if user has the permission, False otherwise
        """
        from sqlalchemy import select
        from uuid import UUID
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Convert user_id to UUID if it's a string
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            logger.info(f"Checking permission {permission} for user {user_uuid}")
            
            # Async query
            result = await db.execute(select(User).filter(User.id == user_uuid))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_uuid} not found")
                return False
                
            if not user.is_active:
                logger.warning(f"User {user_uuid} is not active")
                return False
            
            # Get permissions for user's role
            role_permissions = RBACService.get_role_permissions(user.role)
            logger.info(f"User {user_uuid} has role {user.role} with permissions: {role_permissions}")
            
            # Check if permission is in the role's permissions
            has_perm = permission in role_permissions
            logger.info(f"User {user_uuid} has permission {permission}: {has_perm}")
            return has_perm
            
        except Exception as e:
            logger.error(f"Error checking permission: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_role_permissions(role: Role) -> list[Permission]:
        """
        Get all permissions for a specific role.
        
        Args:
            role: Role to get permissions for
            
        Returns:
            List of permissions for the role
        """
        return ROLE_PERMISSIONS.get(role, [])

    
    @staticmethod
    async def can_access_project(db: DBSession, user_id: str, project_id: str, permission: Permission) -> bool:
        """
        Check if a user can access a specific project with a given permission.
        
        Admins can access all projects. For other users, they must either:
        - Own the project (for any permission)
        - Have an explicit access grant (for VIEW_PROJECT permission only)
        
        Args:
            db: Database session
            user_id: User's unique identifier (string)
            project_id: Project's unique identifier (string)
            permission: Permission being requested
            
        Returns:
            True if user can access the project, False otherwise
        """
        from sqlalchemy import select
        
        try:
            # Get user from database (IDs are stored as strings)
            result = await db.execute(select(User).filter(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                return False
            
            # Admin bypass: Admins can access all projects
            if user.role == Role.ADMIN:
                return True
            
            # Get project from database
            result = await db.execute(select(Project).filter(Project.id == project_id))
            project = result.scalar_one_or_none()
            
            if not project:
                return False
            
            # Check if user is the project owner
            if project.owner_id == user_id:
                return True
            
            # For non-owners, check if they have an explicit access grant
            # Access grants only allow VIEW_PROJECT permission
            if permission == Permission.VIEW_PROJECT:
                result = await db.execute(
                    select(ProjectAccess).filter(
                        ProjectAccess.project_id == project_id,
                        ProjectAccess.user_id == user_id
                    )
                )
                access_grant = result.scalar_one_or_none()
                
                if access_grant:
                    return True
            
            # No access
            return False
            
        except Exception as e:
            # Log error but don't expose details
            logger.info("Error in can_access_project: {type(e).__name__}: {str(e)}")
            return False
    
    @staticmethod
    def grant_project_access(db: DBSession, project_id: str, user_id: str, 
                            granted_by: str) -> bool:
        """
        Grant a user access to a project.
        
        Only admins or project owners can grant access.
        
        Args:
            db: Database session
            project_id: Project's unique identifier
            user_id: User to grant access to
            granted_by: User ID of the person granting access
            
        Returns:
            True if access was granted successfully, False otherwise
        """
        try:
            # Verify the granter has permission to grant access
            granter = db.query(User).filter(User.id == granted_by).first()
            if not granter:
                return False
            
            # Get the project
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return False
            
            # Only admins or project owners can grant access
            if granter.role != Role.ADMIN and project.owner_id != granted_by:
                return False
            
            # Check if access grant already exists
            existing_grant = db.query(ProjectAccess).filter(
                ProjectAccess.project_id == project_id,
                ProjectAccess.user_id == user_id
            ).first()
            
            if existing_grant:
                # Access already granted
                return True
            
            # Create new access grant
            access_grant = ProjectAccess(
                project_id=project_id,
                user_id=user_id,
                granted_by=granted_by
            )
            db.add(access_grant)
            db.commit()
            
            return True
            
        except Exception:
            db.rollback()
            return False
    
    @staticmethod
    def revoke_project_access(db: DBSession, project_id: str, user_id: str, 
                             revoked_by: str) -> bool:
        """
        Revoke a user's access to a project.
        
        Only admins or project owners can revoke access.
        
        Args:
            db: Database session
            project_id: Project's unique identifier
            user_id: User to revoke access from
            revoked_by: User ID of the person revoking access
            
        Returns:
            True if access was revoked successfully, False otherwise
        """
        try:
            # Verify the revoker has permission to revoke access
            revoker = db.query(User).filter(User.id == revoked_by).first()
            if not revoker:
                return False
            
            # Get the project
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return False
            
            # Only admins or project owners can revoke access
            if revoker.role != Role.ADMIN and project.owner_id != revoked_by:
                return False
            
            # Find and delete the access grant
            access_grant = db.query(ProjectAccess).filter(
                ProjectAccess.project_id == project_id,
                ProjectAccess.user_id == user_id
            ).first()
            
            if access_grant:
                db.delete(access_grant)
                db.commit()
            
            return True
            
        except Exception:
            db.rollback()
            return False

    
    @staticmethod
    def validate_role(role: str) -> bool:
        """
        Validate that a role is one of the valid roles.
        
        Args:
            role: Role string to validate
            
        Returns:
            True if role is valid, False otherwise
        """
        try:
            # Try to convert to Role enum
            Role(role)
            return True
        except (ValueError, KeyError):
            return False
    
    @staticmethod
    def assign_role(db: DBSession, user_id: str, new_role: Role, 
                   assigned_by: str) -> bool:
        """
        Assign a new role to a user.
        
        This function updates the user's role and immediately applies the new permissions.
        Active sessions will reflect the new role on their next permission check.
        
        Args:
            db: Database session
            user_id: User's unique identifier
            new_role: New role to assign
            assigned_by: User ID of the person assigning the role (must be admin)
            
        Returns:
            True if role was assigned successfully, False otherwise
        """
        try:
            # Verify the assigner is an admin
            assigner = db.query(User).filter(User.id == assigned_by).first()
            if not assigner or assigner.role != Role.ADMIN:
                return False
            
            # Get the user to update
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Update the user's role
            user.role = new_role
            db.commit()
            
            # Note: Active sessions will automatically reflect the new role
            # because permission checks query the user's current role from the database
            # No need to invalidate sessions
            
            return True
            
        except Exception:
            db.rollback()
            return False
