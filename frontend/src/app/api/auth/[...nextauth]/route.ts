import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import type { NextAuthOptions } from 'next-auth';
import {
  authenticateUser,
  handleAuthError,
  getUserFriendlyErrorMessage,
  validateEnvironmentConfig,
} from '@/lib/auth';

// Validate environment configuration on startup
const envValidation = validateEnvironmentConfig();
if (!envValidation.valid && process.env.NODE_ENV === 'development') {
  console.warn('[NextAuth] Environment configuration issues:', envValidation.errors);
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          if (process.env.NODE_ENV === 'development') {
            console.error('[NextAuth] Missing credentials');
          }
          throw new Error('Email and password are required');
        }

        try {
          if (process.env.NODE_ENV === 'development') {
            console.log('[NextAuth] Starting authentication for:', credentials.email);
          }

          // Use the authentication service utility
          const user = await authenticateUser({
            username: credentials.email,
            password: credentials.password,
          });

          if (process.env.NODE_ENV === 'development') {
            console.log('[NextAuth] Authentication successful for:', user.email);
          }

          return {
            id: user.id,
            email: user.email || user.username,
            name: user.name || user.email?.split('@')[0] || user.username,
            role: user.role || 'user',
            accessToken: user.accessToken || '',
            refreshToken: user.refreshToken || '',
          };
        } catch (error) {
          const authError = handleAuthError(error);
          const userMessage = getUserFriendlyErrorMessage(authError);
          
          if (process.env.NODE_ENV === 'development') {
            console.error('[NextAuth] Authentication failed:', {
              type: authError.type,
              message: authError.message,
              statusCode: authError.statusCode,
            });
          }
          
          throw new Error(userMessage);
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.email = user.email;
        token.name = user.name;
        token.role = user.role;
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
      }
      return token;
    },
    async session({ session, token }) {
      // Ensure session and session.user exist before assigning properties
      if (!session || !token) {
        return session;
      }
      
      // Initialize user object if it doesn't exist
      if (!session.user) {
        session.user = {} as any;
      }
      
      session.user.id = token.id as string;
      session.user.email = token.email as string;
      session.user.name = token.name as string;
      session.user.role = token.role as string;
      session.user.accessToken = token.accessToken as string;
      session.user.refreshToken = token.refreshToken as string;
      
      return session;
    },
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  session: {
    strategy: 'jwt' as const,
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === 'development',
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
