# 🔐 Git History Secrets Cleanup Guide

## 🚨 CRITICAL SECURITY PROCEDURE

This guide provides a **step-by-step process** to safely remove Neo4j credentials and other secrets from your Git repository history using `git-filter-repo`. This is required when TruffleHog detects exposed credentials in your repository.

## ⚠️ IMPORTANT WARNINGS

- **This operation is IRREVERSIBLE** - it rewrites Git history
- **Backup your repository** before proceeding
- **Inform all team members** - they will need to re-clone
- **Update all CI/CD pipelines** with new repository URLs
- **Test thoroughly** after cleanup

## 📋 Prerequisites

1. **Install git-filter-repo** (recommended over git-filter-branch):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install git-filter-repo

   # macOS with Homebrew
   brew install git-filter-repo

   # Or install via pip
   pip install git-filter-repo
   ```

2. **Create a backup** of your repository:
   ```bash
   # Option 1: Clone to backup location
   git clone --mirror /path/to/your/repo /path/to/backup/repo.git

   # Option 2: Create compressed archive
   git bundle create /path/to/backup/repo.bundle --all
   ```

3. **Identify all secrets** that need to be removed:
   - Neo4j credentials (username/password/URI)
   - API keys and tokens
   - Database connection strings
   - Private keys and certificates

## 🔍 Step 1: Analyze Current Exposure

### 1.1 Run TruffleHog to identify exposed secrets:
```bash
# Scan entire repository history
trufflehog git --repo-path . --json > secrets_audit.json

# Or scan specific branch
trufflehog git --repo-path . --branch main --json > secrets_audit.json
```

### 1.2 Review findings:
```bash
# Count secrets by type
jq '. | group_by(.DetectorName) | map({detector: .[0].DetectorName, count: length})' secrets_audit.json

# Extract Neo4j-specific findings
jq '.[] | select(.DetectorName == "Neo4j" or (.Raw? | contains("neo4j"))) | {file: .SourceMetadata.Data.Git.File, line: .SourceMetadata.Data.Git.Line, secret: .Raw}' secrets_audit.json
```

### 1.3 Document all secrets to remove:
```bash
# Create secrets removal list
cat > secrets_to_remove.txt << 'EOF'
neo4j
NEO4J_PASSWORD
NEO4J_USER
NEO4J_URI
your_neo4j_password_here
your_neo4j_username_here
bolt://localhost:7687
EOF
```

## 🧹 Step 2: Clean Repository History

### 2.1 Create a fresh clone for cleaning:
```bash
# Create a new directory for the cleaned repository
mkdir ../clean-repo
cd ../clean-repo
git clone ../original-repo .
```

### 2.2 Remove secrets from all branches and tags:
```bash
# Remove specific passwords/secrets (replace with your actual values)
git filter-repo --replace-text <(echo "your_neo4j_password_here==>REDACTED_PASSWORD") --force
git filter-repo --replace-text <(echo "your_neo4j_username_here==>REDACTED_USERNAME") --force
git filter-repo --replace-text <(echo "bolt://localhost:7687==>REDACTED_URI") --force

# Remove entire files containing secrets (if any)
git filter-repo --path secrets.env --invert-paths
git filter-repo --path .env.local --invert-paths

# Remove specific file patterns
git filter-repo --path-glob "*.key" --invert-paths
git filter-repo --path-glob "*secret*" --invert-paths
```

### 2.3 Alternative: Use sed for complex patterns:
```bash
# For more complex patterns, create a sed script
cat > cleanup_secrets.sed << 'EOF'
# Remove Neo4j passwords (various formats)
/password.*=.*["']([^"']*)["']/s//password="REDACTED"/g
/user.*=.*["']([^"']*)["']/s//user="REDACTED"/g
/uri.*=.*["']bolt:\/\/([^"']*)["']/s//uri="REDACTED_URI"/g

# Remove hardcoded credentials in code
s/neo4j:.*@/neo4j:REDACTED@/g
s/testpassword/REDACTED_PASSWORD/g
EOF

git filter-repo --replace-text cleanup_secrets.sed --force
```

### 2.4 Verify cleanup:
```bash
# Check that secrets are gone
git log --all --grep="password\|secret\|neo4j" --oneline
git log --all --full-history -- your_secret_file

# Verify with TruffleHog
trufflehog git --repo-path . --json | jq '.[] | select(.DetectorName != "Base64") | .DetectorName' | sort | uniq -c
```

## 🔄 Step 3: Update and Push Changes

### 3.1 Force push the cleaned history:
```bash
# WARNING: This will overwrite remote history
git push origin --force --all
git push origin --force --tags
```

### 3.2 Update default branch protection rules:
```bash
# Ensure the cleaned main/master branch is protected
# Add branch protection rules in GitHub/GitLab settings
```

### 3.3 Update all CI/CD pipelines:
```bash
# Update GitHub Actions to use new repository state
# Update any webhooks or integrations
# Update documentation references
```

## 👥 Step 4: Team Coordination

### 4.1 Notify all team members:
```bash
# Send notification about repository history rewrite
cat > team_notification.md << 'EOF'
# 🚨 URGENT: Repository History Rewrite

## What Happened
We discovered exposed credentials in our Git repository history. To maintain security, we've rewritten the repository history to remove these secrets.

## What You Need to Do

### IMMEDIATE ACTION REQUIRED:
1. **Backup any uncommitted work** (stash or commit locally)
2. **Delete your current clone** of the repository
3. **Re-clone from the updated repository**

### Commands to run:
```bash
# Backup current work
git stash push -m "backup before repo rewrite"

# Remove old clone (after backing up important branches)
cd ..
rm -rf original-repo-name

# Clone fresh repository
git clone https://github.com/your-org/your-repo.git
cd your-repo

# Restore your work
git stash pop
```

## Why This Was Necessary
- Exposed Neo4j credentials were found in commit history
- This could compromise database security
- Industry best practice requires immediate cleanup

## Prevention Measures
- Never commit secrets to version control
- Use `.gitignore` for sensitive files
- Use environment variables for configuration
- Regular secret scanning with TruffleHog

Contact @security-team if you have questions.
EOF
```

### 4.2 Update remote references:
```bash
# For each team member, help them update their remotes
git remote set-url origin https://github.com/your-org/your-repo.git
git fetch origin
git reset --hard origin/main
```

## 🔐 Step 5: Implement Prevention Measures

### 5.1 Update .gitignore:
```bash
cat >> .gitignore << 'EOF'
# Secrets and credentials
.env
.env.local
.env.*.local
secrets.json
*.key
*.pem
config/secrets.py

# Database credentials
neo4j_credentials.txt
db_config.json

# API keys and tokens
api_keys.json
tokens.txt
EOF
```

### 5.2 Create pre-commit hooks:
```bash
# Install pre-commit framework
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/trufflesecurity/trufflehog
    rev: main
    hooks:
      - id: trufflehog
        name: TruffleHog
        description: Detect secrets in code
        entry: trufflehog
        args: [--no-verification, --git]
        stages: [commit]

  - repo: local
    hooks:
      - id: bandit
        name: Bandit Security Scan
        entry: bandit
        language: system
        files: \.py$
        args: [-r, backend/app, --silent, --exit-zero]
EOF

# Install the hooks
pre-commit install
```

### 5.3 Set up repository secret scanning:
```yaml
# Add to .github/workflows/security-scanning.yml
- name: Repository Secret Scan
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: main
    head: HEAD
    extra_args: --only-verified --fail
```

## 🔍 Step 6: Verification and Monitoring

### 6.1 Verify cleanup was successful:
```bash
# Run comprehensive checks
echo "=== Running post-cleanup verification ==="

# 1. Check for remaining secrets
echo "1. Scanning for remaining secrets..."
trufflehog git --repo-path . --json | jq '.[] | select(.Verified == true) | {detector: .DetectorName, file: .SourceMetadata.Data.Git.File}' || echo "✅ No verified secrets found"

# 2. Verify repository integrity
echo "2. Checking repository integrity..."
git fsck --full

# 3. Check file sizes (large files may indicate issues)
echo "3. Checking for large files..."
find . -type f -size +50M -exec ls -lh {} \; || echo "✅ No large files found"

# 4. Verify all branches are clean
echo "4. Checking all branches..."
for branch in $(git branch -r | grep -v HEAD); do
  echo "Checking $branch..."
  git log --oneline $branch | head -5
done
```

### 6.2 Set up ongoing monitoring:
```bash
# Create monitoring script
cat > scripts/monitor_secrets.sh << 'EOF'
#!/bin/bash
# Daily secret monitoring script

REPO_PATH="."
OUTPUT_FILE="secret_scan_$(date +%Y%m%d).json"

echo "🔍 Running daily secret scan..."

# Run TruffleHog scan
trufflehog git --repo-path "$REPO_PATH" --json > "$OUTPUT_FILE"

# Count findings
verified_secrets=$(jq '.[] | select(.Verified == true) | .DetectorName' "$OUTPUT_FILE" | wc -l)
unverified_secrets=$(jq '.[] | select(.Verified == false) | .DetectorName' "$OUTPUT_FILE" | wc -l)

echo "📊 Scan Results:"
echo "  Verified secrets: $verified_secrets"
echo "  Unverified secrets: $unverified_secrets"
echo "  Report saved to: $OUTPUT_FILE"

# Alert if verified secrets found
if [ "$verified_secrets" -gt 0 ]; then
  echo "🚨 ALERT: Verified secrets found! Check $OUTPUT_FILE"
  # Send notification (integrate with your alerting system)
  exit 1
else
  echo "✅ No verified secrets detected"
fi
EOF

chmod +x scripts/monitor_secrets.sh
```

### 6.3 Schedule regular monitoring:
```bash
# Add to crontab for daily monitoring
echo "0 2 * * * /path/to/your/repo/scripts/monitor_secrets.sh" | crontab -
```

## 🚨 Emergency Response Plan

If secrets are exposed again in the future:

1. **IMMEDIATE ACTIONS:**
   - Rotate ALL affected credentials
   - Notify security team
   - Assess impact scope

2. **CONTAINMENT:**
   - Temporarily disable affected systems
   - Implement emergency access controls

3. **RECOVERY:**
   - Follow this cleanup guide again
   - Implement additional prevention measures
   - Conduct security review

## 📞 Support and Resources

- **Security Team:** Contact for assistance with credential rotation
- **Git Documentation:** https://git-scm.com/docs/git-filter-repo
- **TruffleHog:** https://github.com/trufflesecurity/trufflehog
- **OWASP Secrets Management:** https://owasp.org/www-project-secrets-management/

---

## ⚡ Quick Reference Commands

```bash
# Emergency cleanup (use with extreme caution)
git filter-repo --replace-text <(echo "your_secret==>REDACTED") --force
git push origin --force --all

# Verification
trufflehog git --repo-path . --json | jq '.[] | select(.Verified == true)'

# Prevention
pre-commit install
echo ".env" >> .gitignore
```

**Remember: Repository history rewrites affect the entire team. Communicate clearly and test thoroughly before pushing changes.**
