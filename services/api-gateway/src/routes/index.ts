import { Router } from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { config } from '../config';
import { logger } from '../utils/logger';
import { webhookRoutes } from './webhooks';

const router = Router();

// Webhook routes (special handling for GitHub webhooks)
router.use('/webhooks', webhookRoutes);

// Proxy routes to microservices
const createServiceProxy = (serviceName: string, serviceUrl: string) => {
  return createProxyMiddleware({
    target: serviceUrl,
    changeOrigin: true,
    pathRewrite: {
      [`^/api/${serviceName}`]: '/api',
    },
    onError: (err, req, res) => {
      logger.error(`Proxy error for ${serviceName}:`, err);
      res.status(503).json({
        error: {
          code: 'SERVICE_UNAVAILABLE',
          message: `${serviceName} service is currently unavailable`,
          retryable: true,
        },
      });
    },
    onProxyReq: (proxyReq, req) => {
      // Add auth context to proxied requests
      if (req.auth) {
        proxyReq.setHeader('X-User-ID', req.auth.userId);
        proxyReq.setHeader('X-User-Roles', JSON.stringify(req.auth.roles));
        proxyReq.setHeader('X-User-Permissions', JSON.stringify(req.auth.permissions));
      }
    },
  });
};

// Service proxy routes
router.use('/auth', createServiceProxy('auth', config.services.authService));
router.use('/code-review', createServiceProxy('code-review', config.services.codeReviewEngine));
router.use('/architecture', createServiceProxy('architecture', config.services.architectureAnalyzer));
router.use('/ai', createServiceProxy('ai', config.services.agenticAI));
router.use('/projects', createServiceProxy('projects', config.services.projectManager));

export { router as routes };