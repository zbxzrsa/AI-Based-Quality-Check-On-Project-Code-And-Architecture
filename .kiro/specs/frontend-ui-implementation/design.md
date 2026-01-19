# Frontend UI Implementation Design

## Overview

This document outlines the design for the frontend user interface of the AI-powered code review and architecture analysis platform. The UI is built with Next.js 14, React 18, TypeScript, and Tailwind CSS, providing a modern, responsive, and accessible user experience.

## Technology Stack

- **Framework**: Next.js 14 (App Router)
- **UI Library**: React 18
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **State Management**: React Context + TanStack Query (React Query)
- **Authentication**: NextAuth.js
- **Charts**: Recharts / Chart.js
- **Graph Visualization**: React Flow / D3.js
- **Real-time**: Socket.IO client
- **Forms**: React Hook Form + Zod validation
- **Icons**: Lucide React

## Architecture

### Component Structure

```
frontend/src/
├── app/                          # Next.js App Router pages
│   ├── (auth)/                   # Authentication routes
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/              # Protected dashboard routes
│   │   ├── dashboard/
│   │   ├── projects/
│   │   ├── reviews/
│   │   ├── architecture/
│   │   └── admin/
│   └── api/                      # API routes
├── components/                   # Reusable components
│   ├── ui/                       # shadcn/ui components
│   ├── dashboard/
│   ├── reviews/
│   ├── architecture/
│   ├── projects/
│   └── common/
├── lib/                          # Utilities and helpers
│   ├── api/                      # API client functions
│   ├── hooks/                    # Custom React hooks
│   ├── utils/                    # Utility functions
│   └── types/                    # TypeScript types
├── contexts/                     # React contexts
└── styles/                       # Global styles
```

## Page Designs

### 1. Authentication Pages

#### Login Page (`/login`)
- Clean, centered login form
- Email and password fields
- "Remember Me" checkbox
- "Forgot Password" link
- Social login options (GitHub OAuth)
- Error message display
- Loading state during authentication

#### Register Page (`/register`)
- User registration form
- Email, password, full name fields
- Password strength indicator
- Terms of service acceptance
- Email verification flow

### 2. Dashboard (`/dashboard`)

#### Layout
- Top navigation bar with:
  - Logo and platform name
  - Global search
  - Notifications bell icon
  - User profile dropdown
- Sidebar navigation with:
  - Dashboard
  - Projects
  - Pull Requests
  - Architecture
  - Admin (role-based)
- Main content area

#### Dashboard Content
- **Overview Cards** (top row):
  - Total Projects
  - Pending Reviews
  - Critical Issues
  - Architecture Health Score
  
- **Recent Activity** (left column):
  - List of recent PR reviews
  - Status indicators (pending, in-progress, completed)
  - Quick action buttons
  
- **Architecture Health** (right column):
  - Health score gauge
  - Recent drift alerts
  - Trend chart
  
- **Quick Actions**:
  - Add New Project
  - View All Reviews
  - Architecture Overview

### 3. Projects Page (`/projects`)

#### Project List View
- Grid or list view toggle
- Each project card shows:
  - Project name and description
  - Repository URL
  - Last analysis date
  - Health status badge
  - Quick stats (PRs, issues, health)
- Filter and sort options
- Search bar
- "Add Project" button

#### Project Detail Page (`/projects/[id]`)
- **Header Section**:
  - Project name and description
  - Repository link
  - Settings button
  - Delete project button (admin only)
  
- **Tabs**:
  - Overview
  - Pull Requests
  - Architecture
  - Settings
  - Analytics
  
- **Overview Tab**:
  - Project statistics
  - Recent pull requests
  - Architecture health summary
  - Team members
  
- **Settings Tab**:
  - Webhook configuration
  - Quality thresholds
  - Notification preferences
  - Integration settings

### 4. Pull Request Review Page (`/reviews/[id]`)

#### Layout
- **Header**:
  - PR title and number
  - Status badge
  - Author and date
  - GitHub link
  
- **Metadata Section**:
  - Files changed count
  - Lines added/deleted
  - Reviewers
  - Labels
  
- **Code Diff Viewer**:
  - File tree navigation (left sidebar)
  - Split or unified diff view toggle
  - Syntax highlighting
  - Line numbers
  - Collapsible file sections
  
- **AI Review Comments**:
  - Inline comments on specific lines
  - Comment cards with:
    - Severity badge (critical, high, medium, low)
    - Category tag (security, performance, etc.)
    - AI explanation
    - Code snippet
    - Suggested fix
    - "Show reasoning" expandable section
    - Action buttons (Resolve, Won't Fix, Ask AI)
  
- **Compliance Section**:
  - ISO/IEC 25010 compliance status
  - ISO/IEC 23396 compliance status
  - Standards violations list
  
- **Summary Panel** (right sidebar):
  - Overall score
  - Issue count by severity
  - Compliance status
  - Architectural impact
  - Action buttons (Approve, Request Changes)

### 5. Architecture Visualization Page (`/architecture`)

#### Main View
- **Graph Canvas** (center):
  - Interactive node-link diagram
  - Zoom and pan controls
  - Node types (components, classes, functions)
  - Edge types (dependencies, calls, imports)
  - Color coding by health status
  - Highlight circular dependencies in red
  
- **Control Panel** (left sidebar):
  - Project selector
  - View options:
    - Layout algorithm (force-directed, hierarchical, circular)
    - Node size by (lines of code, complexity, dependencies)
    - Show/hide node types
  - Filter options:
    - By layer (presentation, business, data)
    - By module
    - By health status
  - Search nodes
  
- **Details Panel** (right sidebar):
  - Selected node information:
    - Component name
    - File path
    - Dependencies (incoming/outgoing)
    - Metrics (complexity, lines of code)
    - Health status
    - Recent changes
  - Drift alerts for selected component
  
- **Timeline** (bottom):
  - Slider to view architecture at different points in time
  - Playback controls
  - Commit markers

#### Architecture Health Dashboard
- **Health Score Gauge**:
  - Overall architecture health (0-100)
  - Trend indicator
  
- **Drift Alerts**:
  - List of recent architectural changes
  - Severity indicators
  - Before/after comparison
  - Approve/Reject buttons
  
- **Metrics Charts**:
  - Coupling metrics over time
  - Cohesion metrics
  - Circular dependencies count
  - Component complexity distribution

### 6. Analysis Queue Page (`/queue`)

#### Queue View
- **Queue Statistics** (top):
  - Total queued tasks
  - In-progress tasks
  - Average wait time
  - Estimated completion time
  
- **Task List**:
  - Table with columns:
    - Project name
    - PR number
    - Status (queued, in-progress, completed, failed)
    - Priority
    - Submitted time
    - Estimated completion
    - Actions (view, retry, cancel)
  - Real-time updates
  - Filter by status and project
  - Sort by various columns

### 7. Admin Panel (`/admin`)

#### User Management Tab
- **User List**:
  - Table with columns:
    - Name
    - Email
    - Role
    - Status (active, inactive)
    - Last login
    - Actions (edit, deactivate, delete)
  - Add user button
  - Bulk actions
  
- **User Edit Modal**:
  - Edit user details
  - Change role
  - Reset password
  - Deactivate account

#### Audit Log Tab
- **Log Viewer**:
  - Filterable log entries
  - Columns: timestamp, user, action, entity, details
  - Export logs button
  - Date range filter

#### System Settings Tab
- **Configuration Options**:
  - LLM model selection
  - API rate limits
  - Webhook retry settings
  - Email notification settings
  - System maintenance mode

## Component Library

### Core UI Components (shadcn/ui)

1. **Button**: Primary, secondary, outline, ghost variants
2. **Card**: Container for content sections
3. **Badge**: Status indicators and tags
4. **Input**: Text input with validation
5. **Select**: Dropdown selection
6. **Checkbox**: Boolean input
7. **Radio**: Single selection from options
8. **Switch**: Toggle switch
9. **Tabs**: Tabbed navigation
10. **Dialog**: Modal dialogs
11. **Dropdown Menu**: Context menus
12. **Toast**: Notification messages
13. **Table**: Data tables with sorting
14. **Skeleton**: Loading placeholders
15. **Progress**: Progress indicators

### Custom Components

#### ReviewCommentCard
```typescript
interface ReviewCommentCardProps {
  comment: ReviewComment;
  onResolve: () => void;
  onWontFix: () => void;
  onAskAI: () => void;
}
```
- Displays AI-generated review comment
- Shows severity, category, and message
- Expandable reasoning section
- Action buttons

#### ArchitectureGraph
```typescript
interface ArchitectureGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick: (node: GraphNode) => void;
  highlightCircularDeps: boolean;
}
```
- Interactive graph visualization
- Zoom, pan, and selection
- Customizable layout and styling

#### CodeDiffViewer
```typescript
interface CodeDiffViewerProps {
  diff: DiffData;
  comments: ReviewComment[];
  onCommentClick: (comment: ReviewComment) => void;
}
```
- Split or unified diff view
- Syntax highlighting
- Inline comment display

#### MetricChart
```typescript
interface MetricChartProps {
  data: MetricData[];
  type: 'line' | 'bar' | 'area';
  title: string;
  xAxis: string;
  yAxis: string;
}
```
- Reusable chart component
- Multiple chart types
- Responsive design

## State Management

### React Query for Server State
- Fetch and cache API data
- Automatic refetching and invalidation
- Optimistic updates
- Error handling

### React Context for UI State
- Theme (light/dark)
- Sidebar collapsed state
- User preferences
- Notification settings

### Local State with useState/useReducer
- Form state
- Modal open/close
- Filter and sort state

## API Integration

### API Client Structure
```typescript
// lib/api/client.ts
export const apiClient = {
  auth: {
    login: (credentials) => POST('/api/v1/auth/login', credentials),
    logout: () => POST('/api/v1/auth/logout'),
    me: () => GET('/api/v1/auth/me'),
  },
  projects: {
    list: () => GET('/api/v1/projects'),
    get: (id) => GET(`/api/v1/projects/${id}`),
    create: (data) => POST('/api/v1/projects', data),
    update: (id, data) => PUT(`/api/v1/projects/${id}`, data),
    delete: (id) => DELETE(`/api/v1/projects/${id}`),
  },
  reviews: {
    list: (projectId) => GET(`/api/v1/projects/${projectId}/reviews`),
    get: (id) => GET(`/api/v1/reviews/${id}`),
    resolve: (id) => POST(`/api/v1/reviews/${id}/resolve`),
  },
  architecture: {
    getGraph: (projectId) => GET(`/api/v1/architecture/${projectId}/graph`),
    getHealth: (projectId) => GET(`/api/v1/architecture/${projectId}/health`),
    getDrift: (projectId) => GET(`/api/v1/architecture/${projectId}/drift`),
  },
};
```

### Custom Hooks
```typescript
// lib/hooks/useProjects.ts
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.projects.list(),
  });
}

// lib/hooks/useReview.ts
export function useReview(id: string) {
  return useQuery({
    queryKey: ['review', id],
    queryFn: () => apiClient.reviews.get(id),
  });
}
```

## Real-time Updates

### WebSocket Integration
```typescript
// lib/websocket.ts
export function useWebSocket() {
  useEffect(() => {
    const socket = io(process.env.NEXT_PUBLIC_WS_URL);
    
    socket.on('review:completed', (data) => {
      queryClient.invalidateQueries(['reviews']);
      toast.success('Review completed!');
    });
    
    socket.on('architecture:drift', (data) => {
      queryClient.invalidateQueries(['architecture']);
      toast.warning('Architecture drift detected!');
    });
    
    return () => socket.disconnect();
  }, []);
}
```

## Accessibility

### WCAG 2.1 Level AA Compliance
- Semantic HTML elements
- ARIA labels and roles
- Keyboard navigation support
- Focus management
- Color contrast ratios
- Screen reader support
- Skip navigation links

### Keyboard Shortcuts
- `/` - Focus search
- `Esc` - Close modals
- `Arrow keys` - Navigate lists
- `Enter` - Select/activate
- `Tab` - Navigate form fields

## Performance Optimization

### Code Splitting
- Route-based code splitting with Next.js
- Dynamic imports for heavy components
- Lazy loading for below-the-fold content

### Image Optimization
- Next.js Image component
- WebP format with fallbacks
- Responsive images
- Lazy loading

### Caching Strategy
- React Query cache configuration
- Service worker for offline support
- CDN for static assets

### Bundle Optimization
- Tree shaking
- Minification
- Compression (gzip/brotli)

## Testing Strategy

### Unit Tests
- Component rendering
- User interactions
- Utility functions
- Custom hooks

### Integration Tests
- Page flows
- API integration
- Form submissions
- Authentication flows

### E2E Tests
- Critical user journeys
- Cross-browser testing
- Accessibility testing

## Deployment

### Build Process
```bash
npm run build
npm run start
```

### Environment Variables
```env
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_WS_URL=wss://api.example.com
NEXTAUTH_URL=https://app.example.com
NEXTAUTH_SECRET=<secret>
```

### Hosting
- Vercel (recommended for Next.js)
- Docker container
- Static export for CDN

## Future Enhancements

1. **Mobile App**: React Native version
2. **VS Code Extension**: In-editor code review
3. **Slack Integration**: Notifications and commands
4. **Advanced Analytics**: ML-powered insights
5. **Collaborative Features**: Real-time collaboration on reviews
6. **Custom Dashboards**: User-configurable widgets
7. **Export/Import**: Project configuration templates
8. **API Documentation**: Interactive API explorer
