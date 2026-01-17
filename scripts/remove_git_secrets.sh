#!/bin/bash
# Script to remove secret history from git using git filter-repo
# This removes hardcoded credentials from git history

set -e

echo "⚠️  WARNING: This script will rewrite your git history!"
echo "This is destructive and cannot be easily undone."
echo "Please ensure you have backed up your repository."
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Install git-filter-repo if not present
if ! command -v git-filter-repo &> /dev/null; then
    echo "Installing git-filter-repo..."
    pip install git-filter-repo
fi

# Create a pattern file for secrets to remove
cat > /tmp/secret_patterns.txt << 'EOF'
(?P<secret>TestPassword123!)
(?P<secret>AdminPassword123!)
(?P<secret>ghp_[A-Za-z0-9_]{36,255})
(?P<secret>sk_[A-Za-z0-9_]{20,})
(?P<secret>postgresql://.*@.*:.*/.*)
(?P<secret>redis://.*:.*@.*:.*/.*)
EOF

echo "🔍 Scanning for secrets in git history..."

# Use git filter-repo to remove secrets
git filter-repo --replace-text=/tmp/secret_patterns.txt --force

echo "✅ Git history cleaned!"
echo "⚠️  You must force-push to your repository:"
echo "   git push --force-with-lease"

rm /tmp/secret_patterns.txt
