import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { Providers } from '@/providers';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/components/theme-provider';
import { ClientToaster } from '@/components/providers/client-toaster';
import BackendStatusBanner from '@/components/common/backend-status';
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
    return (
        <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
            <head>
                {/* Critical CSS for first paint optimization (requirement 11.5) */}
                <style
                    dangerouslySetInnerHTML={{
                        __html: `
                            /* Critical layout styles for above-the-fold content */
                            * {
                                box-sizing: border-box;
                            }
                            
                            html {
                                -webkit-text-size-adjust: 100%;
                                -webkit-font-smoothing: antialiased;
                                -moz-osx-font-smoothing: grayscale;
                            }
                            
                            body {
                                margin: 0;
                                min-height: 100vh;
                            }
                            
                            /* Loading skeleton animation for initial render */
                            @keyframes skeleton-loading {
                                0% {
                                    background-position: 200% 0;
                                }
                                100% {
                                    background-position: -200% 0;
                                }
                            }
                            
                            .loading-skeleton {
                                background: linear-gradient(
                                    90deg,
                                    hsl(var(--muted)) 25%,
                                    hsl(var(--muted-foreground) / 0.1) 50%,
                                    hsl(var(--muted)) 75%
                                );
                                background-size: 200% 100%;
                                animation: skeleton-loading 1.5s ease-in-out infinite;
                            }
                            
                            /* Prevent layout shift during font loading */
                            .font-sans {
                                font-family: var(--font-inter), -apple-system, BlinkMacSystemFont, 'Segoe UI', 
                                    'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 
                                    'Helvetica Neue', sans-serif;
                            }
                            
                            .font-mono {
                                font-family: var(--font-jetbrains-mono), 'Courier New', monospace;
                            }
                            
                            /* Critical container styles */
                            .container {
                                width: 100%;
                                margin-left: auto;
                                margin-right: auto;
                                padding-left: 1rem;
                                padding-right: 1rem;
                            }
                            
                            @media (min-width: 640px) {
                                .container {
                                    max-width: 640px;
                                }
                            }
                            
                            @media (min-width: 768px) {
                                .container {
                                    max-width: 768px;
                                }
                            }
                            
                            @media (min-width: 1024px) {
                                .container {
                                    max-width: 1024px;
                                }
                            }
                            
                            @media (min-width: 1280px) {
                                .container {
                                    max-width: 1280px;
                                }
                            }
                            
                            /* Prevent flash of unstyled content */
                            [data-theme="dark"] {
                                color-scheme: dark;
                            }
                            
                            [data-theme="light"] {
                                color-scheme: light;
                            }
                        `,
                    }}
                />
            </head>
            <body className="min-h-screen bg-background font-sans antialiased">
                <ThemeProvider
                    attribute="class"
                    defaultTheme="system"
                    enableSystem
                    disableTransitionOnChange
                >
                    <Providers>
                        <AuthProvider>
                            {children}
                            <BackendStatusBanner />
                        </AuthProvider>
                    </Providers>
                    <ClientToaster />
                </ThemeProvider>
            </body>
        </html>
    );
}
