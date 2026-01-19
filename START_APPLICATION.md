# Start Application Guide

## Quick Start

### Prerequisites
- Node.js 18+ installed
- Python 3.9+ installed (for backend)
- PostgreSQL running (for backend)
- Redis running (for backend)

## Start Frontend Only

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: **http://localhost:3000**

## Start Full Stack

### Terminal 1 - Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Terminal 2 - Frontend
```bash
cd frontend
npm install
npm run dev
```

### Terminal 3 - Celery Worker (Optional)
```bash
cd backend
celery -A app.celery_config worker --loglevel=info
```

## Environment Variables

### Frontend (.env.local)
```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=dev-secret-key-change-in-production-min-32-chars-required
NEXT_PUBLIC_API_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_APP_ENV=development
NODE_ENV=development
```

### Backend (.env)
```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Access Points

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## Default Test Credentials

If you have seeded the database:
- **Email:** admin@example.com
- **Password:** admin123

## Troubleshooting

### Frontend Issues

**Port 3000 already in use:**
```bash
# Kill process on port 3000
npx kill-port 3000
# Or use a different port
npm run dev -- -p 3001
```

**Module not found errors:**
```bash
rm -rf node_modules package-lock.json
npm install
```

**NextAuth errors:**
- Verify NEXTAUTH_SECRET is set
- Check backend is running
- Clear browser cookies

### Backend Issues

**Port 8000 already in use:**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9  # Mac/Linux
# Or use a different port
uvicorn app.main:app --reload --port 8001
```

**Database connection errors:**
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Run migrations: `alembic upgrade head`

**Import errors:**
```bash
pip install -r requirements.txt --force-reinstall
```

## Development Workflow

### 1. Start Services
```bash
# Start PostgreSQL
brew services start postgresql  # Mac
sudo service postgresql start   # Linux

# Start Redis
brew services start redis        # Mac
sudo service redis-server start  # Linux
```

### 2. Run Migrations
```bash
cd backend
alembic upgrade head
```

### 3. Seed Database (Optional)
```bash
cd backend
python scripts/seed_database.py
```

### 4. Start Application
Follow "Start Full Stack" instructions above

## Testing

### Frontend Tests
```bash
cd frontend
npm test
npm run test:watch  # Watch mode
npm run test:coverage  # With coverage
```

### Backend Tests
```bash
cd backend
pytest
pytest --cov=app  # With coverage
pytest -v  # Verbose output
```

## Building for Production

### Frontend
```bash
cd frontend
npm run build
npm start  # Start production server
```

### Backend
```bash
cd backend
# Use gunicorn for production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Docker Compose (Alternative)

Start everything with Docker:
```bash
docker-compose up -d
```

Stop everything:
```bash
docker-compose down
```

View logs:
```bash
docker-compose logs -f
```

## Useful Commands

### Frontend
```bash
npm run lint          # Run ESLint
npm run lint:fix      # Fix linting issues
npm run format        # Format with Prettier
npm run type-check    # TypeScript type checking
```

### Backend
```bash
black .               # Format Python code
flake8 .              # Lint Python code
mypy .                # Type checking
bandit -r app/        # Security checks
```

## IDE Setup

### VS Code Extensions
- ESLint
- Prettier
- Python
- Pylance
- Docker
- GitLens

### Recommended Settings
```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true
}
```

## Getting Help

- Check TROUBLESHOOTING.md for common issues
- Review PAGES_COMPLETION_GUIDE.md for page-specific info
- Check API documentation at http://localhost:8000/docs
- Review component documentation in /frontend/src/components/

## Summary

✅ Frontend runs on port 3000
✅ Backend runs on port 8000
✅ All pages are functional
✅ Mock data available for development
✅ Ready for backend integration

Happy coding! 🚀
