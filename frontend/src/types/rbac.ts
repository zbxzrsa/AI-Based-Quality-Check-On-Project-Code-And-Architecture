/**
 * RBAC Type Definitions
 */

export enum Role {
  ADMIN = 'admin',
  USER = 'user',
}

export enum Permission {
  VIEW_PROJECTS = 'view_projects',
  CREATE_PROJECT = 'create_project',
  MODIFY_PROJECT = 'modify_project',
  DELETE_PROJECT = 'delete_project',
  VIEW_USERS = 'view_users',
  CREATE_USER = 'create_user',
  MODIFY_USER = 'modify_user',
  DELETE_USER = 'delete_user',
  VIEW_REVIEWS = 'view_reviews',
  CREATE_REVIEW = 'create_review',
  MODIFY_REVIEW = 'modify_review',
  MODIFY_CONFIG = 'modify_config',
}

export type UserRole = Role;

export interface ProjectAccess {
  projectId: string;
  permissions: Permission[];
}

export interface RBACUser {
  id: string;
  username: string;
  role: Role;
  permissions?: Permission[];
}

