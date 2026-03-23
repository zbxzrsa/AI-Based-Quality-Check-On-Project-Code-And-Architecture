#!/usr/bin/env node

/**
 * Build Configuration Verification Script
 * 
 * This script verifies that the build system is properly configured
 * according to the requirements:
 * - 7.4: Tree Shaking enabled
 * - 7.5: Code splitting for each page
 * - 11.1: Minification and compression
 * - 11.2: Content hash filenames for static assets
 */

const fs = require('fs');
const path = require('path');

console.log('🔍 Verifying Build Configuration...\n');

let hasErrors = false;

// Check 1: Verify next.config.mjs exists and has required settings
console.log('✓ Checking next.config.mjs...');
const configPath = path.join(__dirname, '..', 'next.config.mjs');
if (!fs.existsSync(configPath)) {
  console.error('❌ next.config.mjs not found');
  hasErrors = true;
} else {
  const configContent = fs.readFileSync(configPath, 'utf-8');
  
  // Check for Tree Shaking (需求 7.4)
  if (configContent.includes('usedExports') && configContent.includes('sideEffects')) {
    console.log('  ✓ Tree Shaking enabled (需求 7.4)');
  } else {
    console.error('  ❌ Tree Shaking not properly configured');
    hasErrors = true;
  }
  
  // Check for Code Splitting (需求 7.5)
  if (configContent.includes('splitChunks')) {
    console.log('  ✓ Code splitting configured (需求 7.5)');
  } else {
    console.error('  ❌ Code splitting not configured');
    hasErrors = true;
  }
  
  // Check for Minification (需求 11.1)
  if (configContent.includes('minimize')) {
    console.log('  ✓ Minification enabled (需求 11.1)');
  } else {
    console.error('  ❌ Minification not configured');
    hasErrors = true;
  }
  
  // Check for Content Hash (需求 11.2)
  if (configContent.includes('contenthash')) {
    console.log('  ✓ Content hash filenames configured (需求 11.2)');
  } else {
    console.error('  ❌ Content hash filenames not configured');
    hasErrors = true;
  }
  
  // Check for Source Maps (需求 11.2)
  if (configContent.includes('productionBrowserSourceMaps') || configContent.includes('source-map')) {
    console.log('  ✓ Production source maps enabled (需求 11.2)');
  } else {
    console.error('  ❌ Production source maps not configured');
    hasErrors = true;
  }
  
  // Check for Cache Headers (需求 11.2)
  if (configContent.includes('Cache-Control')) {
    console.log('  ✓ Cache headers configured (需求 11.2)');
  } else {
    console.error('  ❌ Cache headers not configured');
    hasErrors = true;
  }
  
  // Check for Image Optimization (需求 11.4)
  if (configContent.includes('formats') && configContent.includes('webp')) {
    console.log('  ✓ WebP image format configured (需求 11.4)');
  } else {
    console.error('  ❌ WebP image format not configured');
    hasErrors = true;
  }
  
  // Check for Compression (需求 11.1)
  if (configContent.includes('compress: true')) {
    console.log('  ✓ Gzip compression enabled (需求 11.1)');
  } else {
    console.error('  ❌ Gzip compression not enabled');
    hasErrors = true;
  }
}

// Check 2: Verify package.json has build scripts
console.log('\n✓ Checking package.json build scripts...');
const packagePath = path.join(__dirname, '..', 'package.json');
if (!fs.existsSync(packagePath)) {
  console.error('❌ package.json not found');
  hasErrors = true;
} else {
  const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf-8'));
  
  if (packageJson.scripts.build) {
    console.log('  ✓ Build script exists');
  } else {
    console.error('  ❌ Build script missing');
    hasErrors = true;
  }
  
  if (packageJson.scripts['build:production']) {
    console.log('  ✓ Production build script exists');
  } else {
    console.error('  ❌ Production build script missing');
    hasErrors = true;
  }
}

// Check 3: Verify documentation exists
console.log('\n✓ Checking documentation...');
const docPath = path.join(__dirname, '..', 'BUILD_OPTIMIZATION.md');
if (fs.existsSync(docPath)) {
  console.log('  ✓ BUILD_OPTIMIZATION.md exists');
} else {
  console.error('  ❌ BUILD_OPTIMIZATION.md missing');
  hasErrors = true;
}

// Summary
console.log('\n' + '='.repeat(50));
if (hasErrors) {
  console.error('❌ Build configuration verification FAILED');
  console.error('Please fix the errors above before proceeding.');
  process.exit(1);
} else {
  console.log('✅ Build configuration verification PASSED');
  console.log('\nAll required optimizations are properly configured:');
  console.log('  • Tree Shaking (需求 7.4)');
  console.log('  • Code Splitting (需求 7.5)');
  console.log('  • Minification (需求 11.1)');
  console.log('  • Gzip Compression (需求 11.1)');
  console.log('  • Content Hash Filenames (需求 11.2)');
  console.log('  • Production Source Maps (需求 11.2)');
  console.log('  • Cache Headers (需求 11.2)');
  console.log('  • WebP Image Optimization (需求 11.4)');
  console.log('\nYou can now run:');
  console.log('  npm run build:webpack    - Build with webpack');
  console.log('  npm run build:production - Production build');
}
