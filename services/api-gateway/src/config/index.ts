import dotenv from 'dotenv';

dotenv.config();

export const config = {
  port: parseInt(process.env.PORT || '3000', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
  
  // Service URLs
  services: {
    authService: process.env.AUTH_SERVICE_URL || 'http://localhost:3001',
    codeReviewEngine: process.env.CODE_REVIEW_ENGINE_URL || 'http://localhost:3002',
    architectureAnalyzer: process.env.ARCHITECTURE_ANALYZER_URL || 'http://localhost:3003',
    agenticAI: process.env.AGENTIC_AI_URL || 'http://localhost:3004',
    projectManager: process.env.PROJECT_MANAGER_URL || 'http://localhost:3005',
  },

  // JWT configuration
  jwt: {
    secret: process.env.JWT_SECRET || 'your-secret-key',
    expiresIn: process.env.JWT_EXPIRES_IN || '24h',
  },

  // CORS configuration
  cors: {
    allowedOrigins: process.env.CORS_ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  },

  // Rate limiting
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000', 10), // 15 minutes
    max: parseInt(process.env.RATE_LIMIT_MAX || '100', 10), // limit each IP to 100 requests per windowMs
  },

  // GitHub webhook
  github: {
    webhookSecret: process.env.GITHUB_WEBHOOK_SECRET || '',
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
  },
};