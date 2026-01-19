# Frontend Troubleshooting Guide

## Common Issues and Solutions

### 1. NextAuth Session Errors

**Error:**
```
[next-auth][error][CLIENT_FETCH_ERROR]
Unexpected token '<', "<!DOCTYPE "... is not valid JSON
```

**Cause:** The backend server is not running or not accessible.

**Solution:**

1. **Start the Backend Server:**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. **Verify Backend is Running:**
   - Open http://localhost:8000/docs in your browser
   - You should see the FastAPI Swagger documentation

3. **Check Environment Variables:**
   Ensure `frontend/.env.local` has:
   ```env
   BACKEND_URL=http://localhost:8000
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXTAUTH_URL=http://localhost:3000
   NEXTAUTH_SECRET=dev-secret-key-change-in-production-min-32-chars-required
   ```

4. **Restart Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

### 2. Backend Status Indicator

The frontend now includes a **Backend Status** indicator that appears in the bottom-right corner when the backend is not available. This indicator:

- Automatically checks backend connectivity
- Shows when the backend is offline
- Provides a "Check Again" button to retry
- Can be dismissed if you're working on frontend-only features

### 3. Working Without Backend

The frontend is designed to work with mock data when the backend is not available:

- All pages will load with sample data
- You can navigate and test the UI
- Authentication will not work (use mock mode)
- API calls will fail gracefully

**To work in mock mode:**
- Simply ignore the backend status warning
- All UI components will function with mock data
- Perfect for frontend development and testing

### 4. Port Conflicts

**Error:** Port 3000 or 8000 already in use

**Solution:**

1. **Find and kill the process:**
   ```bash
   # Windows
   netstat -ano | findstr :3000
   taskkill /PID <PID> /F

   # Linux/Mac
   lsof -ti:3000 | xargs kill -9
   ```

2. **Or use different ports:**
   ```bash
   # Frontend
   npm run dev -- -p 3001

   # Backend
   uvicorn app.main:app --port 8001
   ```

### 5. Module Not Found Errors

**Error:** Cannot find module '@/components/...'

**Solution:**

1. **Check tsconfig.json paths:**
   ```json
   {
     "compilerOptions": {
       "paths": {
         "@/*": ["./src/*"]
       }
     }
   }
   ```

2. **Restart the dev server:**
   ```bash
   npm run dev
   ```

### 6. Styling Issues

**Error:** Tailwind classes not working

**Solution:**

1. **Check tailwind.config.ts content paths:**
   ```typescript
   content: [
     './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
     './src/components/**/*.{js,ts,jsx,tsx,mdx}',
     './src/app/**/*.{js,ts,jsx,tsx,mdx}',
   ]
   ```

2. **Rebuild:**
   ```bash
   npm run build
   npm run dev
   ```

### 7. React Flow Errors

**Error:** React Flow rendering issues

**Solution:**

1. **Ensure reactflow is installed:**
   ```bash
   npm install reactflow
   ```

2. **Import CSS:**
   ```typescript
   import 'reactflow/dist/style.css';
   ```

### 8. Chart Rendering Issues

**Error:** Recharts not displaying

**Solution:**

1. **Check Recharts installation:**
   ```bash
   npm install recharts
   ```

2. **Ensure ResponsiveContainer is used:**
   ```typescript
   <ResponsiveContainer width="100%" height={300}>
     <LineChart data={data}>
       {/* ... */}
     </LineChart>
   </ResponsiveContainer>
   ```

## Development Workflow

### Recommended Setup

1. **Terminal 1 - Backend:**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. **Terminal 2 - Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Frontend-Only Development

If you're working on UI components without needing the backend:

1. Start only the frontend
2. Dismiss the backend status warning
3. Work with mock data
4. All UI features will function normally

### Full-Stack Development

When working with both frontend and backend:

1. Start backend first
2. Wait for backend to be ready (check /docs)
3. Start frontend
4. Backend status indicator should show green or not appear

## Quick Fixes

### Clear Everything and Restart

```bash
# Frontend
cd frontend
rm -rf node_modules .next
npm install
npm run dev

# Backend
cd backend
rm -rf __pycache__ .pytest_cache
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Check All Services

```bash
# Check if ports are available
netstat -ano | findstr :3000
netstat -ano | findstr :8000

# Check if processes are running
ps aux | grep node
ps aux | grep uvicorn
```

## Getting Help

If you encounter issues not covered here:

1. Check the browser console for detailed errors
2. Check the terminal output for both frontend and backend
3. Verify all environment variables are set correctly
4. Ensure all dependencies are installed
5. Try clearing caches and rebuilding

## Production Deployment

For production deployment:

1. Set proper environment variables
2. Build the frontend: `npm run build`
3. Use a process manager (PM2, systemd)
4. Set up reverse proxy (nginx)
5. Enable HTTPS
6. Configure CORS properly
7. Set secure NEXTAUTH_SECRET

---

**Last Updated:** January 19, 2026
