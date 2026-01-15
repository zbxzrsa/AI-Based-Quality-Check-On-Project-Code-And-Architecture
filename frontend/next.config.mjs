/** @type {import('next').NextConfig} */
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const nextConfig = {
    reactStrictMode: true,
    swcMinify: true,
    images: {
        domains: ['localhost'],
        formats: ['image/avif', 'image/webp'],
    },
    env: {
        NEXT_PUBLIC_API_URL: apiUrl,
    },
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: `${apiUrl}/:path*`,
            },
        ];
    },
};

export default nextConfig;
