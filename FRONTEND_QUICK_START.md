# Frontend Quick Start Guide

## 🚀 Get Started in 5 Minutes

This guide will help you get the AI Code Review Platform frontend up and running quickly.

---

## Prerequisites

- **Node.js**: >= 18.0.0
- **npm**: >= 9.0.0
- **Git**: Latest version

---

## Installation

### 1. Navigate to Frontend Directory
```bash
cd frontend
```

### 2. Install Dependencies
```bash
npm install
```

This will install all required packages including:
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- shadcn/ui components
- React Query
- NextAuth
- And more...

---

## Configuration

### 3. Set Up Environment Variables

Create a `.env.local` file in the `frontend` directory:

```bash
# Copy the example file
cp .env.example .env.local
```

Edit `.env.local` with your values:

```env
# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-min-32-chars-change-in-production

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# OAuth Providers (Optional)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

**Important**: 
- Generate a secure `NEXTAUTH_SECRET` for production
- The backend URL should point to your FastAPI server

---

## Running the Application

### Option 1: Frontend Only (Mock Data)

Perfect for UI development without backend:

```bash
npm run dev
```

- Application runs at: http://localhost:3000
- Uses mock data for all features
- Backend status warning will appear (can be dismissed)
- All UI features work normally

### Option 2: Full Stack (With Backend)

For complete functionality with real data:

**Terminal 1 - Start Backend:**
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Available Scripts

### Development
```bash
npm run dev          # Start development server
```

### Production
```bash
npm run build        # Build for production
npm start            # Start production server
```

### Code Quality
```bash
npm run lint         # Run ESLint
npm run test         # Run tests (if configured)
```

---

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js 14 App Router pages
│   │   ├── dashboard/          # Dashboard page
│   │   ├── projects/           # Projects pages
│   │   ├── reviews/            # Review pages
│   │   ├── architecture/       # Architecture visualization
│   │   ├── admin/              # Admin panel
│   │   ├── queue/              # Queue monitoring
│   │   ├── search/             # Global search
│   │   ├── metrics/            # Metrics dashboard
│   │   ├── profile/            # User profile
│   │   ├── settings/           # User settings
│   │   ├── login/              # Login page
│   │   ├── register/           # Registration page
│   │   └── ...                 # Other pages
│   │
│   ├── components/             # React components
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── layout/             # Layout components
│   │   ├── common/             # Common components
│   │   ├── projects/           # Project components
│   │   ├── reviews/            # Review components
│   │   ├── architecture/       # Architecture components
│   │   ├── charts/             # Chart components
│   │   └── notifications/      # Notification components
│   │
│   ├── lib/                    # Utilities and configs
│   │   ├── utils.ts            # Utility functions
│   │   ├── api.ts              # API client
│   │   └── react-query.ts      # React Query config
│   │
│   ├── hooks/                  # Custom React hooks
│   │   └── use-toast.ts        # Toast hook
│   │
│   ├── types/                  # TypeScript types
│   │   └── index.ts            # Type definitions
│   │
│   ├── styles/                 # Global styles
│   │   └── globals.css         # Global CSS
│   │
│   └── middleware.ts           # Next.js middleware
│
├── public/                     # Static assets
├── .env.local                  # Environment variables (create this)
├── .env.example                # Environment template
├── next.config.mjs             # Next.js configuration
├── tailwind.config.ts          # Tailwind configuration
├── tsconfig.json               # TypeScript configuration
└── package.json                # Dependencies and scripts
```

---

## Key Features

### 🎨 UI Components
- 20+ shadcn/ui components
- Custom theme with dark mode
- Responsive design
- Accessible (WCAG AA)

### 📄 Pages (17 Total)
- Landing page
- Authentication (login, register, password reset)
- Dashboard with overview
- Projects management
- PR review interface
- Architecture visualization
- Queue monitoring
- Admin panel
- Global search
- Metrics dashboard
- User profile & settings

### 🔧 Technical Features
- TypeScript strict mode
- React Query for data fetching
- Form validation with Zod
- Real-time notifications
- WebSocket support
- Error boundaries
- Loading states
- Toast notifications

---

## First Steps After Installation

### 1. Explore the Landing Page
Visit http://localhost:3000 to see the landing page with:
- Feature overview
- Call-to-action buttons
- Responsive design

### 2. Try the Dashboard
Navigate to http://localhost:3000/dashboard to see:
- Overview cards
- Recent activity
- Architecture health
- Quick actions

### 3. Browse Projects
Visit http://localhost:3000/projects to explore:
- Project list with grid/list view
- Search and filters
- Add project modal

### 4. Check Architecture Visualization
Go to http://localhost:3000/architecture for:
- Interactive graph
- Node details
- Timeline view

### 5. View Metrics
Visit http://localhost:3000/metrics to see:
- Code quality trends
- Architecture health
- Team productivity

---

## Development Tips

### Hot Reload
- Changes to files automatically reload the browser
- Fast Refresh preserves component state

### TypeScript
- Strict mode enabled for type safety
- Use `npm run build` to check for type errors

### Styling
- Use Tailwind CSS utility classes
- Custom theme in `tailwind.config.ts`
- Dark mode with `next-themes`

### Components
- Use shadcn/ui components from `@/components/ui`
- Follow kebab-case naming convention
- Keep components small and focused

### API Integration
- API client in `src/lib/api.ts`
- Use React Query hooks for data fetching
- Mock data available for development

---

## Common Issues

### Port Already in Use
```bash
# Kill process on port 3000
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:3000 | xargs kill -9
```

### Module Not Found
```bash
# Clear cache and reinstall
rm -rf node_modules .next
npm install
```

### Backend Connection Issues
- Check if backend is running on port 8000
- Verify `NEXT_PUBLIC_API_URL` in `.env.local`
- Dismiss backend status warning for frontend-only development

### Build Errors
```bash
# Check TypeScript errors
npm run build

# Fix linting issues
npm run lint
```

---

## Next Steps

### For UI Development
1. ✅ Frontend is ready to use
2. Work with mock data
3. Develop and test components
4. No backend required

### For Full-Stack Development
1. Start the backend server
2. Configure environment variables
3. Test API integration
4. Enable real-time features

### For Production
1. Set secure environment variables
2. Build the application: `npm run build`
3. Test the production build: `npm start`
4. Deploy to your hosting platform

---

## Documentation

- **Implementation Status**: `FRONTEND_IMPLEMENTATION_STATUS.md`
- **Troubleshooting**: `FRONTEND_TROUBLESHOOTING.md`
- **Fixes Applied**: `FIXES_APPLIED.md`
- **Complete Summary**: `FRONTEND_COMPLETE_SUMMARY.md`
- **Completion Checklist**: `FRONTEND_COMPLETION_CHECKLIST.md`

---

## Support

### Resources
- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [shadcn/ui Components](https://ui.shadcn.com)
- [Tailwind CSS](https://tailwindcss.com)

### Getting Help
1. Check the troubleshooting guide
2. Review the documentation files
3. Check browser console for errors
4. Verify environment variables

---

## Summary

You now have a fully functional frontend application with:
- ✅ 17 pages implemented
- ✅ 45+ components created
- ✅ Dark mode support
- ✅ Responsive design
- ✅ TypeScript strict mode
- ✅ Production ready

**Happy coding! 🚀**

---

**Last Updated**: January 19, 2026
**Version**: 1.0.0
**Status**: Production Ready

