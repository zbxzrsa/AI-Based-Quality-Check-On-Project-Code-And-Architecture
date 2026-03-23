/**
 * ProjectActions Component
 * Demonstrates permission-based UI element rendering
 */
'use client';

import { Button } from '@/components/ui/button';
import { PermissionCheck } from '@/components/auth/PermissionCheck';
import { Permission } from '@/types/rbac';
import { Edit, Trash2, Eye, Plus } from 'lucide-react';

interface ProjectActionsProps {
  projectId: string;
  onView?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function ProjectActions({ projectId, onView, onEdit, onDelete }: ProjectActionsProps) {
  return (
    <div className="flex gap-2">
      {/* View button - visible to all users with VIEW_PROJECTS permission */}
      <PermissionCheck permission={Permission.VIEW_PROJECTS}>
        <Button variant="outline" size="sm" onClick={onView}>
          <Eye className="h-4 w-4 mr-2" />
          View
        </Button>
      </PermissionCheck>

      {/* Edit button - only visible to users with MODIFY_PROJECT permission */}
      <PermissionCheck permission={Permission.MODIFY_PROJECT}>
        <Button variant="outline" size="sm" onClick={onEdit}>
          <Edit className="h-4 w-4 mr-2" />
          Edit
        </Button>
      </PermissionCheck>

      {/* Delete button - only visible to users with DELETE_PROJECT permission */}
      <PermissionCheck permission={Permission.DELETE_PROJECT}>
        <Button variant="destructive" size="sm" onClick={onDelete}>
          <Trash2 className="h-4 w-4 mr-2" />
          Delete
        </Button>
      </PermissionCheck>
    </div>
  );
}

interface UserManagementActionsProps {
  userId: string;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function UserManagementActions({ userId, onEdit, onDelete }: UserManagementActionsProps) {
  return (
    <div className="flex gap-2">
      {/* Edit user - only visible to admins with MODIFY_USER permission */}
      <PermissionCheck permission={Permission.MODIFY_USER}>
        <Button variant="ghost" size="sm" onClick={onEdit}>
          <Edit className="h-4 w-4" />
        </Button>
      </PermissionCheck>

      {/* Delete user - only visible to admins with DELETE_USER permission */}
      <PermissionCheck permission={Permission.DELETE_USER}>
        <Button variant="ghost" size="sm" onClick={onDelete}>
          <Trash2 className="h-4 w-4" />
        </Button>
      </PermissionCheck>
    </div>
  );
}

interface CreateProjectButtonProps {
  onClick?: () => void;
}

export function CreateProjectButton({ onClick }: CreateProjectButtonProps) {
  return (
    <PermissionCheck 
      permission={Permission.CREATE_PROJECT}
      fallback={
        <Button variant="outline" disabled>
          <Plus className="h-4 w-4 mr-2" />
          Create Project (No Permission)
        </Button>
      }
    >
      <Button onClick={onClick}>
        <Plus className="h-4 w-4 mr-2" />
        Create Project
      </Button>
    </PermissionCheck>
  );
}
