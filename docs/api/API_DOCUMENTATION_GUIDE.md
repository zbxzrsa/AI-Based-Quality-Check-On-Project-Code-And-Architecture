# API Documentation Guide

This guide explains how to access and use the API documentation for the AI Code Review Platform.

## Documentation Locations

The API documentation is available in three formats:

### 1. Swagger UI (Interactive)
**URL:** `http://localhost:8000/docs`

Swagger UI provides an interactive interface where you can:
- Browse all API endpoints
- Try out API calls directly from the browser
- See request/response schemas
- Test authentication

**Best for:** Interactive exploration and testing

### 2. ReDoc (Read-Only)
**URL:** `http://localhost:8000/redoc`

ReDoc provides a clean, read-only documentation interface with:
- Better organization for large APIs
- Search functionality
- Responsive design
- Code samples

**Best for:** Reading documentation and understanding the API structure

### 3. OpenAPI Specification (JSON/YAML)
**URLs:**
- JSON: `http://localhost:8000/api/v1/openapi.json`
- YAML: `docs/api/openapi.yaml` (generated file)

The raw OpenAPI specification can be used with:
- API client generators (e.g., openapi-generator)
- Testing tools (e.g., Postman, Insomnia)
- Documentation generators
- CI/CD pipelines

**Best for:** Automation and tooling integration

## Using Authentication in Swagger UI

Most API endpoints require JWT authentication. Here's how to authenticate in Swagger UI:

### Step 1: Get a JWT Token

First, you need to register and login to get a token:

1. **Register a new user** (if you don't have an account):
   - Navigate to `POST /api/v1/auth/register`
   - Click "Try it out"
   - Fill in the request body:
     ```json
     {
       "email": "your.email@example.com",
       "password": "your-strong-password",
       "full_name": "Your Name"
     }
     ```
   - Click "Execute"

2. **Login to get your token**:
   - Navigate to `POST /api/v1/auth/login`
   - Click "Try it out"
   - Fill in the request body:
     ```json
     {
       "email": "your.email@example.com",
       "password": "your-strong-password"
     }
     ```
   - Click "Execute"
   - Copy the `access_token` from the response

### Step 2: Authorize in Swagger UI

1. Click the **"Authorize"** button at the top right of the Swagger UI page
2. In the "HTTPBearer" section, enter your token:
   ```
   Bearer <your_access_token_here>
   ```
   **Note:** Include the word "Bearer" followed by a space, then your token
3. Click **"Authorize"**
4. Click **"Close"**

The lock icon (🔒) next to protected endpoints will now appear closed, indicating you're authenticated.

### Step 3: Make Authenticated Requests

Now you can call any protected endpoint:
1. Navigate to the endpoint you want to test
2. Click "Try it out"
3. Fill in any required parameters
4. Click "Execute"

The request will automatically include your authentication token in the `Authorization` header.

## Using Authentication with curl

If you prefer using curl or other HTTP clients:

```bash
# 1. Register (if needed)
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-strong-password",
    "full_name": "John Doe"
  }'

# 2. Login to get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-strong-password"
  }'

# Response will include:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer",
#   "expires_in": 86400
# }

# 3. Use the token in subsequent requests
curl -X GET "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Token Management

### Token Expiration

- **Access tokens** expire after 24 hours
- **Refresh tokens** are valid for 7 days

### Refreshing Tokens

When your access token expires, use the refresh endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Authorization: Bearer <your_current_token>"
```

This will return a new access token without requiring you to re-enter your credentials.

### Logout

To invalidate your token:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Authorization: Bearer <your_token>"
```

## API Endpoint Categories

The API is organized into the following categories (tags):

- **Health**: Health check endpoints for monitoring
- **Authentication**: User registration, login, logout, token refresh
- **RBAC Authentication**: Role-based access control authentication
- **RBAC User Management**: User management with role-based permissions
- **RBAC Project Management**: Project management with access control
- **RBAC Audit Logs**: Audit log queries for RBAC operations
- **Webhooks**: GitHub webhook handlers for automated PR analysis
- **GitHub Integration**: GitHub API integration for repositories and PRs
- **Code Review**: Automated code review endpoints
- **PR Analysis**: Pull request analysis and review generation
- **Architecture Analysis**: Repository architecture analysis and pattern detection
- **Local LLM**: Local LLM (Ollama) integration for code analysis
- **Library Management**: Manage code libraries and dependencies
- **Repository Management**: Repository CRUD operations
- **Audit Logs**: System-wide audit log queries
- **User Data Management**: User data export and deletion (GDPR compliance)
- **Metrics**: Prometheus metrics endpoint for monitoring
- **Database**: Database management and migration endpoints

## Rate Limiting

API endpoints are rate-limited to **100 requests per minute per user**.

If you exceed this limit, you'll receive an HTTP 429 (Too Many Requests) response:

```json
{
  "error": "Rate limit exceeded: 100 per 1 minute",
  "detail": "Too many requests"
}
```

Wait for the rate limit window to reset before making more requests.

## Error Responses

All endpoints return standardized error responses:

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common HTTP Status Codes

- **200 OK**: Request succeeded
- **201 Created**: Resource created successfully
- **204 No Content**: Request succeeded with no response body
- **400 Bad Request**: Invalid input or malformed request
- **401 Unauthorized**: Missing or invalid authentication token
- **403 Forbidden**: Insufficient permissions for this action
- **404 Not Found**: Resource doesn't exist
- **422 Unprocessable Entity**: Validation error
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server-side error
- **503 Service Unavailable**: Service temporarily unavailable

## Generating API Clients

You can generate API clients in various programming languages using the OpenAPI specification:

### Using openapi-generator

```bash
# Install openapi-generator
npm install @openapitools/openapi-generator-cli -g

# Generate Python client
openapi-generator-cli generate \
  -i http://localhost:8000/api/v1/openapi.json \
  -g python \
  -o ./api-client-python

# Generate TypeScript client
openapi-generator-cli generate \
  -i http://localhost:8000/api/v1/openapi.json \
  -g typescript-axios \
  -o ./api-client-typescript

# Generate Java client
openapi-generator-cli generate \
  -i http://localhost:8000/api/v1/openapi.json \
  -g java \
  -o ./api-client-java
```

### Using Postman

1. Open Postman
2. Click "Import"
3. Select "Link" tab
4. Enter: `http://localhost:8000/api/v1/openapi.json`
5. Click "Continue" and "Import"

All API endpoints will be imported into a Postman collection.

## Verifying Documentation Setup

To verify that the API documentation is properly configured, run:

```bash
cd backend
python scripts/verify_api_documentation.py
```

This script checks:
- Swagger UI accessibility
- ReDoc accessibility
- OpenAPI specification completeness
- Security scheme configuration
- Authentication documentation

## Updating Documentation

The API documentation is automatically generated from the FastAPI application code. To update it:

1. **Modify endpoint docstrings** in the code:
   ```python
   @router.get("/example")
   async def example_endpoint():
       """
       Brief description of the endpoint.
       
       Detailed description with more information.
       
       - **param1**: Description of parameter 1
       - **param2**: Description of parameter 2
       
       Returns:
           Description of the return value
       """
       pass
   ```

2. **Regenerate the OpenAPI specification**:
   ```bash
   cd backend
   python scripts/generate_openapi_spec.py --validate --summary
   ```

3. **Restart the server** to see the changes:
   ```bash
   uvicorn app.main:app --reload
   ```

The documentation at `/docs` and `/redoc` will automatically reflect your changes.

## Troubleshooting

### Documentation Not Loading

If the documentation pages don't load:

1. **Check the server is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check for errors in server logs**

3. **Verify the OpenAPI spec is accessible**:
   ```bash
   curl http://localhost:8000/api/v1/openapi.json
   ```

### Authentication Not Working

If authentication fails in Swagger UI:

1. **Verify you included "Bearer" prefix**:
   - Correct: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - Incorrect: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

2. **Check token hasn't expired** (24-hour lifetime)

3. **Try getting a fresh token** by logging in again

### Rate Limit Issues

If you're hitting rate limits during testing:

1. **Wait for the rate limit window to reset** (1 minute)

2. **Use a different user account** for testing

3. **Temporarily disable rate limiting** in development:
   - Set `RATE_LIMIT_ENABLED=false` in `.env`
   - Restart the server

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Swagger UI Documentation](https://swagger.io/tools/swagger-ui/)
- [ReDoc Documentation](https://redocly.com/docs/redoc/)

## Support

For issues or questions about the API documentation:

- **Email**: support@example.com
- **GitHub Issues**: [Project Repository](https://github.com/your-org/your-repo)
- **Internal Documentation**: See `docs/` directory for more guides
