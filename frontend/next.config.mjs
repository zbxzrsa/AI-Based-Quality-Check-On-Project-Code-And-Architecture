/* global process */
/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    compress: true,
    generateEtags: true,

    // Exclude test files from pages.
    pageExtensions: ['ts', 'tsx', 'js', 'jsx', 'md', 'mdx'],

    // Compiler optimizations.
    compiler: {
        removeConsole: process.env.NODE_ENV === 'production',
        reactRemoveProperties: process.env.NODE_ENV === 'production',
    },

    // Production source maps configuration.
    productionBrowserSourceMaps: true,

    images: {
        remotePatterns: [
            {
                protocol: 'http',
                hostname: 'localhost',
                port: '6066',
            },
            {
                protocol: 'http',
                hostname: 'localhost',
                port: '8000',
            },
        ],
        // Next.js automatically converts images to AVIF or WebP when possible,
        // with the original format used as a fallback in older browsers.
        formats: ['image/avif', 'image/webp'],
        minimumCacheTTL: 31536000,
    },

    serverExternalPackages: ['sharp'],

    // Headers for static asset caching.
    async headers() {
        return [
            {
                source: '/static/:path*',
                headers: [
                    {
                        key: 'Cache-Control',
                        value: 'public, max-age=31536000, immutable',
                    },
                ],
            },
            {
                source: '/_next/static/:path*',
                headers: [
                    {
                        key: 'Cache-Control',
                        value: 'public, max-age=31536000, immutable',
                    },
                ],
            },
            {
                source: '/_next/image/:path*',
                headers: [
                    {
                        key: 'Cache-Control',
                        value: 'public, max-age=31536000, immutable',
                    },
                ],
            },
        ];
    },

    experimental: {
        optimizePackageImports: [
            '@radix-ui/react-icons',
            'lucide-react',
            'd3',
            'recharts',
            'react-force-graph-2d',
            'reactflow',
            '@radix-ui/react-avatar',
            '@radix-ui/react-checkbox',
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-label',
            '@radix-ui/react-progress',
            '@radix-ui/react-radio-group',
            '@radix-ui/react-scroll-area',
            '@radix-ui/react-select',
            '@radix-ui/react-separator',
            '@radix-ui/react-slot',
            '@radix-ui/react-switch',
            '@radix-ui/react-tabs',
            '@radix-ui/react-toast',
        ],
        esmExternals: true,
    },

    // Code splitting configuration.
    modularizeImports: {
        'lucide-react': {
            transform: 'lucide-react/dist/esm/icons/{{kebabCase member}}',
        },
        d3: {
            transform: 'd3-{{member}}',
        },
    },

    // Webpack configuration.
    webpack: (config, { isServer, dev }) => {
        const isProductionBuild = !dev;

        if (!isServer) {
            config.resolve.fallback = {
                ...config.resolve.fallback,
                fs: false,
                net: false,
                tls: false,
            };
        }

        if (isProductionBuild) {
            // Keep these webpack overrides out of development so they do not
            // conflict with Next.js 16's cacheUnaffected behavior.
            config.optimization.usedExports = true;
            config.optimization.sideEffects = false;
        }

        if (isProductionBuild) {
            // Production-only minification and browser source maps.
            config.optimization.minimize = true;
            config.devtool = isServer ? false : 'source-map';
        }

        if (isProductionBuild && !isServer) {
            config.optimization.splitChunks = {
                chunks: 'all',
                cacheGroups: {
                    vendor: {
                        test: /[\\/]node_modules[\\/](react|react-dom|next)[\\/]/,
                        name: 'vendor',
                        priority: 10,
                        reuseExistingChunk: true,
                    },
                    ui: {
                        test: /[\\/]node_modules[\\/](@radix-ui|lucide-react|class-variance-authority|clsx|tailwind-merge)[\\/]/,
                        name: 'ui',
                        priority: 9,
                        reuseExistingChunk: true,
                    },
                    visualization: {
                        test: /[\\/]node_modules[\\/](d3|react-force-graph-2d|reactflow|recharts)[\\/]/,
                        name: 'visualization',
                        priority: 8,
                        reuseExistingChunk: true,
                    },
                    forms: {
                        test: /[\\/]node_modules[\\/](react-hook-form|@hookform|zod)[\\/]/,
                        name: 'forms',
                        priority: 7,
                        reuseExistingChunk: true,
                    },
                    common: {
                        minChunks: 2,
                        priority: 5,
                        reuseExistingChunk: true,
                        name: 'common',
                    },
                },
                maxInitialRequests: 25,
                maxAsyncRequests: 25,
                minSize: 20000,
            };

            config.output.filename = 'static/chunks/[name].[contenthash].js';
            config.output.chunkFilename = 'static/chunks/[name].[contenthash].js';
        }

        return config;
    },
};

export default nextConfig;
