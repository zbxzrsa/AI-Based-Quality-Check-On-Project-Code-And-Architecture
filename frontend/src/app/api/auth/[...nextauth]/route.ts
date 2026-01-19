import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import type { NextAuthOptions } from 'next-auth';

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
          throw new Error('Email and password are required');
        }

        try {
          const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
          
          // Step 1: Authenticate and get tokens
          const loginRes = await fetch(`${backendUrl}/api/v1/auth/login`, {
            method: 'POST',
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
            headers: { 'Content-Type': 'application/json' },
          });

          if (!loginRes.ok) {
            const error = await loginRes.json().catch(() => ({}));
            throw new Error(error.detail || 'Authentication failed');
          }

          const authData = await loginRes.json();

          if (!authData.access_token) {
            throw new Error('Invalid response from authentication server');
          }

          // Step 2: Get user details using access token
          const meRes = await fetch(`${backendUrl}/api/v1/auth/me`, {
            headers: {
              'Authorization': `Bearer ${authData.access_token}`,
            },
          });

          if (!meRes.ok) {
            throw new Error('Failed to fetch user details');
          }

          const userData = await meRes.json();

          return {
            id: userData.id,
            email: userData.email,
            name: userData.full_name || userData.email.split('@')[0],
            role: userData.role,
            accessToken: authData.access_token,
            refreshToken: authData.refresh_token,
          };
        } catch (error) {
          console.error('Authentication error:', error);
          throw new Error(error instanceof Error ? error.message : 'Authentication failed');
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
      if (token && session.user) {
        session.user.id = token.id as string;
        session.user.email = token.email as string;
        session.user.name = token.name as string;
        session.user.role = token.role as string;
        session.user.accessToken = token.accessToken as string;
        session.user.refreshToken = token.refreshToken as string;
      }
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
