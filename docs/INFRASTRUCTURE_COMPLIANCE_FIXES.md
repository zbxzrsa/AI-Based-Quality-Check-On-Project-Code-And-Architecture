# Infrastructure & Compliance Fixes

This document outlines the fixes implemented to resolve infrastructure and compliance issues in the AI Code Review Platform.

## Issues Fixed

### 1. Path Compliance Check Failures
**Problem**: GitHub Action 'Path Compliance Check' was failing due to non-ASCII characters (like Chinese characters) or spaces in file paths.

**Solution**: 
- Created a comprehensive Python script (`scripts/scan_file_paths.py`) that recursively scans the project directory
- Updated the compliance workflow to use both Python and JavaScript path checking
- Added cross-platform support (Ubuntu, Windows)

**Usage**:
```bash
# Scan current directory
python scripts/scan_file_paths.py

# Scan specific directory with JSON output
python scripts/scan_file_paths.py /path/to/project --output-format json
```

**Git Commands for Fixing Issues**:
The script automatically generates `git mv` commands to rename files while preserving history:
```bash
git mv "old-name-with-spaces.txt" "old-name-with-spaces.txt"
git mv "文件名.txt" "wenjianming.txt"
```

### 2. Reproducible Build Test Failures
**Problem**: Dependency version conflicts between React 19 and @testing-library/react causing ERESOLVE errors.

**Solution**:
- Updated `frontend/package.json` to use exact versions (no ^ or ~) for all dependencies
- Added `--legacy-peer-deps` flag to npm install commands in CI/CD
- Enhanced dependency audit workflow with multi-platform testing

**Key Changes in package.json**:
```json
{
  "dependencies": {
    "react": "19.2.3",
    "react-dom": "19.2.3",
    "@testing-library/react": "16.3.1"
  }
}
```

**CI/CD Fix**:
```yaml
- name: Install dependencies
  run: |
    cd frontend
    npm ci --prefer-offline --no-audit --legacy-peer-deps
    npm ls --depth=0
```

### 3. Backend Dependency Management
**Problem**: Need for reproducible builds and security auditing with hashed dependencies.

**Solution**: Created pip-compile workflow for generating requirements.txt with dependency hashes.

**Files Created**:
- `scripts/generate_requirements.py` - Python script for generating requirements
- `.github/workflows/generate-requirements.yml` - Automated workflow

**Usage**:
```bash
# Generate requirements.txt with hashes
python scripts/generate_requirements.py

# Custom input/output files
python scripts/generate_requirements.py --input requirements.in --output requirements-prod.txt
```

**Workflow Features**:
- Daily automated updates at 2 AM UTC
- Automatic commit and push of changes
- Security auditing with safety
- Cross-platform compatibility

## Implementation Details

### Path Compliance Scanner (`scripts/scan_file_paths.py`)

**Features**:
- Recursive directory scanning
- Non-ASCII character detection
- Space detection in file names
- Automatic git mv command generation
- JSON and text output formats
- Skip directories (node_modules, .git, etc.)

**API**:
```python
from scripts.scan_file_paths import PathComplianceScanner

scanner = PathComplianceScanner("./project")
issues = scanner.scan()
commands = scanner.generate_git_mv_commands()
```

### Requirements Generator (`scripts/generate_requirements.py`)

**Features**:
- Automatic pip-tools installation
- requirements.in creation from existing requirements.txt
- Hashed dependency generation
- Validation and reporting
- Security audit integration

**Workflow Integration**:
```yaml
- name: Generate requirements.txt with hashes
  run: |
    cd backend
    pip-compile --verbose --output-file=requirements.txt requirements.in
```

### Enhanced CI/CD Pipeline

**Frontend Tests Job**:
- Added `--legacy-peer-deps` to resolve React 19 compatibility
- Enhanced dependency verification
- Improved error reporting

**Compliance Check Job**:
- Multi-platform path checking (Ubuntu, Windows)
- Python-based comprehensive scanning
- JSON artifact generation for detailed reporting

## Usage Instructions

### Running Path Compliance Check
```bash
# Local development
python scripts/scan_file_paths.py

# With JSON output for CI/CD
python scripts/scan_file_paths.py --output-format json > compliance-report.json
```

### Generating Requirements
```bash
# Generate for backend
python scripts/generate_requirements.py

# With custom output
python scripts/generate_requirements.py --output requirements-prod.txt
```

### Manual Dependency Resolution
If ERESOLVE issues persist:
```bash
# Clean install with legacy peer deps
npm ci --legacy-peer-deps

# Force resolution (use with caution)
npm install --force

# Use overrides in package.json
{
  "overrides": {
    "react": "19.2.3",
    "@testing-library/react": "16.3.1"
  }
}
```

## Monitoring and Maintenance

### Automated Workflows
1. **Path Compliance**: Runs on every PR/push to main/develop
2. **Requirements Generation**: Daily at 2 AM UTC, or when requirements.in changes
3. **Security Audit**: Part of requirements generation workflow

### Manual Checks
```bash
# Check path compliance
python scripts/scan_file_paths.py

# Verify requirements
python scripts/generate_requirements.py

# Test npm installation
cd frontend && npm ci --legacy-peer-deps
```

### Troubleshooting

**Path Issues**:
- Check for Chinese characters in directory names
- Look for spaces in file names
- Use git mv commands provided by the scanner

**Dependency Issues**:
- Ensure exact versions in package.json
- Use --legacy-peer-deps flag
- Check for conflicting peer dependencies

**Build Issues**:
- Verify requirements.txt has hashes
- Check Python version compatibility
- Ensure pip-tools is installed

## Security Considerations

### Dependency Hashing
- All backend dependencies now include SHA256 hashes
- Prevents supply chain attacks
- Ensures reproducible builds

### Path Security
- Prevents issues with non-ASCII characters in CI/CD
- Ensures compatibility across platforms
- Reduces npm installation failures

### Audit Integration
- Automated security scanning with safety
- Daily dependency updates
- Vulnerability reporting in JSON format

## Future Improvements

1. **Automated Path Fixing**: Script to automatically rename files with non-compliant paths
2. **Dependency Pinning**: Automatic pinning of all transitive dependencies
3. **Multi-Environment Requirements**: Separate requirements for dev, test, and production
4. **Enhanced Monitoring**: Real-time compliance monitoring and alerting

## Related Files

- `scripts/scan_file_paths.py` - Path compliance scanner
- `scripts/generate_requirements.py` - Requirements generator
- `.github/workflows/compliance-check.yml` - Compliance checking workflow
- `.github/workflows/generate-requirements.yml` - Requirements generation workflow
- `.github/workflows/ci-cd.yml` - Updated CI/CD with ERESOLVE fixes
- `frontend/package.json` - Updated with exact versions
- `backend/requirements.txt` - Will be updated by automated workflow
