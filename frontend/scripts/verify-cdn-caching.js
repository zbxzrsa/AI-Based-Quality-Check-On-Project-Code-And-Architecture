#!/usr/bin/env node

/**
 * CDN and Caching Configuration Verification Script
 * 
 * This script verifies that CDN and caching strategies are properly configured.
 * It checks:
 * 1. Cache headers configuration in next.config.mjs
 * 2. Content-hash filenames in build output
 * 3. Critical CSS inlining in layout
 * 4. CDN environment variables
 * 
 * Usage: node scripts/verify-cdn-caching.js
 */

const fs = require('fs');
const path = require('path');

// ANSI color codes for terminal output
const colors = {
    reset: '\x1b[0m',
    green: '\x1b[32m',
    red: '\x1b[31m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m',
};

function log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

function checkFile(filePath, description) {
    const fullPath = path.join(process.cwd(), filePath);
    if (fs.existsSync(fullPath)) {
        log(`✓ ${description}`, 'green');
        return true;
    } else {
        log(`✗ ${description}`, 'red');
        return false;
    }
}

function checkFileContent(filePath, pattern, description) {
    const fullPath = path.join(process.cwd(), filePath);
    if (!fs.existsSync(fullPath)) {
        log(`✗ ${description} - File not found: ${filePath}`, 'red');
        return false;
    }

    const content = fs.readFileSync(fullPath, 'utf8');
    const regex = new RegExp(pattern);
    
    if (regex.test(content)) {
        log(`✓ ${description}`, 'green');
        return true;
    } else {
        log(`✗ ${description}`, 'red');
        return false;
    }
}

function main() {
    log('\n=== CDN and Caching Configuration Verification ===\n', 'cyan');

    let allChecks = true;

    // Check 1: Next.js configuration file exists
    log('1. Checking Next.js Configuration...', 'blue');
    allChecks &= checkFile('next.config.mjs', 'next.config.mjs exists');

    // Check 2: Cache headers configuration
    log('\n2. Checking Cache Headers Configuration...', 'blue');
    allChecks &= checkFileContent(
        'next.config.mjs',
        'async headers\\(\\)',
        'Cache headers function defined'
    );
    allChecks &= checkFileContent(
        'next.config.mjs',
        'max-age=31536000',
        '1-year cache duration configured'
    );
    allChecks &= checkFileContent(
        'next.config.mjs',
        'immutable',
        'Immutable cache directive configured'
    );
    allChecks &= checkFileContent(
        'next.config.mjs',
        '/_next/static/:path\\*',
        'Static assets cache headers configured'
    );
    allChecks &= checkFileContent(
        'next.config.mjs',
        '/_next/image/:path\\*',
        'Image cache headers configured'
    );

    // Check 3: Content-hash configuration
    log('\n3. Checking Content-Hash Configuration...', 'blue');
    allChecks &= checkFileContent(
        'next.config.mjs',
        '\\[contenthash\\]',
        'Content-hash filenames configured'
    );

    // Check 4: Compression configuration
    log('\n4. Checking Compression Configuration...', 'blue');
    allChecks &= checkFileContent(
        'next.config.mjs',
        'compress:\\s*true',
        'Gzip compression enabled'
    );

    // Check 5: Critical CSS inlining
    log('\n5. Checking Critical CSS Inlining...', 'blue');
    allChecks &= checkFileContent(
        'src/app/layout.tsx',
        'dangerouslySetInnerHTML',
        'Critical CSS inline styles present'
    );
    allChecks &= checkFileContent(
        'src/app/layout.tsx',
        'loading-skeleton',
        'Loading skeleton styles defined'
    );
    allChecks &= checkFileContent(
        'src/app/layout.tsx',
        'Critical CSS for first paint',
        'Critical CSS comment present'
    );

    // Check 6: Font optimization
    log('\n6. Checking Font Optimization...', 'blue');
    allChecks &= checkFileContent(
        'src/app/layout.tsx',
        "display:\\s*['\"]swap['\"]",
        'Font display swap configured'
    );
    allChecks &= checkFileContent(
        'src/app/layout.tsx',
        'next/font/google',
        'Google Fonts optimization enabled'
    );

    // Check 7: Documentation
    log('\n7. Checking Documentation...', 'blue');
    allChecks &= checkFile('CDN_AND_CACHING.md', 'CDN and Caching documentation exists');
    allChecks &= checkFile('BUILD_OPTIMIZATION.md', 'Build optimization documentation exists');

    // Check 8: Environment configuration
    log('\n8. Checking Environment Configuration...', 'blue');
    const envExamplePath = '.env.production.example';
    if (checkFile(envExamplePath, 'Production environment example exists')) {
        allChecks &= checkFileContent(
            envExamplePath,
            'NEXT_PUBLIC_CDN_URL',
            'CDN URL environment variable documented'
        );
    } else {
        allChecks = false;
    }

    // Check 9: Image optimization
    log('\n9. Checking Image Optimization...', 'blue');
    allChecks &= checkFileContent(
        'next.config.mjs',
        'formats:\\s*\\[',
        'Image formats configuration present'
    );
    allChecks &= checkFileContent(
        'next.config.mjs',
        'image/webp',
        'WebP format enabled'
    );

    // Check 10: Build output verification (if .next exists)
    log('\n10. Checking Build Output (if available)...', 'blue');
    const buildDir = path.join(process.cwd(), '.next');
    if (fs.existsSync(buildDir)) {
        const staticDir = path.join(buildDir, 'static');
        if (fs.existsSync(staticDir)) {
            log('✓ Build output directory exists', 'green');
            
            // Check for content-hashed files
            const chunksDir = path.join(staticDir, 'chunks');
            if (fs.existsSync(chunksDir)) {
                const files = fs.readdirSync(chunksDir);
                const hashedFiles = files.filter(f => /\.[a-f0-9]{8,}\.(js|css)$/.test(f));
                
                if (hashedFiles.length > 0) {
                    log(`✓ Found ${hashedFiles.length} content-hashed files`, 'green');
                } else {
                    log('⚠ No content-hashed files found in build output', 'yellow');
                    log('  Run "npm run build" to generate production build', 'yellow');
                }
            }
        } else {
            log('⚠ Build static directory not found', 'yellow');
            log('  Run "npm run build" to generate production build', 'yellow');
        }
    } else {
        log('⚠ Build output not found (.next directory)', 'yellow');
        log('  Run "npm run build" to generate production build', 'yellow');
    }

    // Summary
    log('\n=== Verification Summary ===\n', 'cyan');
    
    if (allChecks) {
        log('✓ All CDN and caching configurations are properly set up!', 'green');
        log('\nNext steps:', 'blue');
        log('1. Run "npm run build" to generate production build', 'reset');
        log('2. Deploy to your hosting platform (Vercel, AWS, etc.)', 'reset');
        log('3. Configure CDN (CloudFront, Cloudflare, etc.) if not using Vercel', 'reset');
        log('4. Verify cache headers in production using browser DevTools', 'reset');
        log('5. Run Lighthouse audit to verify performance improvements', 'reset');
        return 0;
    } else {
        log('✗ Some checks failed. Please review the output above.', 'red');
        log('\nRefer to CDN_AND_CACHING.md for detailed configuration instructions.', 'yellow');
        return 1;
    }
}

// Run the verification
const exitCode = main();
process.exit(exitCode);
