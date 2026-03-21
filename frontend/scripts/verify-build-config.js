#!/usr/bin/env node
/* eslint-disable no-console */

/**
 * Build configuration verification script.
 *
 * Verifies:
 * - Tree shaking overrides are production-only
 * - Code splitting is production-only
 * - Minification is production-only
 * - Static asset hashing and caching remain configured
 */

const fs = require('fs');
const path = require('path');

console.log('Verifying build configuration...\n');

let hasErrors = false;

console.log('Checking next.config.mjs...');
const configPath = path.join(__dirname, '..', 'next.config.mjs');
if (!fs.existsSync(configPath)) {
  console.error('ERROR: next.config.mjs not found');
  hasErrors = true;
} else {
  const configContent = fs.readFileSync(configPath, 'utf-8');

  if (
    configContent.includes('const isProductionBuild = !dev;') &&
    configContent.includes('config.optimization.usedExports = true;') &&
    configContent.includes('config.optimization.sideEffects = false;')
  ) {
    console.log('  OK: production-only tree shaking overrides configured');
  } else {
    console.error('  ERROR: production-only tree shaking overrides not configured');
    hasErrors = true;
  }

  if (
    configContent.includes('if (isProductionBuild && !isServer) {') &&
    configContent.includes('splitChunks')
  ) {
    console.log('  OK: production-only code splitting configured');
  } else {
    console.error('  ERROR: production-only code splitting not configured');
    hasErrors = true;
  }

  if (
    configContent.includes('if (isProductionBuild) {') &&
    configContent.includes('config.optimization.minimize = true;')
  ) {
    console.log('  OK: production-only minification configured');
  } else {
    console.error('  ERROR: production-only minification not configured');
    hasErrors = true;
  }

  if (configContent.includes('contenthash')) {
    console.log('  OK: content-hash filenames configured');
  } else {
    console.error('  ERROR: content-hash filenames not configured');
    hasErrors = true;
  }

  if (
    configContent.includes('productionBrowserSourceMaps') ||
    configContent.includes("'source-map'")
  ) {
    console.log('  OK: production source maps configured');
  } else {
    console.error('  ERROR: production source maps not configured');
    hasErrors = true;
  }

  if (configContent.includes('Cache-Control')) {
    console.log('  OK: cache headers configured');
  } else {
    console.error('  ERROR: cache headers not configured');
    hasErrors = true;
  }

  if (configContent.includes('formats') && configContent.includes('webp')) {
    console.log('  OK: image optimization formats configured');
  } else {
    console.error('  ERROR: image optimization formats not configured');
    hasErrors = true;
  }

  if (configContent.includes('compress: true')) {
    console.log('  OK: gzip compression enabled');
  } else {
    console.error('  ERROR: gzip compression not enabled');
    hasErrors = true;
  }
}

console.log('\nChecking package.json build scripts...');
const packagePath = path.join(__dirname, '..', 'package.json');
if (!fs.existsSync(packagePath)) {
  console.error('ERROR: package.json not found');
  hasErrors = true;
} else {
  const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf-8'));

  if (packageJson.scripts.build) {
    console.log('  OK: build script exists');
  } else {
    console.error('  ERROR: build script missing');
    hasErrors = true;
  }

  if (packageJson.scripts['build:production']) {
    console.log('  OK: production build script exists');
  } else {
    console.error('  ERROR: production build script missing');
    hasErrors = true;
  }
}

console.log('\nChecking documentation...');
const docPath = path.join(__dirname, '..', 'BUILD_OPTIMIZATION.md');
if (fs.existsSync(docPath)) {
  console.log('  OK: BUILD_OPTIMIZATION.md exists');
} else {
  console.error('  ERROR: BUILD_OPTIMIZATION.md missing');
  hasErrors = true;
}

console.log('\n' + '='.repeat(50));
if (hasErrors) {
  console.error('Build configuration verification failed');
  process.exit(1);
}

console.log('Build configuration verification passed');
console.log('\nYou can now run:');
console.log('  npm run build:webpack');
console.log('  npm run build:production');
