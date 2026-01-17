# npm Audit Fix Guide

## Overview

This guide explains how to properly fix npm vulnerabilities while maintaining dependency stability.

## Step 1: Audit Your Dependencies

```bash
cd frontend
npm audit
```

**Output will show:**

- Number of vulnerabilities by severity (critical, high, moderate, low)
- Affected packages and their versions
- Remediation steps

## Step 2: Automatic Fixes (Safe)

```bash
# Try automatic fixes first (respects package.json version constraints)
npm audit fix
```

**What this does:**

- Updates packages to patched versions within the allowed semver range
- Does NOT update major versions by default
- Safe for most projects

## Step 3: Manual Review for Remaining Vulnerabilities

After `npm audit fix`, check for remaining issues:

```bash
npm audit --json > audit-report.json
cat audit-report.json
```

## Step 4: Handle Problematic Dependencies

If vulnerabilities persist:

### Option A: Check Peer Dependencies First

```bash
# List all peer dependency conflicts
npm ls --all

# Example: If @hookform/resolvers has peer dependency issues:
npm list react
npm list react-hook-form
```

### Option B: Force Fix (Use with Caution)

```bash
# Only if automatic fix didn't work AND you've reviewed the changes
npm audit fix --force
```

⚠️ **Warning:** `--force` may update major versions and break compatibility.

### Option C: Manual Package Update

```bash
# Update specific vulnerable package
npm update <package-name>

# Or specify exact version
npm install <package-name>@<version>
```

## Step 5: Lock File & Verification

```bash
# Commit the lock file
git add package-lock.json
git commit -m "fix: update dependencies to fix npm audit vulnerabilities"

# Verify no new issues
npm audit
```

## Step 6: CI/CD Integration

Add to `.github/workflows/npm-audit.yml`:

```yaml
name: NPM Audit

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 0 * * 0" # Weekly

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "18"
          cache: "npm"

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: Run npm audit
        run: cd frontend && npm audit --audit-level=moderate
        continue-on-error: true

      - name: Create PR for audit fixes
        if: github.event_name == 'schedule'
        uses: actions/github-script@v7
        with:
          script: |
            const { execSync } = require('child_process');

            try {
              execSync('cd frontend && npm audit fix', { stdio: 'inherit' });
              const status = execSync('git status --porcelain').toString();
              
              if (status.trim()) {
                execSync('git config user.name "github-actions"');
                execSync('git config user.email "github-actions@github.com"');
                execSync('git add package*.json');
                execSync('git commit -m "chore: npm audit fix"');
                execSync('git push origin audit-fixes-${new Date().toISOString().split("T")[0]}');
              }
            } catch (error) {
              console.log('No audit fixes needed');
            }
```

## Common Issues & Solutions

### Issue 1: Peer Dependency Conflicts

```bash
# Check what's requested
npm ls <package-name>

# Install compatible version
npm install <package-name>@<compatible-version>
```

### Issue 2: Major Version Breaking Changes

```bash
# Review changelog before updating
npm view <package-name> versions

# Test after update
npm run build
npm run test
```

### Issue 3: Transitive Dependency Issues

```bash
# See the dependency tree
npm ls --all | grep <vulnerable-package>

# May need to update parent package
npm update <parent-package>
```

## Best Practices

✅ **DO:**

- Run `npm audit` in CI/CD pipelines
- Update dependencies regularly (monthly)
- Review changelogs before major updates
- Test thoroughly after updates
- Commit `package-lock.json`

❌ **DON'T:**

- Ignore high/critical vulnerabilities
- Always use `--force` without review
- Update all packages at once without testing
- Commit vulnerable dependencies

## Security Levels

```bash
# Check for high severity only (strict)
npm audit --audit-level=high

# Check for moderate and above
npm audit --audit-level=moderate

# Check everything
npm audit --audit-level=low
```

## Automated Dependency Updates

Consider using Dependabot (GitHub) or Renovate:

1. **GitHub Dependabot** (built-in):
   - Settings → Code security and analysis → Enable Dependabot
   - Auto-creates PRs for dependency updates

2. **Renovate Bot**:
   - Add renovate.json configuration
   - More granular control than Dependabot

## References

- [npm Audit Documentation](https://docs.npmjs.com/cli/v8/commands/npm-audit)
- [Node.js Security Best Practices](https://nodejs.org/en/docs/guides/security/)
- [OWASP Dependency Confusion](https://owasp.org/www-community/attacks/Dependency_Confusion)
