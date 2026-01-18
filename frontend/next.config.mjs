/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    images: {
        remotePatterns: [
            {
                protocol: 'http',
                hostname: 'localhost',
                port: '3000',
            },
            {
                protocol: 'http',
                hostname: 'localhost',
                port: '8000',
            },
        ],
        formats: ['image/avif', 'image/webp'],
    },
    // Production export configuration for static hosting
    output: 'export',
    distDir: 'dist',
    trailingSlash: true,
    experimental: {
        // Removed: appDir is not compatible with 'output: export' configuration
    },
};

export default nextConfig;
