/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    swcMinify: true,
    images: {
        domains: ['localhost'],
        formats: ['image/avif', 'image/webp'],
    },
    // Server-side only configuration (not exposed to client)
    serverRuntimeConfig: {
        // These secrets are only available server-side
        jwtSecret: process.env.JWT_SECRET,
        githubToken: process.env.GITHUB_TOKEN,
        githubWebhookSecret: process.env.GITHUB_WEBHOOK_SECRET,
    },
    // Client-side safe configuration
    publicRuntimeConfig: {
        apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
    },
    // Production export configuration for static hosting
    output: 'export',
    distDir: 'dist',
    trailingSlash: true,
    // Disable server-side rendering for static export
    experimental: {
        appDir: true,
    },
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/:path*`,
            },
        ];
    },
};

export default nextConfig;
