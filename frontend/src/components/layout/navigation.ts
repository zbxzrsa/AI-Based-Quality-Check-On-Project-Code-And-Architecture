import {
  Activity,
  LayoutDashboard,
  FolderGit2,
  GitPullRequest,
  Network,
  Settings2,
  UserCircle2,
} from 'lucide-react'

export const primaryNavigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Projects', href: '/projects', icon: FolderGit2 },
  { name: 'Pull Requests', href: '/reviews', icon: GitPullRequest },
  { name: 'Architecture', href: '/architecture', icon: Network },
  { name: 'Analysis Queue', href: '/queue', icon: Activity },
] as const

export const secondaryNavigation = [
  { name: 'Profile', href: '/profile', icon: UserCircle2 },
  { name: 'Settings', href: '/settings', icon: Settings2 },
] as const
