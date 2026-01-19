# AI-Powered Code Review and Architecture Analysis Platform

This is a comprehensive microservices-based platform that provides automated code quality analysis, graph-based architecture visualization, and agentic AI reasoning for software development teams.

## Architecture

The platform consists of the following microservices:

- **api-gateway**: Single entry point for all external requests, handles routing and rate limiting
- **auth-service**: Manages user authentication, authorization, and role-based access control
- **code-review-engine**: Processes code changes and performs quality analysis
- **architecture-analyzer**: Parses source code and maintains architectural graph database
- **agentic-ai**: Provides contextual AI reasoning and pattern recognition
- **project-manager**: Manages project lifecycle and provides dashboard functionality

## Development Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start all services with Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Run individual services in development mode:
   ```bash
   npm run dev:api-gateway
   npm run dev:auth-service
   npm run dev:code-review-engine
   npm run dev:architecture-analyzer
   npm run dev:agentic-ai
   npm run dev:project-manager
   ```

## Testing

Run all tests:
```bash
npm test
```

Run property-based tests:
```bash
npm run test:property
```

## Services

Each service is independently deployable and has its own:
- TypeScript configuration
- Docker container
- Test suite
- Documentation

See individual service README files for detailed information.