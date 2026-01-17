# NPM Cache Cleanup - Quick Reference

## Quick Commands

### Windows (Recommended for your environment)
```cmd
# Run cleanup
scripts\clean-npm-cache.bat

# Verify cleanup
scripts\verify-path-clean.bat

# Manual commands if scripts fail
npm cache clean --force
npm config delete cache
npm config delete prefix
npm config delete tmp
npm config set cache "%CD%\.npm-cache"
set npm_config_cache=%CD%\.npm-cache
```

### Linux/macOS
```bash
# Make scripts executable
chmod +x scripts/clean-npm-cache.sh scripts/verify-path-clean.sh

# Run cleanup
./scripts/clean-npm-cache.sh

# Verify cleanup
./scripts/verify-path-clean.sh

# Manual commands if scripts fail
npm cache clean --force
npm config delete cache
npm config delete prefix
npm config delete tmp
npm config set cache "$PWD/.npm-cache"
export npm_config_cache="$PWD/.npm-cache"
```

## Key Environment Variable

```bash
# Set for current session
npm_config_cache=D:\Desktop\AI-Based-Quality-Check-On-Project-Code-And-Architecture\.npm-cache

# Make permanent (Windows)
# Add to System Properties > Environment Variables

# Make permanent (Linux/macOS)
echo 'export npm_config_cache="$PWD/.npm-cache"' >> ~/.bashrc
```

## Verification Checklist

✅ **npm cache path**: Should be in English characters only  
✅ **npm prefix path**: Should be in English characters only  
✅ **npm tmp path**: Should be in English characters only  
✅ **Environment variables**: No Chinese characters  
✅ **.npmrc file**: No Chinese characters  
✅ **npm commands**: Work without errors  

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `npm command not found` | Install Node.js/npm from nodejs.org |
| `Permission denied` | Run as administrator (Windows) or use sudo (Linux/macOS) |
| Chinese paths still detected | Re-run cleanup script, check system environment variables |
| Cache directory not writable | Check permissions, ensure sufficient disk space |

## Project Status

**Current Directory**: `D:\Desktop\AI-Based-Quality-Check-On-Project-Code-And-Architecture`  
**npm Version**: 11.6.2  
**Node.js Version**: v24.12.0  

## Script Locations

- **Cleanup Scripts**: `scripts/clean-npm-cache.{sh,bat}`
- **Verification Scripts**: `scripts/verify-path-clean.{sh,bat}`
- **Documentation**: `docs/NPM_CACHE_CLEANUP_GUIDE.md`

## CI/CD Integration

### GitHub Actions
```yaml
- name: Clean npm cache
  run: |
    npm cache clean --force
    npm config set cache ${{ github.workspace }}/.npm-cache
    export npm_config_cache=${{ github.workspace }}/.npm-cache
```

### Docker
```dockerfile
RUN npm cache clean --force
RUN npm config set cache /app/.npm-cache
ENV npm_config_cache=/app/.npm-cache
```

## Support

1. **Run verification first**: `scripts\verify-path-clean.bat`
2. **Check npm documentation**: https://docs.npmjs.com/
3. **Review project requirements**: Check team DevOps practices
4. **Contact team**: Share verification results with DevOps team

## Next Steps

1. Run cleanup script: `scripts\clean-npm-cache.bat`
2. Verify results: `scripts\verify-path-clean.bat`
3. If successful, project is ready for CI/CD
4. Add verification to deployment pipeline
5. Document cache path in project README
