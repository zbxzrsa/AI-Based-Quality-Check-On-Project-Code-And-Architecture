import dotenv from 'dotenv';

dotenv.config();

export const config = {
  port: parseInt(process.env['PORT'] || '3001', 10),
  nodeEnv: process.env['NODE_ENV'] || 'development',
  
  // Database configuration
  database: {
    url: process.env['DATABASE_URL'] || 'postgresql://postgres:postgres@localhost:5432/ai_code_review',
  },

  // Redis configuration
  redis: {
    url: process.env['REDIS_URL'] || 'redis://localhost:6379',
  },

  // JWT configuration
  jwt: {
    secret: process.env['JWT_SECRET'] || 'your-secret-key',
    expiresIn: process.env['JWT_EXPIRES_IN'] || '24h',
  },

  // Password hashing
  bcrypt: {
    rounds: parseInt(process.env['BCRYPT_ROUNDS'] || '12', 10),
  },

  // Session configuration
  session: {
    secret: process.env['SESSION_SECRET'] || 'your-session-secret',
  },

  // SAML configuration
  saml: {
    certPath: process.env['SAML_CERT_PATH'] || './certs/saml.crt',
    keyPath: process.env['SAML_KEY_PATH'] || './certs/saml.key',
  },

  // OAuth configuration
  oauth: {
    clientId: process.env['OAUTH_CLIENT_ID'] || '',
    clientSecret: process.env['OAUTH_CLIENT_SECRET'] || '',
  },

  // CORS configuration
  cors: {
    allowedOrigins: process.env['CORS_ALLOWED_ORIGINS']?.split(',') || ['http://localhost:3000'],
  },

  // Logging
  logging: {
    level: process.env['LOG_LEVEL'] || 'info',
  },
};