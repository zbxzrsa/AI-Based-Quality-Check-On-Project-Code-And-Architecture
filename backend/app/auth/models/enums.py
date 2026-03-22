"""
Enums for the Enterprise RBAC Authentication System.
"""

# Import consolidated enums from shared package
from app.shared.enums import Permission, Role

# Role-Permission Mapping
_USER_PERMISSIONS = [
    Permission.CREATE_PROJECT,
    Permission.UPDATE_PROJECT,
    Permission.VIEW_PROJECT,
    Permission.VIEW_CONFIG,
    Permission.EXPORT_REPORT,
]

ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.ADMIN: [
        Permission.CREATE_USER,
        Permission.DELETE_USER,
        Permission.UPDATE_USER,
        Permission.VIEW_USER,
        Permission.CREATE_PROJECT,
        Permission.DELETE_PROJECT,
        Permission.UPDATE_PROJECT,
        Permission.VIEW_PROJECT,
        Permission.MODIFY_CONFIG,
        Permission.VIEW_CONFIG,
        Permission.EXPORT_REPORT,
    ],
    Role.USER: _USER_PERMISSIONS,
}
