#!/bin/bash
# Frontend Environment Variables Verification Script
# Verifies that all required environment variables are present in GitHub Actions

set -e

echo "🔍 Verifying Frontend Environment Variables..."
echo "=============================================="

# Required environment variables for Next.js frontend
REQUIRED_VARS=(
    "NEXT_PUBLIC_API_URL"
    "NEXT_PUBLIC_APP_ENV"
)

# Optional but recommended variables
OPTIONAL_VARS=(
    "NEXT_PUBLIC_GITHUB_CLIENT_ID"
    "NEXT_PUBLIC_ANALYTICS_ID"
)

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ .env.local file not found!"
    echo "💡 Make sure the CI/CD workflow creates this file with environment variables"
    exit 1
fi

echo "📄 Found .env.local file"

# Check required variables
MISSING_REQUIRED=()
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env.local 2>/dev/null; then
        MISSING_REQUIRED+=("$var")
        echo "❌ Missing required variable: $var"
    else
        value=$(grep "^${var}=" .env.local | cut -d'=' -f2-)
        echo "✅ $var = ${value:0:20}..."  # Show first 20 chars for security
    fi
done

# Check optional variables
MISSING_OPTIONAL=()
for var in "${OPTIONAL_VARS[@]}"; do
    if ! grep -q "^${var}=" .env.local 2>/dev/null; then
        MISSING_OPTIONAL+=("$var")
        echo "⚠️  Missing optional variable: $var"
    else
        value=$(grep "^${var}=" .env.local | cut -d'=' -f2-)
        if [ -z "$value" ] || [ "$value" = "undefined" ] || [ "$value" = "null" ]; then
            echo "⚠️  $var is empty or placeholder"
        else
            echo "✅ $var = ${value:0:20}..."  # Show first 20 chars for security
        fi
    fi
done

echo ""
echo "📊 Verification Summary:"
echo "========================"

if [ ${#MISSING_REQUIRED[@]} -gt 0 ]; then
    echo "❌ FAILED: Missing ${#MISSING_REQUIRED[@]} required variables"
    echo "   Required but missing: ${MISSING_REQUIRED[*]}"
    echo ""
    echo "🔧 Fix Instructions:"
    echo "1. Check your GitHub Actions workflow"
    echo "2. Ensure secrets are properly configured"
    echo "3. Verify the .env.local creation step"
    exit 1
else
    echo "✅ SUCCESS: All required variables present"
fi

if [ ${#MISSING_OPTIONAL[@]} -gt 0 ]; then
    echo "⚠️  WARNING: ${#MISSING_OPTIONAL[@]} optional variables missing"
    echo "   Consider adding: ${MISSING_OPTIONAL[*]}"
else
    echo "✅ All optional variables configured"
fi

echo ""
echo "🔍 Additional Checks:"
echo "===================="

# Check if package.json has test script
if grep -q '"test":' package.json 2>/dev/null; then
    echo "✅ package.json has test script"
else
    echo "❌ package.json missing test script"
fi

# Check if Jest dependencies are installed
if grep -q '"jest":' package.json 2>/dev/null; then
    echo "✅ Jest dependencies found in package.json"
else
    echo "❌ Jest dependencies missing from package.json"
fi

# Check if jest.config.js exists
if [ -f "jest.config.js" ]; then
    echo "✅ jest.config.js found"
else
    echo "❌ jest.config.js missing"
fi

# Check if jest.setup.js exists
if [ -f "jest.setup.js" ]; then
    echo "✅ jest.setup.js found"
else
    echo "❌ jest.setup.js missing"
fi

echo ""
echo "🎯 Next Steps:"
echo "=============="

if [ ${#MISSING_REQUIRED[@]} -eq 0 ]; then
    echo "✅ Ready to run tests: npm test"
    echo "✅ Ready to build: npm run build"
else
    echo "❌ Fix missing variables before running tests"
fi

echo ""
echo "📝 Environment Variables Reference:"
echo "=================================="
echo "NEXT_PUBLIC_API_URL     - Backend API URL (required)"
echo "NEXT_PUBLIC_APP_ENV     - Application environment (required)"
echo "NEXT_PUBLIC_GITHUB_CLIENT_ID - GitHub OAuth (optional)"
echo "NEXT_PUBLIC_ANALYTICS_ID     - Analytics tracking (optional)"

echo ""
echo "🔐 Security Note:"
echo "================="
echo "Never commit .env.local to version control"
echo "Use GitHub Secrets for sensitive values"
echo "Test values should be different from production"
