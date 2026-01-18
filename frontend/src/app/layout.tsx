import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { getServerSession } from 'next-auth/next';
import { authOptions } from './api/auth/[...nextauth]/route';
import { Providers } from '@/providers';
import { AuthProvider } from '@/contexts/AuthContext';
import '@/styles/globals.css';

const inter = Inter({
    subsets: ['latin'],
    variable: '--font-inter',
    display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
    subsets: ['latin'],
    variable: '--font-jetbrains-mono',
    display: 'swap',
});

export const metadata: Metadata = {
    title: 'AI Code Review Platform',
    description: 'AI-powered code review and architecture analysis platform',
    keywords: ['code review', 'AI', 'static analysis', 'architecture'],
    icons: {
        icon: '/favicon.svg',
    },
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const session = getServerSession(authOptions);
    
    return (
        <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
            <body className="min-h-screen bg-background font-sans antialiased">
                <Providers>
                    <AuthProvider>{children}</AuthProvider>
                </Providers>
            </body>
        </html>
    );
}
