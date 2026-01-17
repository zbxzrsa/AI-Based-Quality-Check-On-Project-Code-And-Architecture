#!/bin/bash

# Clean NPM Cache and Remove Chinese Path References
# This script ensures your project is "Path-Clean" for CI/CD environments

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

print_status "Starting npm cache cleanup and Chinese path removal..."
print_status "Current working directory: $(pwd)"

# 1. Delete node_modules and package-lock.json
print_status "Step 1: Cleaning project dependencies..."
if [ -d "node_modules" ]; then
    print_status "Removing node_modules..."
    rm -rf node_modules
    print_success "node_modules removed"
else
    print_warning "node_modules directory not found"
fi

if [ -f "package-lock.json" ]; then
    print_status "Removing package-lock.json..."
    rm package-lock.json
    print_success "package-lock.json removed"
else
    print_warning "package-lock.json not found"
fi

# 2. Clean npm cache
print_status "Step 2: Cleaning npm cache..."
if command_exists npm; then
    print_status "Running npm cache clean --force..."
    npm cache clean --force
    print_success "npm cache cleaned"
else
    print_error "npm command not found. Please install Node.js and npm first."
    exit 1
fi

# 3. Check and unset custom npm configurations
print_status "Step 3: Checking npm configurations for Chinese paths..."

# Get current npm configurations
NPM_CACHE=$(get_npm_config cache)
NPM_PREFIX=$(get_npm_config prefix)
NPM_TMP=$(get_npm_config tmp)
NPM_CONFIG_CACHE=$(get_npm_config npm_config_cache)

print_status "Current npm configurations:"
print_status "  cache: $NPM_CACHE"
print_status "  prefix: $NPM_PREFIX"
print_status "  tmp: $NPM_TMP"
print_status "  npm_config_cache: $NPM_CONFIG_CACHE"

# Check for Chinese characters in paths
CHINESE_PATHS_FOUND=false

if check_chinese_paths "$NPM_CACHE"; then
    print_warning "Chinese characters found in npm cache path: $NPM_CACHE"
    CHINESE_PATHS_FOUND=true
fi

if check_chinese_paths "$NPM_PREFIX"; then
    print_warning "Chinese characters found in npm prefix path: $NPM_PREFIX"
    CHINESE_PATHS_FOUND=true
fi

if check_chinese_paths "$NPM_TMP"; then
    print_warning "Chinese characters found in npm tmp path: $NPM_TMP"
    CHINESE_PATHS_FOUND=true
fi

if check_chinese_paths "$NPM_CONFIG_CACHE"; then
    print_warning "Chinese characters found in npm_config_cache path: $NPM_CONFIG_CACHE"
    CHINESE_PATHS_FOUND=true
fi

# 4. Unset problematic configurations
if [ "$CHINESE_PATHS_FOUND" = true ]; then
    print_status "Step 4: Unsetting configurations with Chinese paths..."
    
    # Unset cache configuration
    if check_chinese_paths "$NPM_CACHE"; then
        print_status "Unsetting npm cache configuration..."
        npm config delete cache
        print_success "npm cache configuration unset"
    fi
    
    # Unset prefix configuration
    if check_chinese_paths "$NPM_PREFIX"; then
        print_status "Unsetting npm prefix configuration..."
        npm config delete prefix
        print_success "npm prefix configuration unset"
    fi
    
    # Unset tmp configuration
    if check_chinese_paths "$NPM_TMP"; then
        print_status "Unsetting npm tmp configuration..."
        npm config delete tmp
        print_success "npm tmp configuration unset"
    fi
    
    # Unset npm_config_cache environment variable if it has Chinese paths
    if check_chinese_paths "$NPM_CONFIG_CACHE"; then
        print_status "Unsetting npm_config_cache environment variable..."
        unset npm_config_cache
        print_success "npm_config_cache environment variable unset"
    fi
else
    print_success "No Chinese paths found in npm configurations"
fi

# 5. Configure npm_config_cache for current session
print_status "Step 5: Configuring npm_config_cache for current session..."

# Set npm_config_cache to current directory
CURRENT_DIR=$(pwd)
NEW_CACHE_PATH="$CURRENT_DIR/.npm-cache"

print_status "Setting npm_config_cache to: $NEW_CACHE_PATH"
export npm_config_cache="$NEW_CACHE_PATH"

# Also set it in npm config for this project
npm config set cache "$NEW_CACHE_PATH"

print_success "npm_config_cache configured for current session: $NEW_CACHE_PATH"

# 6. Verify the project is now "Path-Clean"
print_status "Step 6: Verifying project is Path-Clean..."

# Check npm configurations again
print_status "Verifying npm configurations:"
NPM_CACHE_NEW=$(get_npm_config cache)
NPM_PREFIX_NEW=$(get_npm_config prefix)
NPM_TMP_NEW=$(get_npm_config tmp)

print_status "  cache: $NPM_CACHE_NEW"
print_status "  prefix: $NPM_PREFIX_NEW"
print_status "  tmp: $NPM_TMP_NEW"
print_status "  npm_config_cache (env): $npm_config_cache"

# Verify no Chinese characters
VERIFICATION_PASSED=true

if check_chinese_paths "$NPM_CACHE_NEW"; then
    print_error "Chinese characters still found in npm cache path: $NPM_CACHE_NEW"
    VERIFICATION_PASSED=false
fi

if check_chinese_paths "$NPM_PREFIX_NEW"; then
    print_error "Chinese characters still found in npm prefix path: $NPM_PREFIX_NEW"
    VERIFICATION_PASSED=false
fi

if check_chinese_paths "$NPM_TMP_NEW"; then
    print_error "Chinese characters still found in npm tmp path: $NPM_TMP_NEW"
    VERIFICATION_PASSED=false
fi

if check_chinese_paths "$npm_config_cache"; then
    print_error "Chinese characters still found in npm_config_cache: $npm_config_cache"
    VERIFICATION_PASSED=false
fi

# 7. Additional verification steps
print_status "Step 7: Additional verification..."

# Check if .npmrc file exists and contains Chinese characters
if [ -f ".npmrc" ]; then
    if grep -qP "[\x{4e00}-\x{9fff}]" .npmrc 2>/dev/null; then
        print_warning ".npmrc file contains Chinese characters. Consider cleaning it."
        print_status "Current .npmrc content:"
        cat .npmrc
    else
        print_success ".npmrc file is clean"
    fi
else
    print_warning ".npmrc file not found"
fi

# Check environment variables
print_status "Checking environment variables for Chinese paths..."
ENV_VARS=("NPM_CONFIG_CACHE" "NPM_CONFIG_PREFIX" "NPM_CONFIG_TMP" "NPM_CONFIG_REGISTRY")

for var in "${ENV_VARS[@]}"; do
    if [ -n "${!var}" ]; then
        if check_chinese_paths "${!var}"; then
            print_warning "Environment variable $var contains Chinese characters: ${!var}"
            VERIFICATION_PASSED=false
        fi
    fi
done

# 8. Final verification and recommendations
print_status "Step 8: Final verification and recommendations..."

if [ "$VERIFICATION_PASSED" = true ]; then
    print_success "✅ Project is now Path-Clean!"
    print_success "✅ No Chinese characters found in npm configurations"
    print_success "✅ npm_config_cache is properly configured for current session"
    
    echo ""
    print_status "Project is ready for CI/CD environment. Key points:"
    echo "  • npm cache is isolated to: $NEW_CACHE_PATH"
    echo "  • No Chinese paths detected in npm configurations"
    echo "  • Environment variable npm_config_cache is set for current session"
    echo ""
    print_status "To make this permanent for future sessions, add this to your shell profile:"
    echo "  export npm_config_cache=\"$NEW_CACHE_PATH\""
    echo ""
    print_status "To verify in future, run: npm config list | grep -E '(cache|prefix|tmp)'"
    
else
    print_error "❌ Project still contains Chinese paths"
    print_error "❌ Verification failed"
    print_status "Please review the errors above and clean up the problematic configurations"
    exit 1
fi

print_success "npm cache cleanup completed successfully!"
