#!/usr/bin/env node
/* eslint-disable no-console */

/**
 * File Path Validation Script
 * 
 * This script checks for non-English characters in file paths to prevent
 * npm installation issues on Windows systems, particularly with Chinese
 * character paths that can cause ERESOLVE errors.
 */

const fs = require('fs');
const path = require('path');
const process = require('process');

// ANSI color codes for terminal output
const colors = {
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    reset: '\x1b[0m',
    bold: '\x1b[1m'
};

/**
 * Check if a string contains non-ASCII characters
 * @param {string} str - String to check
 * @returns {boolean} True if contains non-ASCII characters
 */
function containsNonAscii(str) {
    return Array.from(str).some(char => char.charCodeAt(0) > 127);
}

/**
 * Check if a path contains non-English characters
 * @param {string} filePath - File path to check
 * @returns {boolean} True if contains non-English characters
 */
function hasNonEnglishPath(filePath) {
    const pathSegments = filePath.split(/[/\\]/);
    return pathSegments.some(segment => containsNonAscii(segment));
}

/**
 * Get project root directory
 * @returns {string} Project root path
 */
function getProjectRoot() {
    return process.cwd();
}

/**
 * Recursively scan directory for files with non-English paths
 * @param {string} dir - Directory to scan
 * @param {Array} results - Array to store results
 * @returns {Array} Array of files with non-English paths
 */
function scanDirectory(dir, results = []) {
    try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        
        for (const entry of entries) {
            // Skip node_modules and hidden directories
            if (entry.name.startsWith('.') || entry.name === 'node_modules') {
                continue;
            }
            
            const fullPath = path.join(dir, entry.name);
            
            // Check if the path contains non-English characters
            if (hasNonEnglishPath(fullPath)) {
                results.push({
                    path: fullPath,
                    name: entry.name,
                    type: entry.isDirectory() ? 'directory' : 'file'
                });
            }
            
            // Recursively scan subdirectories
            if (entry.isDirectory()) {
                scanDirectory(fullPath, results);
            }
        }
    } catch {
        // Skip directories that can't be read
        console.warn(`${colors.yellow}Warning: Cannot read directory ${dir}${colors.reset}`);
    }
    
    return results;
}

/**
 * Display compliance report header
 */
function displayHeader() {
    console.log(`${colors.cyan}${colors.bold}`);
    console.log('╔══════════════════════════════════════════════════════════════╗');
    console.log('║                    Path Compliance Check                     ║');
    console.log('║                    AI Code Review Platform                   ║');
    console.log('╚══════════════════════════════════════════════════════════════╝');
    console.log(`${colors.reset}`);
}

/**
 * Display project information
 * @param {string} projectRoot - Project root directory
 */
function displayProjectInfo(projectRoot) {
    console.log(`${colors.blue}Project Root: ${colors.bold}${projectRoot}${colors.reset}`);
    console.log(`${colors.blue}Current Working Directory: ${colors.bold}${process.cwd()}${colors.reset}`);
    console.log('');
}

/**
 * Display scan results
 * @param {Array} results - Array of files with non-English paths
 */
function displayResults(results) {
    if (results.length === 0) {
        console.log(`${colors.green}✅ All file paths are compliant with English-only requirements.${colors.reset}`);
        console.log(`${colors.green}✅ No non-ASCII characters detected in file paths.${colors.reset}`);
        console.log('');
        console.log(`${colors.cyan}This ensures compatibility with npm installations and CI/CD pipelines.${colors.reset}`);
        return true;
    }
    
    console.log(`${colors.red}❌ Found ${results.length} file(s)/directory(ies) with non-English characters:${colors.reset}`);
    console.log('');
    
    results.forEach((result, index) => {
        const typeIcon = result.type === 'directory' ? '📁' : '📄';
        console.log(`${colors.red}${index + 1}. ${typeIcon} ${result.path}${colors.reset}`);
        console.log(`   Name: ${colors.yellow}${result.name}${colors.reset}`);
        console.log(`   Type: ${colors.cyan}${result.type}${colors.reset}`);
        console.log('');
    });
    
    console.log(`${colors.yellow}⚠️  Recommendations:${colors.reset}`);
    console.log('   1. Rename directories/files to use only ASCII characters');
    console.log('   2. Avoid spaces, special characters, and non-English text in paths');
    console.log('   3. Use hyphens (-) or underscores (_) instead of spaces');
    console.log('   4. Consider moving the project to a path without Chinese characters');
    console.log('');
    console.log(`${colors.red}⚠️  This may cause npm installation failures and CI/CD issues.${colors.reset}`);
    
    return false;
}

/**
 * Display compliance standards information
 */
function displayComplianceInfo() {
    console.log(`${colors.magenta}╔══════════════════════════════════════════════════════════════╗${colors.reset}`);
    console.log(`${colors.magenta}║                    Compliance Standards                      ║${colors.reset}`);
    console.log(`${colors.magenta}╠══════════════════════════════════════════════════════════════╣${colors.reset}`);
    console.log(`${colors.magenta}║ • File paths must contain only ASCII characters (0-127)       ║${colors.reset}`);
    console.log(`${colors.magenta}║ • No Chinese, Japanese, Korean, or other Unicode characters  ║${colors.reset}`);
    console.log(`${colors.magenta}║ • No special symbols or emojis in directory/file names       ║${colors.reset}`);
    console.log(`${colors.magenta}║ • Spaces should be replaced with hyphens or underscores      ║${colors.reset}`);
    console.log(`${colors.magenta}║ • Ensures compatibility with Windows, Linux, and macOS       ║${colors.reset}`);
    console.log(`${colors.magenta}║ • Prevents npm ERESOLVE and installation errors              ║${colors.reset}`);
    console.log(`${colors.magenta}╚══════════════════════════════════════════════════════════════╝${colors.reset}`);
    console.log('');
}

/**
 * Main execution function
 */
function main() {
    displayHeader();
    
    const projectRoot = getProjectRoot();
    displayProjectInfo(projectRoot);
    
    console.log(`${colors.cyan}Scanning for non-English file paths...${colors.reset}`);
    console.log('');
    
    const results = scanDirectory(projectRoot);
    const isCompliant = displayResults(results);
    
    displayComplianceInfo();
    
    if (!isCompliant) {
        console.log(`${colors.red}❌ Path compliance check failed. Please address the issues above.${colors.reset}`);
        console.log(`${colors.red}❌ npm installation may fail due to path encoding issues.${colors.reset}`);
        process.exit(1);
    } else {
        console.log(`${colors.green}✅ Path compliance check passed. Proceeding with installation.${colors.reset}`);
        process.exit(0);
    }
}

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
    console.error(`${colors.red}Unexpected error during path validation:${colors.reset}`, error);
    process.exit(1);
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
    console.error(`${colors.red}Unhandled promise rejection at:${colors.reset}`, promise, `${colors.red}reason:${colors.reset}`, reason);
    process.exit(1);
});

// Run the script
if (require.main === module) {
    main();
}

module.exports = {
    containsNonAscii,
    hasNonEnglishPath,
    scanDirectory,
    getProjectRoot
};
