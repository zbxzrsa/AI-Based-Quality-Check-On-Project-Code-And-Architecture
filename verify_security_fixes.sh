#!/bin/bash
# Security Fixes Verification Script
# 验证所有CI/CD安全修复

set -e

echo "════════════════════════════════════════════════════"
echo "🔐 AI Code Review Platform - Security Fixes Verification"
echo "════════════════════════════════════════════════════"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Helper functions
check_pass() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}❌ FAIL:${NC} $1"
    ((FAILED++))
}

check_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠️  WARN:${NC} $1"
}

echo ""
echo "════ 1. 检查密钥迁移文件 ════"
echo ""

# Check .env.example exists
if [ -f ".env.example" ]; then
    check_pass ".env.example 文件存在"
    
    # Check for common keys in .env.example
    if grep -q "POSTGRES_PASSWORD" ".env.example" && \
       grep -q "JWT_SECRET" ".env.example" && \
       grep -q "REDIS_PASSWORD" ".env.example"; then
        check_pass ".env.example 包含必要的密钥模板"
    else
        check_fail ".env.example 缺少必要的密钥"
    fi
else
    check_fail ".env.example 文件不存在"
fi

# Check .env is in .gitignore
if [ -f ".gitignore" ] && grep -q "^\.env" ".gitignore"; then
    check_pass ".env 在 .gitignore 中"
else
    check_fail ".env 未在 .gitignore 中"
fi

echo ""
echo "════ 2. 检查代码修复 ════"
echo ""

# Check locustfile has been fixed
if grep -q 'os.getenv("TEST_USER_PASSWORD"' "load_testing/locustfile.py" 2>/dev/null; then
    check_pass "load_testing/locustfile.py 已使用环境变量"
else
    check_fail "load_testing/locustfile.py 仍有硬编码密码"
fi

# Check go_parser subprocess fix
if grep -q 'shell=False' "backend/app/services/parsers/go_parser.py" 2>/dev/null; then
    check_pass "go_parser.py 已修复 subprocess 安全问题"
else
    check_fail "go_parser.py subprocess 安全问题未修复"
fi

# Check serializers has security warnings
if grep -q "SECURITY WARNING" "backend/app/utils/serializers.py" 2>/dev/null; then
    check_pass "serializers.py 包含安全警告"
else
    check_fail "serializers.py 缺少安全警告"
fi

echo ""
echo "════ 3. 检查依赖更新 ════"
echo ""

# Check requirements.txt has security tools
if grep -q "bandit" "backend/requirements.txt" && \
   grep -q "safety" "backend/requirements.txt"; then
    check_pass "requirements.txt 包含安全扫描工具"
else
    check_fail "requirements.txt 缺少安全扫描工具"
fi

echo ""
echo "════ 4. 检查 Dockerfile 改进 ════"
echo ""

# Check Backend Dockerfile multi-stage
if grep -q "as builder" "backend/Dockerfile" && \
   grep -q "from builder" "backend/Dockerfile"; then
    check_pass "Backend Dockerfile 使用多阶段构建"
else
    check_fail "Backend Dockerfile 未使用多阶段构建"
fi

# Check Backend Dockerfile non-root user
if grep -q "USER appuser" "backend/Dockerfile"; then
    check_pass "Backend Dockerfile 使用非 root 用户"
else
    check_fail "Backend Dockerfile 未使用非 root 用户"
fi

# Check Frontend Dockerfile multi-stage
if grep -q "as deps" "frontend/Dockerfile" && \
   grep -q "as builder" "frontend/Dockerfile"; then
    check_pass "Frontend Dockerfile 使用多阶段构建"
else
    check_fail "Frontend Dockerfile 未使用多阶段构建"
fi

# Check Frontend Dockerfile non-root
if grep -q "USER nextjs" "frontend/Dockerfile"; then
    check_pass "Frontend Dockerfile 使用非 root 用户"
else
    check_fail "Frontend Dockerfile 未使用非 root 用户"
fi

# Check Worker Dockerfile improvements
if grep -q "as builder" "backend/Dockerfile.worker"; then
    check_pass "Worker Dockerfile 使用多阶段构建"
else
    check_fail "Worker Dockerfile 未使用多阶段构建"
fi

echo ""
echo "════ 5. 检查 ESLint 配置 ════"
echo ""

# Check ESLint configuration
if [ -f "frontend/.eslintrc.json" ]; then
    if grep -q '"@typescript-eslint/explicit-function-return-types": "error"' "frontend/.eslintrc.json" && \
       grep -q '"@typescript-eslint/no-explicit-any": "error"' "frontend/.eslintrc.json"; then
        check_pass "ESLint 包含严格类型规则"
    else
        check_fail "ESLint 缺少严格类型规则"
    fi
else
    check_fail "ESLint 配置文件不存在"
fi

echo ""
echo "════ 6. 检查 GitHub Actions 工作流 ════"
echo ""

# Check security-scanning workflow exists
if [ -f ".github/workflows/security-scanning.yml" ]; then
    check_pass "security-scanning.yml 工作流存在"
    
    # Check for specific jobs
    if grep -q "python-security" ".github/workflows/security-scanning.yml" && \
       grep -q "npm-security" ".github/workflows/security-scanning.yml" && \
       grep -q "tuffleHog-secrets" ".github/workflows/security-scanning.yml"; then
        check_pass "工作流包含所有必要的扫描作业"
    else
        check_fail "工作流缺少某些扫描作业"
    fi
    
    # Check for PR creation
    if grep -q "create-pull-request" ".github/workflows/security-scanning.yml"; then
        check_pass "工作流支持自动 PR 创建"
    else
        check_fail "工作流不支持自动 PR 创建"
    fi
else
    check_fail "security-scanning.yml 工作流不存在"
fi

echo ""
echo "════ 7. 检查文档 ════"
echo ""

# Check documentation files
if [ -f "docs/SECRETS_MIGRATION_GUIDE.md" ]; then
    check_pass "SECRETS_MIGRATION_GUIDE.md 存在"
else
    check_fail "SECRETS_MIGRATION_GUIDE.md 不存在"
fi

if [ -f "docs/NPM_AUDIT_GUIDE.md" ]; then
    check_pass "NPM_AUDIT_GUIDE.md 存在"
else
    check_fail "NPM_AUDIT_GUIDE.md 不存在"
fi

if [ -f "SECURITY_FIXES_SUMMARY.md" ]; then
    check_pass "SECURITY_FIXES_SUMMARY.md 存在"
else
    check_fail "SECURITY_FIXES_SUMMARY.md 不存在"
fi

echo ""
echo "════ 8. 检查脚本文件 ════"
echo ""

if [ -f "scripts/remove_git_secrets.sh" ]; then
    check_pass "remove_git_secrets.sh 脚本存在"
    if [ -x "scripts/remove_git_secrets.sh" ]; then
        check_pass "remove_git_secrets.sh 可执行"
    else
        check_warn "remove_git_secrets.sh 不可执行，运行: chmod +x scripts/remove_git_secrets.sh"
    fi
else
    check_fail "remove_git_secrets.sh 脚本不存在"
fi

echo ""
echo "════ 9. 可选验证 (需要工具) ════"
echo ""

# Check if Python tools are available
if command -v bandit &> /dev/null; then
    check_pass "Bandit 已安装"
    
    # Run basic Bandit check
    if bandit -r backend/app -ll -q 2>/dev/null | head -1 | grep -q "Issue"; then
        check_warn "Bandit 发现问题 (请手动审查)"
    else
        check_pass "Bandit 未发现关键问题"
    fi
else
    check_info "Bandit 未安装 (可选: pip install bandit)"
fi

if command -v safety &> /dev/null; then
    check_pass "Safety 已安装"
else
    check_info "Safety 未安装 (可选: pip install safety)"
fi

if command -v trufflehog &> /dev/null; then
    check_pass "TruffleHog 已安装"
else
    check_info "TruffleHog 未安装 (可选: pip install truffleHog)"
fi

if command -v npm &> /dev/null; then
    check_pass "npm 已安装"
    
    # Check npm audit
    cd frontend && npm audit --quiet 2>/dev/null || true
    check_info "npm audit 报告已生成"
    cd ..
else
    check_info "npm 未安装"
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "📊 验证总结"
echo "════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}✅ 通过: $PASSED${NC}"
echo -e "${RED}❌ 失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有检查通过！${NC}"
    echo ""
    echo "后续步骤:"
    echo "1. 确保 .env 已在 .gitignore 中"
    echo "2. 复制 .env.example 到 .env 并更新实际凭证"
    echo "3. 运行: git add -A && git commit -m 'fix: CI/CD security improvements'"
    echo "4. 推送到 GitHub 并验证 GitHub Actions 工作流运行"
    echo "5. 检查生成的安全报告"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  发现 $FAILED 个问题，需要修复${NC}"
    echo ""
    exit 1
fi
