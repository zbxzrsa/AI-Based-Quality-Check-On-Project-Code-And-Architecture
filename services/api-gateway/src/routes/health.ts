import { Router, Request, Response } from 'express';
import axios from 'axios';
import { config } from '../config';
import { logger } from '../utils/logger';

const router = Router();

interface ServiceHealth {
  name: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  responseTime?: number;
  error?: string;
}

const checkServiceHealth = async (name: string, url: string): Promise<ServiceHealth> => {
  const startTime = Date.now();
  
  try {
    const response = await axios.get(`${url}/health`, {
      timeout: 5000,
    });
    
    const responseTime = Date.now() - startTime;
    
    return {
      name,
      status: response.status === 200 ? 'healthy' : 'unhealthy',
      responseTime,
    };
  } catch (error) {
    const responseTime = Date.now() - startTime;
    
    return {
      name,
      status: 'unhealthy',
      responseTime,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
};

router.get('/', async (req: Request, res: Response): Promise<void> => {
  try {
    const healthChecks = await Promise.all([
      checkServiceHealth('auth-service', config.services.authService),
      checkServiceHealth('code-review-engine', config.services.codeReviewEngine),
      checkServiceHealth('architecture-analyzer', config.services.architectureAnalyzer),
      checkServiceHealth('agentic-ai', config.services.agenticAI),
      checkServiceHealth('project-manager', config.services.projectManager),
    ]);

    const allHealthy = healthChecks.every(check => check.status === 'healthy');
    const overallStatus = allHealthy ? 'healthy' : 'degraded';

    const response = {
      status: overallStatus,
      timestamp: new Date().toISOString(),
      service: 'api-gateway',
      version: '1.0.0',
      services: healthChecks,
    };

    res.status(allHealthy ? 200 : 503).json(response);
  } catch (error) {
    logger.error('Health check error:', error);
    
    res.status(500).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      service: 'api-gateway',
      version: '1.0.0',
      error: 'Health check failed',
    });
  }
});

export { router as healthCheck };