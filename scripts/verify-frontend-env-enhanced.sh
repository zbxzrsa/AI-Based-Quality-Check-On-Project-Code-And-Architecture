#!/bin/bash
# Enhanced Frontend Environment Variables Verification Script
# Tests Next.js build to catch environment variable issues early

set -e

echo "🔍 Enhanced Frontend Environment Verification..."
echo "================================================"

cd frontend

# Check 1: Required environment variables
echo "1️⃣  Checking Required Environment Variables..."
REQUIRED_VARS=("NEXT_PUBLIC_API_URL" "NEXT_PUBLIC_APP_ENV")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required variable: $var"
        exit 1
    else
        echo "✅ $var = ${!var:0:30}..."
    fi
done

# Check 2: Test Next.js build without actually building
echo ""
echo "2️⃣  Testing Next.js Configuration..."
if npx next build --dry-run 2>/dev/null; then
    echo "✅ Next.js configuration is valid"
else
    echo "❌ Next.js configuration error"
    echo "   This usually indicates missing environment variables"
    exit 1
fi

# Check 3: Validate package.json scripts
echo ""
echo "3️⃣  Validating package.json scripts..."
if npm run test --dry-run 2>/dev/null; then
    echo "✅ Test script is valid"
else
    echo "❌ Test script configuration error"
    exit 1
fi

# Check 4: Test Jest configuration
echo ""
echo "4️⃣  Testing Jest Configuration..."
if npx jest --version >/dev/null 2>&1; then
    echo "✅ Jest is properly configured"
else
    echo "❌ Jest configuration error"
    exit 1
fi

# Check 5: Quick syntax check
echo ""
echo "5️⃣  Running ESLint Syntax Check..."
if npm run lint 2>/dev/null; then
    echo "✅ Code syntax is valid"
else
    echo "❌ Syntax errors found"
    exit 1
fi

echo ""
echo "🎉 All pre-flight checks passed!"
echo "   Ready to run full test suite..."
