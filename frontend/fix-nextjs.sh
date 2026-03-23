#!/bin/bash
# Fix Next.js development server issues

echo "🔧 Fixing Next.js development server..."

# Step 1: Stop any running Next.js processes
echo ""
echo "📌 Step 1: Stopping any running Next.js processes..."
pkill -f "next dev" 2>/dev/null && echo "✅ Stopped running Next.js processes" || echo "ℹ️  No running Next.js processes found"

# Step 2: Clean build artifacts and cache
echo ""
echo "📌 Step 2: Cleaning build artifacts and cache..."
for dir in .next .swc node_modules/.cache; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"
        echo "✅ Removed $dir"
    else
        echo "ℹ️  $dir not found (already clean)"
    fi
done

# Step 3: Reinstall dependencies
echo ""
echo "📌 Step 3: Reinstalling dependencies..."
echo "This may take a few minutes..."
npm install
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Step 4: Verify Next.js installation
echo ""
echo "📌 Step 4: Verifying Next.js installation..."
NEXT_VERSION=$(npm list next --depth=0 2>/dev/null | grep "next@")
if [ -n "$NEXT_VERSION" ]; then
    echo "✅ $NEXT_VERSION"
else
    echo "⚠️  Could not verify Next.js version"
fi

echo ""
echo "✨ Fix complete! You can now run:"
echo "   npm run dev"
echo ""
echo "The development server should start at http://localhost:3000"
