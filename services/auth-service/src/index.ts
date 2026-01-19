import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { config } from './config';
import { logger } from './utils/logger';
import { errorHandler } from './middleware/errorHandler';
import { authRoutes } from './routes/auth';
import { healthRoutes } from './routes/health';
import { DatabaseService } from './services/database';
import { RedisService } from './services/redis';

const app = express();

// Security middleware
app.use(helmet());
app.use(cors({
  origin: config.cors.allowedOrigins,
  credentials: true,
}));

// Body parsing
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));

// Routes
app.use('/health', healthRoutes);
app.use('/api/auth', authRoutes);

// Error handling
app.use(errorHandler);

// Initialize services
const initializeServices = async (): Promise<void> => {
  try {
    await DatabaseService.initialize();
    await RedisService.initialize();
    logger.info('All services initialized successfully');
  } catch (error) {
    logger.error('Failed to initialize services:', error);
    process.exit(1);
  }
};

const server = app.listen(config.port, async () => {
  await initializeServices();
  logger.info(`Auth Service started on port ${config.port}`);
});

// Graceful shutdown
const gracefulShutdown = async (): Promise<void> => {
  logger.info('Shutting down gracefully...');
  
  server.close(async () => {
    try {
      await DatabaseService.close();
      await RedisService.close();
      logger.info('All services closed successfully');
      process.exit(0);
    } catch (error) {
      logger.error('Error during shutdown:', error);
      process.exit(1);
    }
  });
};

process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

export { app };