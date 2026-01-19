import { Router } from 'express';
import { body, validationResult } from 'express-validator';
import { AuthenticationService } from '../services/authentication';
import { UserService } from '../services/user';
import { AuditService } from '../services/audit';
import { authenticateToken, extractClientInfo } from '../middleware/auth';
import { logger } from '../utils/logger';

const router = Router();
const authService = new AuthenticationService();

// Apply client info extraction to all routes
router.use(extractClientInfo);

/**
 * POST /login - Authenticate user and return JWT token
 */
router.post('/login', [
  body('email').isEmail().normalizeEmail(),
  body('password').isLength({ min: 1 }).withMessage('Password is required'),
], async (req, res) => {
  try {
    // Check validation errors
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation Error',
        details: errors.array(),
      });
    }

    const { email, password } = req.body;
    const clientInfo = (req as any).clientInfo;

    // Authenticate user
    const token = await authService.authenticate(
      { email, password },
      clientInfo.ipAddress,
      clientInfo.userAgent
    );

    logger.info('User logged in successfully:', email);

    res.json({
      success: true,
      token: {
        userId: token.userId,
        roles: token.roles,
        permissions: token.permissions,
        expiresAt: token.expiresAt,
      },
      refreshToken: token.refreshToken,
    });
  } catch (error) {
    logger.error('Login error:', error);
    res.status(401).json({
      error: 'Authentication Failed',
      message: error instanceof Error ? error.message : 'Invalid credentials',
    });
  }
});

/**
 * POST /logout - Revoke user token
 */
router.post('/logout', authenticateToken, async (req, res) => {
  try {
    const clientInfo = (req as any).clientInfo;
    
    // Create token object from auth context
    const token = {
      userId: req.auth!.userId,
      roles: req.auth!.roles,
      permissions: req.auth!.permissions,
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // Placeholder
      refreshToken: req.body.refreshToken || '',
    };

    await authService.revokeToken(token, clientInfo.ipAddress, clientInfo.userAgent);

    logger.info('User logged out successfully:', req.auth!.userId);

    res.json({
      success: true,
      message: 'Logged out successfully',
    });
  } catch (error) {
    logger.error('Logout error:', error);
    res.status(500).json({
      error: 'Logout Failed',
      message: 'Failed to logout user',
    });
  }
});

/**
 * POST /validate - Validate JWT token
 */
router.post('/validate', async (req, res) => {
  try {
    const authHeader = req.headers.authorization;
    const token = await authService.verifyAuthorizationHeader(authHeader);

    if (!token) {
      return res.status(401).json({
        valid: false,
        error: 'Invalid or expired token',
      });
    }

    res.json({
      valid: true,
      token: {
        userId: token.userId,
        roles: token.roles,
        permissions: token.permissions,
        expiresAt: token.expiresAt,
      },
    });
  } catch (error) {
    logger.error('Token validation error:', error);
    res.status(401).json({
      valid: false,
      error: 'Token validation failed',
    });
  }
});

/**
 * POST /refresh - Refresh JWT token using refresh token
 */
router.post('/refresh', [
  body('refreshToken').isLength({ min: 1 }).withMessage('Refresh token is required'),
], async (req, res) => {
  try {
    // Check validation errors
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation Error',
        details: errors.array(),
      });
    }

    const { refreshToken } = req.body;
    const clientInfo = (req as any).clientInfo;

    const newToken = await authService.refreshToken(
      refreshToken,
      clientInfo.ipAddress,
      clientInfo.userAgent
    );

    logger.info('Token refreshed successfully for user:', newToken.userId);

    res.json({
      success: true,
      token: {
        userId: newToken.userId,
        roles: newToken.roles,
        permissions: newToken.permissions,
        expiresAt: newToken.expiresAt,
      },
      refreshToken: newToken.refreshToken,
    });
  } catch (error) {
    logger.error('Token refresh error:', error);
    res.status(401).json({
      error: 'Token Refresh Failed',
      message: error instanceof Error ? error.message : 'Failed to refresh token',
    });
  }
});

/**
 * POST /register - Register new user (admin only)
 */
router.post('/register', [
  authenticateToken,
  body('email').isEmail().normalizeEmail(),
  body('name').isLength({ min: 1 }).withMessage('Name is required'),
  body('password').isLength({ min: 8 }).withMessage('Password must be at least 8 characters'),
  body('roles').optional().isArray().withMessage('Roles must be an array'),
], async (req, res) => {
  try {
    // Check validation errors
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation Error',
        details: errors.array(),
      });
    }

    // Check if user has admin role
    if (!req.auth!.roles.includes('administrator')) {
      return res.status(403).json({
        error: 'Forbidden',
        message: 'Only administrators can register new users',
      });
    }

    const { email, name, password, roles } = req.body;
    const clientInfo = (req as any).clientInfo;

    const user = await UserService.createUser({
      email,
      name,
      password,
      roles: roles || ['programmer'],
    });

    // Log account creation
    await AuditService.logAccountCreation(
      user.id,
      email,
      clientInfo.ipAddress,
      clientInfo.userAgent
    );

    logger.info('New user registered:', email);

    res.status(201).json({
      success: true,
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        roles: user.roles.map(r => r.name),
      },
    });
  } catch (error) {
    logger.error('User registration error:', error);
    res.status(400).json({
      error: 'Registration Failed',
      message: error instanceof Error ? error.message : 'Failed to register user',
    });
  }
});

/**
 * GET /me - Get current user information
 */
router.get('/me', authenticateToken, async (req, res) => {
  try {
    const user = await UserService.getUserById(req.auth!.userId);
    if (!user) {
      return res.status(404).json({
        error: 'User Not Found',
        message: 'User account not found',
      });
    }

    res.json({
      success: true,
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        roles: user.roles.map(r => r.name),
        preferences: user.preferences,
        lastLogin: user.lastLogin,
      },
    });
  } catch (error) {
    logger.error('Get user info error:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to get user information',
    });
  }
});

/**
 * PUT /me - Update current user information
 */
router.put('/me', [
  authenticateToken,
  body('name').optional().isLength({ min: 1 }).withMessage('Name cannot be empty'),
  body('preferences').optional().isObject().withMessage('Preferences must be an object'),
], async (req, res) => {
  try {
    // Check validation errors
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: 'Validation Error',
        details: errors.array(),
      });
    }

    const { name, preferences } = req.body;

    const updatedUser = await UserService.updateUser(req.auth!.userId, {
      name,
      preferences,
    });

    logger.info('User updated profile:', req.auth!.userId);

    res.json({
      success: true,
      user: {
        id: updatedUser.id,
        email: updatedUser.email,
        name: updatedUser.name,
        roles: updatedUser.roles.map(r => r.name),
        preferences: updatedUser.preferences,
      },
    });
  } catch (error) {
    logger.error('Update user error:', error);
    res.status(500).json({
      error: 'Update Failed',
      message: error instanceof Error ? error.message : 'Failed to update user',
    });
  }
});

/**
 * GET /audit - Get audit logs for current user
 */
router.get('/audit', authenticateToken, async (req, res) => {
  try {
    const limit = parseInt(req.query.limit as string) || 50;
    const offset = parseInt(req.query.offset as string) || 0;

    const auditLogs = await AuditService.getUserAuditLogs(
      req.auth!.userId,
      limit,
      offset
    );

    res.json({
      success: true,
      logs: auditLogs,
      pagination: {
        limit,
        offset,
        total: auditLogs.length,
      },
    });
  } catch (error) {
    logger.error('Get audit logs error:', error);
    res.status(500).json({
      error: 'Internal Server Error',
      message: 'Failed to get audit logs',
    });
  }
});

export { router as authRoutes };