/* eslint-disable no-console */
/**
 * Bundle Size Performance Tests
 * 
 * Tests to verify that the frontend bundle size meets performance requirements.
 * 
 * Requirements: 5.9, 10.8
 */

import { describe, test, expect } from '@jest/globals';
import fs from 'fs';
import path from 'path';

describe('Bundle Size Performance Tests', () => {
  const distPath = path.join(__dirname, '../../../dist');
  const maxInitialBundleSize = 500 * 1024; // 500KB requirement from 10.8
  const maxVisualizationChunkSize = 600 * 1024; // 600KB for visualization chunks

  // Check if this is a production build
  const isProductionBuild = fs.existsSync(distPath) && 
    fs.existsSync(path.join(distPath, 'static')) &&
    !fs.existsSync(path.join(distPath, 'static', 'webpack', 'webpack.hot-update.json'));

  if (!isProductionBuild) {
    test.skip('Bundle size tests require production build - run "npm run build" first', () => {
      // This test will be skipped
    });
  }

  /**
   * Helper function to get file size in bytes
   */
  function getFileSize(filePath: string): number {
    try {
      const stats = fs.statSync(filePath);
      return stats.size;
    } catch (error) {
      return 0;
    }
  }

  /**
   * Helper function to get all files in a directory recursively
   */
  function getAllFiles(dirPath: string, arrayOfFiles: string[] = []): string[] {
    if (!fs.existsSync(dirPath)) {
      return arrayOfFiles;
    }

    const files = fs.readdirSync(dirPath);

    files.forEach((file) => {
      const filePath = path.join(dirPath, file);
      if (fs.statSync(filePath).isDirectory()) {
        arrayOfFiles = getAllFiles(filePath, arrayOfFiles);
      } else {
        arrayOfFiles.push(filePath);
      }
    });

    return arrayOfFiles;
  }

  /**
   * Helper function to calculate total size of JS files
   */
  function calculateJSBundleSize(files: string[]): number {
    return files
      .filter((file) => file.endsWith('.js') && !file.includes('.map'))
      .reduce((total, file) => total + getFileSize(file), 0);
  }

  test('initial bundle size should be below 500KB', () => {
    if (!isProductionBuild) {
      console.warn('⚠️  Skipping: Production build required. Run "npm run build" first.');
      return;
    }

    // Skip if dist folder doesn't exist (not built yet)
    if (!fs.existsSync(distPath)) {
      console.warn('⚠️  Dist folder not found. Run "npm run build" first.');
      return;
    }

    const staticPath = path.join(distPath, 'static');
    if (!fs.existsSync(staticPath)) {
      console.warn('⚠️  Static folder not found in dist.');
      return;
    }

    // Get all JS files in the static folder
    const allFiles = getAllFiles(staticPath);
    const jsFiles = allFiles.filter(
      (file) => file.endsWith('.js') && !file.includes('.map')
    );

    // Calculate initial bundle size (vendor + ui + forms + common chunks)
    const initialChunks = jsFiles.filter(
      (file) =>
        file.includes('vendor') ||
        file.includes('ui') ||
        file.includes('forms') ||
        file.includes('common') ||
        file.includes('main') ||
        file.includes('webpack')
    );

    const initialBundleSize = calculateJSBundleSize(initialChunks);

    console.log(`📦 Initial bundle size: ${(initialBundleSize / 1024).toFixed(2)} KB`);
    console.log(`📊 Breakdown:`);
    initialChunks.forEach((file) => {
      const size = getFileSize(file);
      const fileName = path.basename(file);
      console.log(`   - ${fileName}: ${(size / 1024).toFixed(2)} KB`);
    });

    expect(initialBundleSize).toBeLessThanOrEqual(maxInitialBundleSize);
  });

  test('visualization chunks should be lazy-loaded', () => {
    if (!isProductionBuild) {
      console.warn('⚠️  Skipping: Production build required. Run "npm run build" first.');
      return;
    }

    if (!fs.existsSync(distPath)) {
      console.warn('⚠️  Dist folder not found. Run "npm run build" first.');
      return;
    }

    const staticPath = path.join(distPath, 'static');
    if (!fs.existsSync(staticPath)) {
      console.warn('⚠️  Static folder not found in dist.');
      return;
    }

    const allFiles = getAllFiles(staticPath);
    const jsFiles = allFiles.filter(
      (file) => file.endsWith('.js') && !file.includes('.map')
    );

    // Check for visualization chunks (should be separate from main bundle)
    const visualizationChunks = jsFiles.filter(
      (file) =>
        file.includes('visualization') ||
        file.includes('dependency-graph') ||
        file.includes('architecture-graph') ||
        file.includes('neo4j-graph') ||
        file.includes('d3') ||
        file.includes('reactflow')
    );

    console.log(`📊 Visualization chunks found: ${visualizationChunks.length}`);
    visualizationChunks.forEach((file) => {
      const size = getFileSize(file);
      const fileName = path.basename(file);
      console.log(`   - ${fileName}: ${(size / 1024).toFixed(2)} KB`);
    });

    // Verify that visualization chunks exist (lazy loading is working)
    expect(visualizationChunks.length).toBeGreaterThan(0);

    // Verify each visualization chunk is within reasonable size
    visualizationChunks.forEach((file) => {
      const size = getFileSize(file);
      expect(size).toBeLessThanOrEqual(maxVisualizationChunkSize);
    });
  });

  test('code splitting should create separate chunks for different routes', () => {
    if (!isProductionBuild) {
      console.warn('⚠️  Skipping: Production build required. Run "npm run build" first.');
      return;
    }

    if (!fs.existsSync(distPath)) {
      console.warn('⚠️  Dist folder not found. Run "npm run build" first.');
      return;
    }

    const staticPath = path.join(distPath, 'static');
    if (!fs.existsSync(staticPath)) {
      console.warn('⚠️  Static folder not found in dist.');
      return;
    }

    const allFiles = getAllFiles(staticPath);
    const jsFiles = allFiles.filter(
      (file) => file.endsWith('.js') && !file.includes('.map')
    );

    // Count unique chunks (should have multiple chunks for code splitting)
    const uniqueChunks = new Set(
      jsFiles.map((file) => {
        const fileName = path.basename(file);
        // Extract chunk name (before hash)
        const match = fileName.match(/^([a-z-]+)/);
        return match ? match[1] : fileName;
      })
    );

    console.log(`📦 Unique chunks created: ${uniqueChunks.size}`);
    console.log(`   Chunks: ${Array.from(uniqueChunks).join(', ')}`);

    // Should have at least 5 different chunks (vendor, ui, forms, common, + route chunks)
    expect(uniqueChunks.size).toBeGreaterThanOrEqual(5);
  });

  test('total bundle size should be reasonable', () => {
    if (!isProductionBuild) {
      console.warn('⚠️  Skipping: Production build required. Run "npm run build" first.');
      return;
    }

    if (!fs.existsSync(distPath)) {
      console.warn('⚠️  Dist folder not found. Run "npm run build" first.');
      return;
    }

    const staticPath = path.join(distPath, 'static');
    if (!fs.existsSync(staticPath)) {
      console.warn('⚠️  Static folder not found in dist.');
      return;
    }

    const allFiles = getAllFiles(staticPath);
    const totalBundleSize = calculateJSBundleSize(allFiles);

    console.log(`📦 Total bundle size: ${(totalBundleSize / 1024).toFixed(2)} KB`);

    // Total bundle should be under 2MB (reasonable for a full-featured app)
    const maxTotalBundleSize = 2 * 1024 * 1024; // 2MB
    expect(totalBundleSize).toBeLessThanOrEqual(maxTotalBundleSize);
  });

  test('CSS bundle size should be reasonable', () => {
    if (!isProductionBuild) {
      console.warn('⚠️  Skipping: Production build required. Run "npm run build" first.');
      return;
    }

    if (!fs.existsSync(distPath)) {
      console.warn('⚠️  Dist folder not found. Run "npm run build" first.');
      return;
    }

    const staticPath = path.join(distPath, 'static');
    if (!fs.existsSync(staticPath)) {
      console.warn('⚠️  Static folder not found in dist.');
      return;
    }

    const allFiles = getAllFiles(staticPath);
    const cssFiles = allFiles.filter((file) => file.endsWith('.css'));

    const totalCSSSize = cssFiles.reduce(
      (total, file) => total + getFileSize(file),
      0
    );

    console.log(`🎨 Total CSS size: ${(totalCSSSize / 1024).toFixed(2)} KB`);
    cssFiles.forEach((file) => {
      const size = getFileSize(file);
      const fileName = path.basename(file);
      console.log(`   - ${fileName}: ${(size / 1024).toFixed(2)} KB`);
    });

    // CSS should be under 200KB
    const maxCSSSize = 200 * 1024; // 200KB
    expect(totalCSSSize).toBeLessThanOrEqual(maxCSSSize);
  });

  test('no duplicate dependencies in chunks', () => {
    if (!isProductionBuild) {
      console.warn('⚠️  Skipping: Production build required. Run "npm run build" first.');
      return;
    }

    if (!fs.existsSync(distPath)) {
      console.warn('⚠️  Dist folder not found. Run "npm run build" first.');
      return;
    }

    const staticPath = path.join(distPath, 'static');
    if (!fs.existsSync(staticPath)) {
      console.warn('⚠️  Static folder not found in dist.');
      return;
    }

    const allFiles = getAllFiles(staticPath);
    const jsFiles = allFiles.filter(
      (file) => file.endsWith('.js') && !file.includes('.map')
    );

    // Check that React is only in vendor chunk
    const reactChunks = jsFiles.filter((file) => {
      const content = fs.readFileSync(file, 'utf-8');
      return content.includes('react') || content.includes('React');
    });

    console.log(`⚛️  React found in ${reactChunks.length} chunks`);

    // React should ideally be in only 1-2 chunks (vendor + maybe one more)
    // This is a soft check as some React code might be in other chunks
    expect(reactChunks.length).toBeLessThanOrEqual(3);
  });
});
