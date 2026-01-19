import { Router, Request, Response } from 'express';
import { DatabaseService } from '../services/database';
import { RedisService } from '../services/redis';
import { logger } from '../utils/logger';

const router = Router();

router.get('/', async (req: Request, res: Response): Promise<void> => {
  try {
    // Check database connection
    const dbHealthy = await DatabaseService.healthCheck();
    
    // Check Redis connection
    const redisHealthy = await RedisService.healthCheck();

    const allHealthy = dbHealthy && redisHealthy;

    const response = {
      status: allHealthy ? 'healthy' : 'unhealthy',
      timestamp: new Date().toISOString(),
      service: 'auth-service',
      version: '1.0.0',
      checks: {
        database: dbHealthy ? 'healthy' : 'unhealthy',
        redis: redisHealthy ? 'healthy' : 'unhealthy',
      },
    };

    res.status(allHealthy ? 200 : 503).json(response);
  } catch (error) {
    logger.error('Health check error:', error);
    
    res.status(500).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      service: 'auth-service',
      version: '1.0.0',
      error: 'Health check failed',
    });
  }
});

export { router as healthRoutes };