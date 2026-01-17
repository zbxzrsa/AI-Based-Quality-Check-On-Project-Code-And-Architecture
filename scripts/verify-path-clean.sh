#!/bin/bash

# Verify Path Clean Status
# This script checks if your project is free from Chinese path references and ready for CI/CD

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get current npm configuration
get_npm_config() {
    npm config get "$1" 2>/dev/null || echo "undefined"
}

# Function to check for Chinese characters in paths
check_chinese_paths() {
    local path="$1"
    if [[ "$path" =~ [\u4e00-\u9fff] ]]; then
        return 0  # Found Chinese characters
    else
        return 1  # No Chinese characters
    fi
}

print_status "Verifying project Path-Clean status..."
print_status "Current working directory: $(pwd)"
echo ""

# 1. Check npm configurations
print_status "1. Checking npm configurations..."
NPM_CACHE=$(get_npm_config cache)
NPM_PREFIX=$(get_npm_config prefix)
NPM_TMP=$(get_npm_config tmp)
NPM_CONFIG_CACHE=$(get_npm_config npm_config_cache)

echo "Current npm configurations:"
echo "  cache: $NPM_CACHE"
echo "  prefix: $NPM_PREFIX"
echo "  tmp: $NPM_TMP"
echo "  npm_config_cache: $NPM_CONFIG_CACHE"
echo ""

# Check for Chinese characters
CHINESE_FOUND=false

if check_chinese_paths "$NPM_CACHE"; then
    print_error "❌ Chinese characters found in npm cache path: $NPM_CACHE"
    CHINESE_FOUND=true
else
    print_success "✅ npm cache path is clean: $NPM_CACHE"
fi

if check_chinese_paths "$NPM_PREFIX"; then
    print_error "❌ Chinese characters found in npm prefix path: $NPM_PREFIX"
    CHINESE_FOUND=true
else
    print_success "✅ npm prefix path is clean: $NPM_PREFIX"
fi

if check_chinese_paths "$NPM_TMP"; then
    print_error "❌ Chinese characters found in npm tmp path: $NPM_TMP"
    CHINESE_FOUND=true
else
    print_success "✅ npm tmp path is clean: $NPM_TMP"
fi

if check_chinese_paths "$NPM_CONFIG_CACHE"; then
    print_error "❌ Chinese characters found in npm_config_cache: $NPM_CONFIG_CACHE"
    CHINESE_FOUND=true
else
    print_success "✅ npm_config_cache is clean: $NPM_CONFIG_CACHE"
fi

echo ""

# 2. Check environment variables
print_status "2. Checking environment variables..."
ENV_VARS=("NPM_CONFIG_CACHE" "NPM_CONFIG_PREFIX" "NPM_CONFIG_TMP" "NPM_CONFIG_REGISTRY")

for var in "${ENV_VARS[@]}"; do
    if [ -n "${!var}" ]; then
        if check_chinese_paths "${!var}"; then
            print_error "❌ Environment variable $var contains Chinese characters: ${!var}"
            CHINESE_FOUND=true
        else
            print_success "✅ Environment variable $var is clean: ${!var}"
        fi
    else
        print_status "ℹ️  Environment variable $var is not set"
    fi
done

echo ""

# 3. Check .npmrc file
print_status "3. Checking .npmrc file..."
if [ -f ".npmrc" ]; then
    if grep -qP "[\x{4e00}-\x{9fff}]" .npmrc 2>/dev/null; then
        print_error "❌ .npmrc file contains Chinese characters"
        print_status "Current .npmrc content:"
        cat .npmrc
        CHINESE_FOUND=true
    else
        print_success "✅ .npmrc file is clean"
        print_status "Current .npmrc content:"
        cat .npmrc
    fi
else
    print_warning "⚠️  .npmrc file not found"
fi

echo ""

# 4. Check npm cache directory exists and is accessible
print_status "4. Checking npm cache directory..."
if [ -n "$NPM_CACHE" ] && [ "$NPM_CACHE" != "undefined" ]; then
    if [ -d "$NPM_CACHE" ]; then
        print_success "✅ npm cache directory exists: $NPM_CACHE"
        if [ -w "$NPM_CACHE" ]; then
            print_success "✅ npm cache directory is writable"
        else
            print_error "❌ npm cache directory is not writable: $NPM_CACHE"
            CHINESE_FOUND=true
        fi
    else
        print_warning "⚠️  npm cache directory does not exist: $NPM_CACHE"
        print_status "This is normal if cache hasn't been used yet"
    fi
else
    print_warning "⚠️  npm cache configuration not found"
fi

echo ""

# 5. Check for node_modules and package-lock.json
print_status "5. Checking project dependencies..."
if [ -d "node_modules" ]; then
    print_status "ℹ️  node_modules directory exists (size: $(du -sh node_modules 2>/dev/null | cut -f1))")
else
    print_status "ℹ️  node_modules directory not found (this is expected after cleanup)"
fi

if [ -f "package-lock.json" ]; then
    print_status "ℹ️  package-lock.json exists"
else
    print_status "ℹ️  package-lock.json not found (this is expected after cleanup)"
fi

echo ""

# 6. Test npm commands
print_status "6. Testing npm commands..."
if command_exists npm; then
    print_status "Testing npm config list..."
    if npm config list >/dev/null 2>&1; then
        print_success "✅ npm config commands work correctly"
    else
        print_error "❌ npm config commands failed"
        CHINESE_FOUND=true
    fi
    
    print_status "Testing npm cache location..."
    if npm config get cache >/dev/null 2>&1; then
        print_success "✅ npm cache location accessible"
    else
        print_error "❌ npm cache location not accessible"
        CHINESE_FOUND=true
    fi
else
    print_error "❌ npm command not found"
    CHINESE_FOUND=true
fi

echo ""

# 7. Check for any files with Chinese characters in project
print_status "7. Scanning project files for Chinese characters..."
CHINESE_FILES_FOUND=false

# Check common configuration files
CONFIG_FILES=(".gitignore" ".env" ".env.local" ".env.development" ".env.production")

for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$file" ]; then
        if grep -qP "[\x{4e00}-\x{9fff}]" "$file" 2>/dev/null; then
            print_warning "⚠️  File $file contains Chinese characters"
            CHINESE_FILES_FOUND=true
        fi
    fi
done

# Check for any files with Chinese characters in filenames
if find . -maxdepth 2 -name "*[\u4e00-\u9fff]*" -type f 2>/dev/null | grep -q .; then
    print_warning "⚠️  Found files with Chinese characters in filenames:"
    find . -maxdepth 2 -name "*[\u4e00-\u9fff]*" -type f 2>/dev/null | head -5
    CHINESE_FILES_FOUND=true
fi

if [ "$CHINESE_FILES_FOUND" = false ]; then
    print_success "✅ No Chinese characters found in project files"
fi

echo ""

# 8. Final assessment
print_status "8. Final assessment..."

if [ "$CHINESE_FOUND" = false ] && [ "$CHINESE_FILES_FOUND" = false ]; then
    print_success "🎉 PROJECT IS PATH-CLEAN! 🎉"
    print_success "✅ No Chinese characters found in npm configurations"
    print_success "✅ No Chinese characters found in environment variables"
    print_success "✅ No Chinese characters found in project files"
    print_success "✅ npm cache is properly configured"
    print_success "✅ Project is ready for CI/CD environment"
    
    echo ""
    print_status "Summary:"
    echo "  • npm cache location: $NPM_CACHE"
    echo "  • npm prefix: $NPM_PREFIX"
    echo "  • npm tmp: $NPM_TMP"
    echo "  • Environment variable npm_config_cache: $npm_config_cache"
    echo ""
    print_status "To maintain this clean state:"
    echo "  1. Keep npm_config_cache environment variable set"
    echo "  2. Avoid installing npm packages in directories with Chinese paths"
    echo "  3. Use the cleanup scripts if Chinese paths are detected again"
    echo "  4. Regularly run this verification script"
    
else
    print_error "❌ PROJECT STILL HAS PATH ISSUES"
    print_error "❌ Chinese characters were found in configurations or files"
    print_status "Please run the cleanup scripts to resolve these issues:"
    echo "  • ./scripts/clean-npm-cache.sh (Linux/macOS)"
    echo "  • ./scripts/clean-npm-cache.bat (Windows)"
    echo ""
    print_status "After running cleanup, re-run this verification script"
fi

echo ""
print_status "Verification completed."
