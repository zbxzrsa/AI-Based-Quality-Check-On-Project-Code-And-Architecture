import { Router, Request, Response } from 'express';
import crypto from 'crypto';
import axios from 'axios';
import { config } from '../config';
import { logger } from '../utils/logger';
import { GitHubWebhookPayload } from '@shared/types';

const router = Router();

// Middleware to verify GitHub webhook signature
const verifyGitHubSignature = (req: Request, res: Response, next: Function): void => {
  const signature = req.headers['x-hub-signature-256'] as string;
  const payload = JSON.stringify(req.body);
  
  if (!signature) {
    res.status(401).json({ error: 'Missing signature' });
    return;
  }

  const expectedSignature = `sha256=${crypto
    .createHmac('sha256', config.github.webhookSecret)
    .update(payload)
    .digest('hex')}`;

  if (!crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expectedSignature))) {
    res.status(401).json({ error: 'Invalid signature' });
    return;
  }

  next();
};

// GitHub webhook endpoint
router.post('/github', verifyGitHubSignature, async (req: Request, res: Response): Promise<void> => {
  try {
    const event = req.headers['x-github-event'] as string;
    const payload: GitHubWebhookPayload = req.body;

    logger.info('Received GitHub webhook:', {
      event,
      action: payload.action,
      repository: payload.repository?.full_name,
      pullRequest: payload.pull_request?.number,
    });

    // Forward webhook to code review engine
    const response = await axios.post(
      `${config.services.codeReviewEngine}/api/webhooks/github`,
      {
        event,
        payload,
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'X-GitHub-Event': event,
        },
        timeout: 30000, // 30 seconds timeout for webhook processing
      }
    );

    logger.info('Webhook processed successfully:', {
      event,
      repository: payload.repository?.full_name,
      status: response.status,
    });

    res.status(200).json({ message: 'Webhook processed successfully' });
  } catch (error) {
    logger.error('Webhook processing error:', error);

    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500;
      res.status(status).json({
        error: 'Failed to process webhook',
        message: error.message,
        retryable: status >= 500,
      });
      return;
    }

    res.status(500).json({
      error: 'Internal server error',
      message: 'Failed to process webhook',
      retryable: true,
    });
  }
});

export { router as webhookRoutes };
