import { AuthContext } from '@shared/types';

declare global {
  namespace Express {
    interface Request {
      auth?: AuthContext;
    }
  }
}
