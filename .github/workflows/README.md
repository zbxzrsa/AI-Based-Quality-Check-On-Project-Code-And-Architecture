# GitHub Actions Workflows

This directory contains all CI/CD workflows for the frontend application.

## Workflows Overview

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| CI Pipeline | `ci.yml` | Push/PR | Lint, test, coverage validation |
| Build Pipeline | `build.yml` | Push/PR/After CI | Build and create artifacts |
| Deploy Pipeline | `deploy.yml` | Manual/After Build | Deploy to test/production |
| Rollback Pipeline | `rollback.yml` | Manual | Rollback deployments |
| Lighthouse CI | `lighthouse.yml` | Push/PR/Manual | Performance auditing |

## Quick Start

### 1. First Time Setup

```bash
# Install dependencies
cd frontend
npm install

# Verify local setup
npm run lint
npm run type-check
npm run test:ci
npm run build
```

### 2. Making Changes

1. Create a feature branch
2. Make your changes
3. Run tests locally: `npm test`
4. Push to GitHub
5. CI will automatically run
6. Review CI results in PR

### 3. Deploying

**To Test Environment:**
- Automatic on main branch merge

**To Production:**
1. Go to Actions → Deploy Pipeline
2. Click "Run workflow"
3. Select "production"
4. Approve deployment

## Workflow Details

### CI Pipeline

**What it does:**
- ✅ Runs ESLint
- ✅ Runs TypeScript type checking
- ✅ Runs all tests
- ✅ Validates 80% coverage threshold
- ✅ Comments PR with coverage report

**When it runs:**
- Every push to main/develop
- Every pull request

**How to fix failures:**
- Linting: `npm run lint:fix`
- Type errors: `npm run type-check`
- Tests: `npm test`
- Coverage: Add more tests

### Build Pipeline

**What it does:**
- ✅ Builds production bundle
- ✅ Verifies build output
- ✅ Creates compressed artifact
- ✅ Uploads to GitHub
- ✅ Comments PR with build info

**When it runs:**
- After CI passes
- On push/PR to main/develop

**Artifacts:**
- `frontend-build-{SHA}.tar.gz` (30 days)
- `build-metadata.json` (30 days)

### Deploy Pipeline

**What it does:**
- ✅ Downloads build artifacts
- ✅ Deploys to environment
- ✅ Creates backup (production)
- ✅ Runs health checks
- ✅ Creates deployment record
- ✅ Creates GitHub release (production)

**Environments:**
- **test**: Auto-deploy on main
- **production**: Manual only

**Customization needed:**
- Update deployment commands for your infrastructure
- Configure GitHub Environments
- Add deployment secrets

### Rollback Pipeline

**What it does:**
- ✅ Restores previous version
- ✅ Runs health checks
- ✅ Creates incident issue
- ✅ Records rollback

**How to use:**
1. Actions → Rollback Pipeline
2. Select environment
3. Enter backup_id OR previous_sha
4. Run workflow

### Lighthouse CI

**What it does:**
- ✅ Audits all core pages
- ✅ Validates performance ≥ 90%
- ✅ Checks Core Web Vitals
- ✅ Comments PR with results
- ✅ Uploads detailed reports

**Thresholds:**
- Performance: ≥ 90% (required)
- FCP: < 2000ms
- LCP: < 2500ms
- CLS: < 0.1

## Configuration Files

| File | Purpose |
|------|---------|
| `frontend/lighthouserc.json` | Lighthouse CI configuration |
| `frontend/package.json` | Scripts and dependencies |
| `frontend/.env.production.example` | Production environment template for local copies |

## Required Secrets

Configure in Settings → Secrets:

**Optional:**
- `LHCI_GITHUB_APP_TOKEN` - Lighthouse CI token
- `CODECOV_TOKEN` - Codecov upload token
- `PRODUCTION_API_URL` - Production API URL

**For Deployment:**
- Add secrets based on your infrastructure

## Monitoring

### Check Workflow Status

1. Go to Actions tab
2. Select workflow
3. View recent runs
4. Click run for details

### View Artifacts

1. Go to Actions tab
2. Click on workflow run
3. Scroll to Artifacts section
4. Download artifacts

### View Reports

**Coverage:**
- PR comments
- Codecov dashboard

**Lighthouse:**
- PR comments
- Workflow step summary
- Downloaded artifacts

## Troubleshooting

### Workflow Not Running

**Check:**
- Branch name matches trigger
- Workflow file syntax is valid
- GitHub Actions is enabled

### Workflow Failing

**CI Pipeline:**
- Check lint errors: `npm run lint`
- Check type errors: `npm run type-check`
- Check test failures: `npm test`
- Check coverage: `npm run test:coverage`

**Build Pipeline:**
- Check build locally: `npm run build`
- Verify environment variables
- Check build logs

**Deploy Pipeline:**
- Verify artifact exists
- Check deployment commands
- Verify secrets configured
- Check server connectivity

**Lighthouse CI:**
- Check performance locally
- Review Lighthouse report
- Optimize based on recommendations

### Artifact Not Found

**Causes:**
- Artifact expired (30 days)
- Build didn't complete
- Wrong SHA provided

**Solution:**
- Re-run build workflow
- Use correct SHA
- Check artifact retention

## Best Practices

### 1. Always Run Tests Locally

```bash
npm run lint
npm run type-check
npm test
npm run build
```

### 2. Keep Coverage Above 80%

- Write tests for new code
- Check coverage: `npm run test:coverage`
- Review coverage report

### 3. Monitor Performance

- Check Lighthouse scores
- Optimize if score drops
- Review Core Web Vitals

### 4. Safe Deployments

- Deploy to test first
- Monitor after deployment
- Keep backups
- Test rollback procedure

### 5. Document Changes

- Update documentation
- Add comments to workflows
- Document deployment steps

## Maintenance

### Update Dependencies

```bash
cd frontend
npm update
npm audit fix
```

### Update Node.js Version

1. Update in workflow files
2. Update in `package.json` engines
3. Test locally
4. Update documentation

### Clean Old Artifacts

- Artifacts auto-delete after retention period
- Manually delete if needed in Actions tab

## Support

**For help:**
1. Check this README
2. Review workflow logs
3. Check main documentation: `frontend/CI_CD_PIPELINE.md`
4. Create an issue

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Lighthouse CI Documentation](https://github.com/GoogleChrome/lighthouse-ci)
- [Jest Documentation](https://jestjs.io/)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
