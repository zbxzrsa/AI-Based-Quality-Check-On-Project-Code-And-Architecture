# 🔒 Security & Automation Scripts

This directory contains automated security tools and AI-powered automation for your AI-Based Quality Check project.

## 📊 Security Compliance Report Generator

**File:** `security_compliance_report.py`

### Purpose
Transforms Bandit SAST JSON output into comprehensive security compliance reports aligned with ISO/IEC 25010 quality standards.

### Usage

#### Generate Markdown Report
```bash
python scripts/security_compliance_report.py backend/bandit-results.json --output security-report.md
```

#### Generate JSON Report
```bash
python scripts/security_compliance_report.py backend/bandit-results.json --format json --output security-report.json
```

### Features

- **ISO/IEC 25010 Compliance Analysis**: Categorizes vulnerabilities by security characteristics
- **Risk Scoring**: Calculates compliance scores (0-100) with severity ratings
- **Executive Summaries**: Business-focused risk assessments
- **Remediation Guidance**: Prioritized action items
- **Multiple Output Formats**: Markdown and JSON support

### Sample Output

#### Compliance Score
```
Security Compliance Score: 78/100 (Fair)
Critical Vulnerabilities: 2
High Severity Issues: 5
ISO/IEC 25010 Analysis:
- Confidentiality: Poor (3 issues)
- Integrity: Good (1 issue)
- Availability: Excellent (0 issues)
```

#### Vulnerability Categories
- **Confidentiality**: Hardcoded credentials, insecure deserialization
- **Integrity**: SQL injection, command injection, input validation
- **Availability**: Resource exhaustion, DoS vulnerabilities
- **Authenticity**: Authentication bypass, session management

### Integration with CI/CD

Add to your GitHub Actions workflow:

```yaml
- name: Generate Security Report
  run: |
    python scripts/security_compliance_report.py bandit-results.json --output security-report.md

- name: Upload Security Report
  uses: actions/upload-artifact@v4
  with:
    name: security-compliance-report
    path: security-report.md

- name: Comment Report on PR
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const report = fs.readFileSync('security-report.md', 'utf8');
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: report
      });
```

### Automated Report Generation

The security scanning workflow automatically generates reports:

```yaml
# In .github/workflows/security-scanning.yml
- name: Generate Compliance Report
  run: |
    python scripts/security_compliance_report.py bandit-results.sarif --output compliance-report.md
  continue-on-error: true
```

## 🚨 Critical Vulnerability Assessment

**File:** `docs/CRITICAL_VULNERABILITY_CATEGORIZATION.md`

### When to Use
- TruffleHog detects exposed secrets
- Bandit finds critical security issues
- ESLint security plugin flags problems
- Any security scan fails with critical findings

### Assessment Framework

1. **Categorize by ISO/IEC 25010**:
   - Confidentiality (data protection)
   - Integrity (modification prevention)
   - Availability (system reliability)
   - Authenticity (identity verification)

2. **Calculate Risk Score**:
   ```
   Risk Score = (Impact × Likelihood) ÷ Controls
   ```

3. **Determine Remediation Priority**:
   - **Critical**: Fix within 24 hours
   - **High**: Fix within 1 week
   - **Medium**: Fix within 1 month

### Quick Assessment Checklist

For each critical vulnerability:
- [ ] ISO characteristic affected?
- [ ] Business impact assessment?
- [ ] Exploitability rating?
- [ ] Remediation timeline?
- [ ] Communication requirements?

## 🧹 Git Secrets Cleanup

**File:** `docs/SECRETS_CLEANUP_GUIDE.md`

### Emergency Response Guide

When TruffleHog fails due to exposed credentials:

1. **Immediate Actions**:
   - Stop all CI/CD pipelines
   - Rotate affected credentials
   - Assess exposure scope

2. **Repository Cleanup**:
   ```bash
   # Install git-filter-repo
   pip install git-filter-repo

   # Remove secrets from history
   git filter-repo --replace-text <(echo "your_secret==>REDACTED") --force

   # Force push (CAUTION: Rewrites history)
   git push origin --force --all
   ```

3. **Team Coordination**:
   - Notify all developers
   - Provide re-cloning instructions
   - Update CI/CD configurations

4. **Prevention Measures**:
   - Install pre-commit hooks
   - Update .gitignore
   - Set up ongoing monitoring

## 🔧 Development Setup

### Prerequisites
```bash
# Install Python dependencies
pip install -r backend/requirements.txt
pip install -r backend/requirements-test.txt

# Install Node.js security tools
cd frontend && npm install --save-dev eslint-plugin-security
```

### Testing the Tools
```bash
# Test Bandit report generation
bandit -r backend/app -f json -o test-bandit.json
python scripts/security_compliance_report.py test-bandit.json --output test-report.md

# Test TruffleHog integration
trufflehog git --repo-path . --json > test-secrets.json
```

## 📈 Monitoring and Alerts

### Automated Security Monitoring
```bash
# Daily secret scanning
0 2 * * * /path/to/repo/scripts/monitor_secrets.sh

# Weekly vulnerability assessment
0 3 * * 1 python scripts/security_compliance_report.py bandit-results.json --output weekly-report.md
```

### Alert Thresholds
- **Critical Issues**: 0 (Zero tolerance)
- **High Severity**: < 5 per 1000 lines of code
- **Compliance Score**: > 85/100
- **Response Time**: < 24 hours for critical findings

## 🔗 Integration Points

### CI/CD Integration
- **GitHub Actions**: Automatic report generation and PR comments
- **Security Gates**: Block deployments on critical findings
- **Artifact Storage**: Preserve reports for compliance audits

### AI Reviewer Integration
- **JSON Output**: Structured data for AI analysis
- **Historical Tracking**: Trend analysis across releases
- **Risk Scoring**: Automated priority assignment

### Compliance Reporting
- **ISO/IEC 25010**: Quality standard alignment
- **Audit Trails**: Complete vulnerability lifecycle
- **Executive Summaries**: Business-focused reporting

## 🆘 Troubleshooting

### Common Issues

**Script won't run:**
```bash
# Check Python path
which python
python --version

# Install missing dependencies
pip install json argparse pathlib
```

**Bandit report empty:**
```bash
# Verify Bandit installation
bandit --version

# Check file permissions
ls -la bandit-results.json

# Run Bandit manually
bandit -r backend/app -f json -o bandit-results.json
```

**Permission errors:**
```bash
# Make script executable
chmod +x scripts/security_compliance_report.py

# Run with Python explicitly
python3 scripts/security_compliance_report.py ...
```

## 📚 Additional Resources

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [TruffleHog Documentation](https://github.com/trufflesecurity/trufflehog)
- [ISO/IEC 25010 Standard](https://iso.org/standard/35733.html)
- [OWASP Security Testing Guide](https://owasp.org/www-project-testing/)

---

## 🤖 AI Self-Healing CI/CD

**File:** `ai_self_healing.py`

### Purpose
Automatically analyzes CI/CD pipeline failures and provides AI-powered fixes through GitHub PR comments, completing the automation of your Pull Request review process.

### How It Works

```
CI/CD Failure → GitHub API → Log Extraction → Ollama AI → PR Comment
     ↓              ↓            ↓              ↓            ↓
  Pipeline Fails → Fetch Logs → Parse Errors → Generate Fix → Post Solution
```

### Features

- **Intelligent Failure Analysis**: Parses Python exceptions, test failures, and security issues
- **Ollama Integration**: Uses qwen2.5-coder for contextual code analysis
- **GitHub PR Comments**: Posts formatted analysis with code fixes
- **Multi-Failure Support**: Handles Backend Tests, Security Scans, and more
- **Automated Triggering**: Integrates with CI/CD workflows

### Usage

#### Analyze Latest Failure
```bash
python scripts/ai_self_healing.py --analyze-failure --pr-number 123
```

#### Manual Analysis
```bash
# Analyze specific workflow run
python scripts/ai_self_healing.py --workflow-run-id 456789012

# Target specific jobs
python scripts/ai_self_healing.py --analyze-failure --job-names "Backend Tests" "Security Scan"
```

### GitHub Actions Integration

Automatically triggers on CI/CD failures:

```yaml
- name: AI Self-Healing Analysis
  if: failure() && github.event_name == 'pull_request'
  run: |
      echo "🤖 Running AI Self-Healing Analysis..."
      cd backend
      python ../scripts/ai_self_healing.py --analyze-failure --pr-number ${{ github.event.number }}
  env:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      OLLAMA_URL: ${{ secrets.OLLAMA_URL }}
      OLLAMA_MODEL: ${{ secrets.OLLAMA_MODEL }}
  continue-on-error: true
```

### Prerequisites

1. **Ollama Setup**:
   ```bash
   ollama pull qwen2.5-coder
   ollama serve
   ```

2. **GitHub Secrets**:
   - `GITHUB_TOKEN`: Personal access token with repo permissions
   - `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
   - `OLLAMA_MODEL`: AI model to use (default: qwen2.5-coder)

3. **Python Dependencies**:
   ```txt
   requests>=2.28.0
   ```

### Supported Failure Types

- **Python Exceptions**: Traceback parsing and root cause analysis
- **Test Failures**: Pytest failure extraction and fixes
- **Security Issues**: Bandit and TruffleHog vulnerability analysis
- **Database Errors**: PostgreSQL, Neo4j, Redis connection issues
- **Async Problems**: Event loop and coroutine failures

### Example AI Analysis Output

**Original Error:**
```
neo4j.exceptions.ServiceUnavailable: Connection refused
```

**AI-Generated PR Comment:**
```markdown
## 🤖 AI Self-Healing Analysis

**Generated:** 2024-01-17T11:06:04
**Job:** Backend Tests
**Status:** 🔴 Failed - AI Analysis Complete

### 🚨 Failure Summary
❌ **1 test(s) failed**
💥 **1 error(s) detected**

### 🔍 AI Analysis & Fix

## 🔍 Root Cause Analysis
The Neo4j connection is failing due to incorrect URI configuration in test environment.

## 🛠️ Fix
Update the test configuration to use the correct Neo4j URI:

```python
# In conftest.py or test setup
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "testpassword"
```

## 🛡️ Prevention
- Ensure Neo4j service is running in CI/CD
- Use environment-specific configuration
- Add connection health checks

### 📋 Next Steps

1. **Review the suggested fix above**
2. **Apply the code changes to your branch**
3. **Run tests locally** before pushing
4. **Request re-review** after implementing fixes
```

## ⚡ Quick Commands

```bash
# Generate security report
python scripts/security_compliance_report.py bandit-results.json -o report.md

# AI self-healing analysis
python scripts/ai_self_healing.py --analyze-failure --pr-number 123

# Emergency secret cleanup
git filter-repo --replace-text <(echo "secret==>REDACTED") --force

# Verify cleanup
trufflehog git --repo-path . --json | jq '.[] | select(.Verified == true)'
```

**Remember:** Security and automation are continuous processes. Run these tools regularly and address findings promptly.
