# 🤖 AI Self-Healing CI/CD Guide

## Overview

The AI Self-Healing system automatically analyzes CI/CD pipeline failures and provides intelligent fixes through GitHub PR comments. This system integrates with your **AI-Based Quality Check** project to automate the Pull Request review process.

## 🚀 How It Works

```
CI/CD Failure → Log Analysis → Ollama AI → GitHub PR Comment
     ↓              ↓            ↓              ↓
  Pipeline Fails → Extract Errors → Generate Fix → Post Solution
```

### 1. Failure Detection
- Monitors "Backend Tests" and "Critical Security Checks" jobs
- Automatically triggers on pipeline failures
- Extracts logs using GitHub API

### 2. Intelligent Analysis
- Parses Python test failures, exceptions, and security issues
- Sends structured data to Ollama (qwen2.5-coder)
- AI analyzes root causes and generates fixes

### 3. Automated Fixes
- Provides specific code changes
- Includes corrected code blocks
- Suggests prevention measures

## 📋 Prerequisites

### Required Secrets (GitHub Repository Settings)

Add these to your GitHub repository secrets:

```bash
# Required for GitHub API access
GITHUB_TOKEN=your_github_personal_access_token

# Ollama configuration (optional, defaults provided)
OLLAMA_URL=http://your-ollama-server:11434
OLLAMA_MODEL=qwen2.5-coder
```

### Ollama Setup

1. **Install Ollama** locally or on a server:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Pull the qwen2.5-coder model**:
   ```bash
   ollama pull qwen2.5-coder
   ```

3. **Start Ollama service**:
   ```bash
   ollama serve
   ```

4. **Verify installation**:
   ```bash
   curl http://localhost:11434/api/tags
   ```

### Python Dependencies

Add to your `backend/requirements.txt`:

```txt
requests>=2.28.0
```

## 🔧 Installation & Setup

### 1. Clone the Script

The AI self-healing script is located at `scripts/ai_self_healing.py`.

### 2. Configure GitHub Actions

The system is pre-integrated into your CI/CD workflow (`.github/workflows/ci-cd.yml`):

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

## 🎯 Usage Examples

### Manual Analysis

Analyze a specific PR's latest failure:

```bash
cd backend
python ../scripts/ai_self_healing.py --analyze-failure --pr-number 123
```

### Analyze Specific Jobs

Target specific job names:

```bash
python scripts/ai_self_healing.py --analyze-failure --job-names "Backend Tests" "Critical Security Checks"
```

### Debug Mode

Analyze a specific workflow run without posting:

```bash
python scripts/ai_self_healing.py --workflow-run-id 456789012
```

## 📊 Supported Failure Types

### Backend Test Failures
- **Python Exceptions**: Traceback parsing and analysis
- **Test Failures**: Pytest failure extraction
- **Async Issues**: Event loop and coroutine problems
- **Database Errors**: PostgreSQL, Neo4j, Redis connection issues

### Security Scan Failures
- **Bandit Issues**: SAST vulnerability analysis
- **TruffleHog Secrets**: Exposed credential detection
- **Critical Vulnerabilities**: High-severity security issues

## 💡 AI Analysis Examples

### Example 1: Database Connection Failure

**Original Error:**
```
neo4j.exceptions.ServiceUnavailable: Connection refused
```

**AI Analysis:**
```
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
```

### Example 2: Pydantic Validation Error

**Original Error:**
```
ValidationError: 1 validation error for UserModel
email
  value is not a valid email address (type=value_error.const; given=invalid-email)
```

**AI Analysis:**
```
## 🔍 Root Cause Analysis
Pydantic validation is failing due to invalid email format in test data.

## 🛠️ Fix
Update test data to use valid email format:

```python
# Fix the test data
user_data = {
    "email": "test@example.com",  # Was: "invalid-email"
    "name": "Test User"
}
```

## 🛡️ Prevention
- Use proper test data factories
- Validate test inputs before API calls
- Add data validation helpers
```

## 🔧 Advanced Configuration

### Custom Ollama Models

Use different AI models for specialized analysis:

```bash
export OLLAMA_MODEL=codellama:13b  # Alternative model
export OLLAMA_MODEL=deepseek-coder # Another option
```

### Custom Analysis Prompts

Modify the system prompt in the script for domain-specific analysis:

```python
system_prompt = """You are an expert in FastAPI, Neo4j, and Next.js development.
Focus on database integration, async patterns, and security best practices."""
```

### Log Filtering

Customize which logs are sent to AI analysis:

```python
# In parse_failure_logs method
if 'DEBUG' in line:
    continue  # Skip debug logs
if len(logs) > 10000:
    logs = logs[-5000:]  # Limit log size
```

## 📈 Monitoring & Metrics

### Success Metrics

Track these KPIs for your AI self-healing system:

- **Response Time**: Time from failure to PR comment
- **Accuracy Rate**: Percentage of AI suggestions that fix the issue
- **Coverage**: Types of failures successfully analyzed
- **User Adoption**: Developer usage of AI suggestions

### Logging

The script provides detailed logging:

```bash
# Enable debug logging
export PYTHONPATH=scripts
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from ai_self_healing import AISelfHealing
# Your analysis code
"
```

## 🚨 Troubleshooting

### Common Issues

#### Ollama Connection Failed
```
Error communicating with Ollama: Connection refused
```

**Solutions:**
- Verify Ollama is running: `ollama serve`
- Check URL: `curl http://localhost:11434/api/tags`
- Update `OLLAMA_URL` secret if using remote server

#### GitHub API Rate Limiting
```
403 Client Error: rate limit exceeded
```

**Solutions:**
- Use GitHub App instead of Personal Access Token
- Implement retry logic with exponential backoff
- Cache workflow run data

#### Large Log Files
```
MemoryError: Log parsing failed
```

**Solutions:**
- Logs are automatically truncated to 5000 characters
- Increase limit in `parse_failure_logs` if needed
- Filter out verbose logs before analysis

### Testing the System

#### Local Testing
```bash
# Test Ollama connection
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5-coder", "prompt": "Hello", "stream": false}'

# Test GitHub API access
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/user
```

#### Integration Testing
```bash
# Test full pipeline locally
export GITHUB_TOKEN=test_token
export DRY_RUN=true
python scripts/ai_self_healing.py --analyze-failure --pr-number 1
```

## 🔒 Security Considerations

### API Token Security
- Store `GITHUB_TOKEN` as GitHub secret
- Use fine-grained Personal Access Tokens
- Rotate tokens regularly

### Ollama Security
- Run Ollama on secure internal network
- Use authentication if exposed externally
- Monitor API usage and costs

### Data Privacy
- CI/CD logs may contain sensitive information
- Filter logs before sending to AI analysis
- Implement log retention policies

## 📚 API Reference

### AISelfHealing Class

```python
class AISelfHealing:
    def __init__(self):
        # Initialize with environment variables

    def run_self_healing(self, pr_number=None, job_names=None):
        # Main entry point for self-healing analysis

    def analyze_latest_failure(self, job_names, pr_number=None):
        # Find and analyze the most recent failure

    def send_to_ollama(self, prompt, context):
        # Send analysis request to Ollama AI

    def post_github_comment(self, pr_number, comment):
        # Post formatted comment to GitHub PR
```

### Command Line Options

```bash
usage: ai_self_healing.py [-h] [--pr-number PR_NUMBER]
                         [--workflow-run-id WORKFLOW_RUN_ID]
                         [--job-names JOB_NAMES [JOB_NAMES ...]]
                         [--analyze-failure] [--dry-run]

AI Self-Healing CI/CD Analysis Tool

optional arguments:
  --pr-number PR_NUMBER      GitHub PR number to comment on
  --workflow-run-id WORKFLOW_RUN_ID
                             Specific workflow run ID to analyze
  --job-names JOB_NAMES [JOB_NAMES ...]
                             Job names to analyze (default: Backend Tests, Critical Security Checks)
  --analyze-failure          Analyze the latest failure and post fix
  --dry-run                  Show what would be done without posting
```

## 🎯 Future Enhancements

### Planned Features
- **Multi-model Support**: Use different AI models for different failure types
- **Historical Learning**: Learn from past fixes to improve suggestions
- **Automated Fixes**: Directly apply fixes (with approval)
- **Slack Integration**: Notify teams of critical failures
- **Metrics Dashboard**: Track system performance

### Integration Ideas
- **Jira Integration**: Create tickets for complex fixes
- **PagerDuty**: Alert on-call engineers for critical failures
- **Code Review**: Suggest code review improvements
- **Documentation**: Auto-update troubleshooting guides

## 📞 Support

For issues with the AI Self-Healing system:

1. **Check the logs** in GitHub Actions
2. **Verify Ollama connectivity**
3. **Review GitHub API permissions**
4. **Check script error handling**

### Debugging Commands

```bash
# Test Ollama directly
echo '{"model": "qwen2.5-coder", "prompt": "Say hello", "stream": false}' | \
  curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d @-

# Test GitHub API
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$GITHUB_REPOSITORY/actions/runs
```

---

## ⚡ Quick Start Summary

1. **Set up Ollama**: `ollama pull qwen2.5-coder && ollama serve`
2. **Configure secrets**: Add `GITHUB_TOKEN`, `OLLAMA_URL`, `OLLAMA_MODEL`
3. **Test locally**: `python scripts/ai_self_healing.py --dry-run --analyze-failure`
4. **Deploy**: Push to trigger CI/CD integration
5. **Monitor**: Check PR comments on failures

The AI Self-Healing system transforms your CI/CD failures from blocking issues into **learning opportunities** that improve your codebase and development practices.
