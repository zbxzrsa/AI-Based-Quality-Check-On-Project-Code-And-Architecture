"""
Enums for the Enterprise RBAC Authentication System.
"""
# Import consolidated enums from common library
from common.shared.enums import Role, Permission


# Role-Permission Mapping
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
    Role.PROGRAMMER: [
        Permission.CREATE_PROJECT,
        Permission.UPDATE_PROJECT,
        Permission.VIEW_PROJECT,
        Permission.VIEW_CONFIG,
        Permission.EXPORT_REPORT,
    ],
    Role.VISITOR: [
        Permission.VIEW_PROJECT,
    ],
}
