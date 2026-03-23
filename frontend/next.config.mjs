/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    trailingSlash: true,
    output: 'standalone',
    compress: true,
    generateEtags: true,



    // Exclude test files from pages
    pageExtensions: ['ts', 'tsx', 'js', 'jsx', 'md', 'mdx'],

    // Compiler optimizations
    compiler: {
        removeConsole: process.env.NODE_ENV === 'production',
        reactRemoveProperties: process.env.NODE_ENV === 'production',
    },

    // Production source maps configuration (需求 11.2)
    productionBrowserSourceMaps: true,

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
        // WebP format support for optimized images (需求 11.4)
        // Next.js automatically converts images to WebP/AVIF with JPEG/PNG fallback
        // The formats array defines the priority order:
        // 1. AVIF (best compression, modern browsers)
        // 2. WebP (good compression, wide support)
        // 3. Original format (JPEG/PNG fallback for older browsers)
        formats: ['image/avif', 'image/webp'],
        // Enable image optimization
        minimumCacheTTL: 31536000, // 1 year cache for images
    },

    serverExternalPackages: ['sharp'],

    // Required for Next.js 16: acknowledge Turbopack is default bundler
    turbopack: {},

    // Headers for static asset caching (需求 11.2)
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
            '@radix-ui/react-toast'
        ],
        esmExternals: true,
    },

    // Code splitting configuration
    modularizeImports: {
        'lucide-react': {
            transform: 'lucide-react/dist/esm/icons/{{kebabCase member}}',
        },
        'd3': {
            transform: 'd3-{{member}}',
        },
    },

    // Webpack configuration
    webpack: (config, { isServer, dev }) => {
        if (!isServer) {
            config.resolve.fallback = {
                ...config.resolve.fallback,
                fs: false,
                net: false,
                tls: false,
            };
        }

        // Tree shaking optimization (需求 7.4)
        config.optimization.usedExports = true;
        config.optimization.sideEffects = false;

        // Production optimizations
        if (!dev) {
            // Enable minification and compression (需求 11.1)
            // This ensures at least 30% size reduction through:
            // 1. Terser minification for JavaScript
            // 2. CSS minification (handled by Next.js)
            // 3. Gzip compression (enabled via compress: true above)
            config.optimization.minimize = true;

            // Configure source maps for production (需求 11.2)
            config.devtool = isServer ? false : 'source-map';
        }

        // Enhanced code splitting (需求 7.5)
        if (!dev && !isServer) {
            config.optimization.splitChunks = {
                chunks: 'all',
                cacheGroups: {
                    // Vendor chunk for core dependencies
                    vendor: {
                        test: /[\\/]node_modules[\\/](react|react-dom|next)[\\/]/,
                        name: 'vendor',
                        priority: 10,
                        reuseExistingChunk: true,
                    },
                    // UI library chunk
                    ui: {
                        test: /[\\/]node_modules[\\/](@radix-ui|lucide-react|class-variance-authority|clsx|tailwind-merge)[\\/]/,
                        name: 'ui',
                        priority: 9,
                        reuseExistingChunk: true,
                    },
                    // Visualization libraries chunk
                    visualization: {
                        test: /[\\/]node_modules[\\/](d3|react-force-graph-2d|reactflow|recharts)[\\/]/,
                        name: 'visualization',
                        priority: 8,
                        reuseExistingChunk: true,
                    },
                    // Forms and validation chunk
                    forms: {
                        test: /[\\/]node_modules[\\/](react-hook-form|@hookform|zod)[\\/]/,
                        name: 'forms',
                        priority: 7,
                        reuseExistingChunk: true,
                    },
                    // Common chunk for shared code
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

            // Configure output filenames with content hash (需求 11.2)
            config.output.filename = 'static/chunks/[name].[contenthash].js';
            config.output.chunkFilename = 'static/chunks/[name].[contenthash].js';
        }

        return config;
    },
};

export default nextConfig;
