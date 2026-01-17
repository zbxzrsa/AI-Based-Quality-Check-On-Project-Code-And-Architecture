# NPM Cache Cleanup Guide

This guide provides comprehensive instructions for cleaning up npm cache and removing Chinese path references to ensure your project is ready for CI/CD environments.

## Overview

The npm cache cleanup process addresses the issue where npm logs and cache files are being saved to directories with Chinese characters in their names, causing path interference in professional development environments.

## Scripts Provided

### 1. Cleanup Scripts

#### `scripts/clean-npm-cache.sh` (Linux/macOS)
Comprehensive bash script that:
- Deletes `node_modules` and `package-lock.json`
- Runs `npm cache clean --force`
- Unsets custom cache/prefix configurations with Chinese paths
- Configures `npm_config_cache` environment variable for current session
- Verifies the project is "Path-Clean"

#### `scripts/clean-npm-cache.bat` (Windows)
Windows batch version of the cleanup script with the same functionality as the bash version.

### 2. Verification Scripts

#### `scripts/verify-path-clean.sh` (Linux/macOS)
Comprehensive verification script that:
- Checks npm configurations for Chinese characters
- Verifies environment variables
- Scans project files for Chinese characters
- Tests npm commands
- Provides final assessment

#### `scripts/verify-path-clean.bat` (Windows)
Windows batch version of the verification script.

## Quick Start

### For Windows Users (Recommended)

1. **Run the cleanup script:**
   ```cmd
   cd D:\Desktop\AI-Based-Quality-Check-On-Project-Code-And-Architecture
   scripts\clean-npm-cache.bat
   ```

2. **Verify the cleanup:**
   ```cmd
   scripts\verify-path-clean.bat
   ```

### For Linux/macOS Users

1. **Make scripts executable:**
   ```bash
   chmod +x scripts/clean-npm-cache.sh scripts/verify-path-clean.sh
   ```

2. **Run the cleanup script:**
   ```bash
   ./scripts/clean-npm-cache.sh
   ```

3. **Verify the cleanup:**
   ```bash
   ./scripts/verify-path-clean.sh
   ```

## Detailed Usage

### Step-by-Step Cleanup Process

1. **Delete Dependencies**
   - Removes `node_modules` directory
   - Removes `package-lock.json` file

2. **Clean npm Cache**
   - Executes `npm cache clean --force`
   - Clears all cached packages

3. **Check Configurations**
   - Examines current npm cache, prefix, and tmp settings
   - Identifies any paths containing Chinese characters

4. **Unset Problematic Configurations**
   - Removes npm configurations pointing to Chinese paths
   - Unsets environment variables with Chinese paths

5. **Configure Clean Cache Path**
   - Sets `npm_config_cache` to project-specific directory
   - Updates npm cache configuration to use clean path

6. **Verify Results**
   - Confirms no Chinese characters remain in configurations
   - Tests npm commands work correctly
   - Scans project files for any remaining issues

### Environment Variable Configuration

The scripts automatically set the `npm_config_cache` environment variable for the current session:

```bash
# For current session only
export npm_config_cache="D:\Desktop\AI-Based-Quality-Check-On-Project-Code-And-Architecture\.npm-cache"
```

To make this permanent, add it to your shell profile:
- **Windows**: Add to system environment variables
- **Linux/macOS**: Add to `~/.bashrc`, `~/.zshrc`, or equivalent

## Understanding the Output

### Success Indicators
- ✅ Green checkmarks indicate successful checks
- 🎉 "PROJECT IS PATH-CLEAN!" means verification passed
- All npm configurations show clean paths

### Warning Indicators
- ⚠️ Yellow warnings indicate potential issues
- Files not found warnings are normal after cleanup

### Error Indicators
- ❌ Red errors indicate problems that need attention
- Chinese characters found in paths require cleanup
- Command failures indicate configuration issues

## Troubleshooting

### Common Issues

1. **npm command not found**
   - Install Node.js and npm from [nodejs.org](https://nodejs.org/)
   - Ensure npm is in your PATH

2. **Permission denied errors**
   - Run terminal as administrator (Windows)
   - Check file permissions (Linux/macOS)

3. **Chinese characters still detected**
   - Re-run cleanup script
   - Check system environment variables
   - Verify no Chinese characters in project directory name

4. **npm cache directory not writable**
   - Check directory permissions
   - Ensure sufficient disk space
   - Verify no file locks or processes using the directory

### Manual Cleanup

If scripts fail, you can manually perform the cleanup:

1. **Delete dependencies:**
   ```bash
   rm -rf node_modules package-lock.json
   ```

2. **Clean cache:**
   ```bash
   npm cache clean --force
   ```

3. **Reset npm configurations:**
   ```bash
   npm config delete cache
   npm config delete prefix
   npm config delete tmp
   ```

4. **Set clean cache path:**
   ```bash
   npm config set cache "$PWD/.npm-cache"
   export npm_config_cache="$PWD/.npm-cache"
   ```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Clean npm cache
on: [push, pull_request]

jobs:
  clean-cache:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Clean npm cache
        run: |
          npm cache clean --force
          npm config set cache ${{ github.workspace }}/.npm-cache
          export npm_config_cache=${{ github.workspace }}/.npm-cache
```

### Docker Example

```dockerfile
# In your Dockerfile
RUN npm cache clean --force
RUN npm config set cache /app/.npm-cache
ENV npm_config_cache=/app/.npm-cache
```

## Best Practices

1. **Regular Verification**
   - Run verification script before major deployments
   - Include in CI/CD pipeline checks

2. **Environment Consistency**
   - Use same npm cache path across development and production
   - Document cache path in project README

3. **Project Organization**
   - Keep project directories in English paths
   - Avoid special characters in project names

4. **Team Communication**
   - Share cleanup scripts with team members
   - Document any project-specific cache configurations

## Script Customization

### Modifying Cache Path

Edit the scripts to change the default cache path:

```bash
# In clean-npm-cache.sh
NEW_CACHE_PATH="$CURRENT_DIR/.npm-cache"
# Change to:
NEW_CACHE_PATH="/custom/path/.npm-cache"
```

### Adding Custom Checks

Extend verification scripts to check additional configurations:

```bash
# Add to verify-path-clean.sh
echo "Checking custom configuration..."
# Your custom check here
```

## Support

If you encounter issues:

1. Run verification script to identify problems
2. Check npm documentation for configuration options
3. Review project-specific requirements
4. Consult team DevOps practices

## Related Documentation

- [npm Configuration Documentation](https://docs.npmjs.com/cli/v9/using-npm/config)
- [npm Cache Documentation](https://docs.npmjs.com/cli/v9/commands/npm-cache)
- [CI/CD Best Practices](docs/CI_CD_BEST_PRACTICES.md)
