import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import QueryClientWrapper from '@/components/QueryClientWrapper';
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
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
            <body className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 font-sans antialiased dark:from-slate-900 dark:to-slate-800">
                <QueryClientWrapper>
                    {children}
                </QueryClientWrapper>
            </body>
        </html>
    );
}
