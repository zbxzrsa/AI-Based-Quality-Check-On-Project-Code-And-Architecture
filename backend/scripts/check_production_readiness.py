#!/usr/bin/env python3
"""
生产就绪状态检查脚本
检查项目是否满足生产部署要求

使用方法:
    python check_production_readiness.py
    python check_production_readiness.py --verbose
    python check_production_readiness.py --export json
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


class Colors:
    """ANSI 颜色代码"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"
    BOLD = "\033[1m"


class Symbols:
    """输出符号 (兼容各种编码)"""

    PASS = "[OK]"
    WARNING = "[WW]"
    FAIL = "[NG]"
    ERROR = "[EE]"


class ProductionReadinessChecker:
    """生产就绪状态检查器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backend_root = self.project_root / "backend"
        self.frontend_root = self.project_root / "frontend"
        self.results = {"passed": [], "warning": [], "failed": [], "error": []}
        self.verbose = False

    def log_pass(self, message: str, details: str = ""):
        """记录通过的检查"""
        self.results["passed"].append(message)
        print(f"{Colors.GREEN}{Symbols.PASS}{Colors.END} {message}")
        if details and self.verbose:
            print(f"  {details}")

    def log_warning(self, message: str, details: str = ""):
        """记录警告"""
        self.results["warning"].append(message)
        print(f"{Colors.YELLOW}{Symbols.WARNING}{Colors.END} {message}")
        if details:
            print(f"  {details}")

    def log_fail(self, message: str, details: str = ""):
        """记录失败的检查"""
        self.results["failed"].append(message)
        print(f"{Colors.RED}{Symbols.FAIL}{Colors.END} {message}")
        if details:
            print(f"  {details}")

    def log_error(self, message: str, details: str = ""):
        """记录错误"""
        self.results["error"].append(message)
        print(f"{Colors.RED}{Symbols.ERROR}{Colors.END} {message}")
        if details:
            print(f"  {details}")

    def check_all(self) -> bool:
        """执行所有检查"""
        print(f"\n{Colors.BOLD}生产就绪状态检查{Colors.END}")
        print("=" * 60)

        # 1. 代码检查
        print(f"\n{Colors.BOLD}1. 代码质量检查{Colors.END}")
        self._check_code_quality()

        # 2. 配置检查
        print(f"\n{Colors.BOLD}2. 配置检查{Colors.END}")
        self._check_configuration()

        # 3. 文件检查
        print(f"\n{Colors.BOLD}3. 文件结构检查{Colors.END}")
        self._check_files()

        # 4. 安全检查
        print(f"\n{Colors.BOLD}4. 安全检查{Colors.END}")
        self._check_security()

        # 5. 文档检查
        print(f"\n{Colors.BOLD}5. 文档检查{Colors.END}")
        self._check_documentation()

        # 总结
        print(f"\n{Colors.BOLD}检查总结{Colors.END}")
        print("=" * 60)
        return self._print_summary()

    def _check_code_quality(self):
        """检查代码质量"""
        # 检查 Python 调试代码
        self._check_python_debug()
        # 检查 JavaScript 调试代码
        self._check_javascript_debug()

    def _check_python_debug(self):
        """检查 Python 文件中的调试代码"""
        debug_patterns = [
            (r"print\s*\(", "print() 语句应使用 logger"),
            (r"DEBUG\s*=\s*True", "DEBUG 模式应关闭"),
            (r"pdb\.set_trace", "调试器断点未移除"),
        ]

        issues = []
        for py_file in self.backend_root.rglob("*.py"):
            # 跳过虚拟环境、测试和脚本目录
            file_str = str(py_file)
            if "venv" in file_str or "test" in file_str or "scripts" in file_str or "__pycache__" in file_str:
                continue

            try:
                # 尝试 UTF-8，失败则尝试 GBK 或其他编码
                try:
                    content = py_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    try:
                        content = py_file.read_text(encoding="gbk")
                    except UnicodeDecodeError:
                        content = py_file.read_text(encoding="utf-8", errors="ignore")

                for pattern, message in debug_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        issues.append(f"{py_file.relative_to(self.backend_root)}:{line_num} - {message}")
            except Exception as e:
                if self.verbose:
                    self.log_warning(f"无法读取 {py_file}: {str(e)[:50]}")

        if issues:
            self.log_fail(f"发现 {len(issues)} 个 Python 调试代码问题", "详见:\n    " + "\n    ".join(issues[:5]))
        else:
            self.log_pass("无 Python 调试代码残留")

    def _check_javascript_debug(self):
        """检查 JavaScript 文件中的调试代码"""
        debug_patterns = [
            (r"console\.log", "console.log 应使用日志库"),
            (r"debugger\s*;", "调试器语句未移除"),
        ]

        issues = []
        for js_file in self.frontend_root.rglob("*.js"):
            if "node_modules" in str(js_file) or ".next" in str(js_file):
                continue

            try:
                # 多编码支持
                try:
                    content = js_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = js_file.read_text(encoding="utf-8", errors="ignore")

                for pattern, _message in debug_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        issues.append(f"{js_file.relative_to(self.frontend_root)}:{line_num}")
            except Exception:
                pass

        if issues:
            self.log_warning(f"发现 {len(issues)} 个 JavaScript 调试代码项", f"示例: {issues[0]}")
        else:
            self.log_pass("无 JavaScript 调试代码残留")

    def _check_configuration(self):
        """检查配置文件"""
        # 检查 .env 文件
        self._check_env_files()
        # 检查 Docker 配置
        self._check_docker_config()
        # 检查 package.json
        self._check_package_json()

    def _check_env_files(self):
        """检查环境配置文件"""
        env_prod = self.backend_root / ".env.production"
        env_prod_secure = self.backend_root / ".env.production.secure"

        if env_prod.exists():
            self.log_pass("发现 .env.production 文件")
            try:
                # 多编码支持
                try:
                    content = env_prod.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = env_prod.read_text(encoding="gbk", errors="ignore")

                if "localhost" in content.lower():
                    self.log_warning("发现 localhost 地址，应使用远程服务器")
                if "admin" in content.lower() and "123" in content:
                    self.log_warning("发现可能的硬编码凭证")
            except Exception as e:
                self.log_warning(f"无法检查 .env.production: {str(e)[:50]}")
        elif env_prod_secure.exists():
            self.log_pass("发现 .env.production.secure 模板")
            self.log_warning("需要创建 .env.production 并填入实际值")
        else:
            self.log_fail("未找到生产环境配置文件")

    def _check_docker_config(self):
        """检查 Docker 配置"""
        docker_compose_prod = self.project_root / "docker-compose.prod.yml"
        docker_compose_production = self.project_root / "docker-compose.production.yml"

        for file in [docker_compose_prod, docker_compose_production]:
            if file.exists():
                self.log_pass(f"发现 {file.name}")
                try:
                    # 多编码支持
                    try:
                        content = file.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        content = file.read_text(encoding="utf-8", errors="ignore")

                    if "localhost" in content and "RDS" not in content and "AWS" not in content:
                        self.log_warning(f"{file.name} 包含 localhost 引用")
                except Exception:
                    pass
                return

        self.log_warning("未找到 docker-compose.prod.yml 或 docker-compose.production.yml")

    def _check_package_json(self):
        """检查 package.json"""
        package_json = self.project_root / "package.json"
        self.frontend_root / "package.json"

        if package_json.exists():
            try:
                # 多编码支持
                try:
                    content = package_json.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = package_json.read_text(encoding="utf-8", errors="ignore")

                content_data = json.loads(content)
                scripts = content_data.get("scripts", {})

                if "build" in scripts:
                    self.log_pass("发现 build 脚本")
                else:
                    self.log_warning("未找到 build 脚本")
            except Exception as e:
                self.log_warning(f"无法检查 package.json: {str(e)[:50]}")

    def _check_files(self):
        """检查文件结构"""
        # 检查关键临时文件
        temp_files = [
            "test_db.py",
            "test_psycopg_conn.py",
            "debug_imports.py",
            "debug_imports_v2.py",
            "create_test_user.py",
        ]

        found_temp_files = []
        for temp_file in temp_files:
            file_path = self.backend_root / temp_file
            if file_path.exists():
                found_temp_files.append(temp_file)

        if found_temp_files:
            self.log_warning(f"发现 {len(found_temp_files)} 个临时文件应删除: {', '.join(found_temp_files)}")
        else:
            self.log_pass("无临时测试文件")

        # 检查关键文档
        docs_required = [
            "PRODUCTION_MIGRATION_AUDIT.md",
            "PRODUCTION_MIGRATION_EXECUTION_PLAN.md",
            "PRODUCTION_DEPLOYMENT_CHECKLIST.md",
        ]

        for doc in docs_required:
            doc_path = self.project_root / doc
            if doc_path.exists():
                self.log_pass(f"发现 {doc}")
            else:
                self.log_fail(f"缺失关键文档: {doc}")

    def _check_security(self):
        """检查安全配置"""
        # 检查是否有硬编码凭证
        self._check_hardcoded_credentials()
        # 检查 API 文档配置
        self._check_api_docs()
        # 检查 TLS 配置
        self._check_tls()

    def _check_hardcoded_credentials(self):
        """检查硬编码凭证"""
        # 更精确的硬编码凭证模式 - 排除常量定义和注释
        # 仅查找真实的、可能被泄露的凭证
        patterns = [
            # 实际的密码/密钥硬编码值（排除常量定义）
            (
                r'(?:password|pwd|passwd|secret|token|api[_-]?key|db_pass|db_password)\s*[:=]\s*["\']([a-zA-Z0-9]{8,})["\'](?!\s*#)',
                "硬编码凭证值",
            ),
            (
                r'(?:POSTGRES|MYSQL|MONGODB|REDIS)_(?:PASS|PASSWORD|SECRET)\s*=\s*["\'][^\"\']{1,}["\'](?!\s*#)',
                "数据库密码",
            ),
        ]

        critical_issues = []
        for pattern, issue_type in patterns:
            found_in = {}
            for py_file in self.backend_root.rglob("*.py"):
                # 跳过不应该包含凭证的目录
                file_str = str(py_file)
                skip_dirs = ["venv", "test", "__pycache__", "scripts", "examples", "migrate", "migrations"]
                if any(x in file_str for x in skip_dirs):
                    continue

                try:
                    # 多编码支持
                    try:
                        content = py_file.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        try:
                            content = py_file.read_text(encoding="gbk")
                        except UnicodeDecodeError:
                            content = py_file.read_text(encoding="utf-8", errors="ignore")

                    # 排除是常量定义的情况
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    real_credentials = []
                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        # 检查这行是否是注释或常量定义
                        start = max(0, content.rfind("\n", 0, match.start()) + 1)
                        end = content.find("\n", match.end())
                        if end == -1:
                            end = len(content)
                        line_content = content[start:end].strip()

                        # 排除常量定义（全大写）和注释
                        if not (line_content.startswith("#") or line_content.upper().startswith(line_content[:10])):
                            real_credentials.append(line_num)

                    if real_credentials:
                        found_in[str(py_file.relative_to(self.backend_root))] = real_credentials
                except Exception:
                    pass

            if found_in:
                for file_name, lines in list(found_in.items())[:1]:
                    critical_issues.append(f"{issue_type}: {file_name}:{lines[0]}")

        if critical_issues:
            self.log_fail(f"发现 {len(critical_issues)} 个潜在的硬编码凭证", "\n    ".join(critical_issues))
        else:
            self.log_pass("未发现明显的硬编码凭证")

    def _check_api_docs(self):
        """检查 API 文档配置"""
        main_py = self.backend_root / "app" / "main.py"

        if main_py.exists():
            try:
                # 尝试多种编码读取文件
                try:
                    content = main_py.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    try:
                        content = main_py.read_text(encoding="gbk")
                    except UnicodeDecodeError:
                        content = main_py.read_text(encoding="utf-8", errors="ignore")

                if "ENVIRONMENT" in content and "docs_url" in content:
                    self.log_pass("FastAPI 文档已条件配置")
                else:
                    self.log_warning("FastAPI 文档可能在生产环境暴露")
            except Exception as e:
                self.log_warning(f"无法检查 API 文档配置: {str(e)[:50]}")

    def _check_tls(self):
        """检查 TLS 配置"""
        docker_compose = self.project_root / "docker-compose.prod.yml"

        if docker_compose.exists():
            try:
                # 多编码支持
                try:
                    content = docker_compose.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = docker_compose.read_text(encoding="utf-8", errors="ignore")

                if "ssl" in content.lower() or "tls" in content.lower() or "443" in content:
                    self.log_pass("发现 TLS/SSL 配置")
                else:
                    self.log_warning("未找到明显的 TLS 配置")
            except Exception:
                self.log_warning("无法检查 TLS 配置")
        else:
            self.log_warning("无法检查 TLS 配置 (缺少 docker-compose.prod.yml)")

    def _check_documentation(self):
        """检查文档完整性"""
        required_sections = {
            "PRODUCTION_MIGRATION_AUDIT.md": [
                "78 个",
                "全面分析",
                "安全",
                "性能",
            ],
            "PRODUCTION_MIGRATION_EXECUTION_PLAN.md": [
                "7 个阶段",
                "具体任务",
                "时间表",
            ],
            "PRODUCTION_DEPLOYMENT_CHECKLIST.md": [
                "检查项",
                "签署",
                "验收",
            ],
        }

        for doc_name, sections in required_sections.items():
            doc_path = self.project_root / doc_name
            if doc_path.exists():
                try:
                    # 多编码支持
                    try:
                        content = doc_path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        content = doc_path.read_text(encoding="gbk", errors="ignore")

                    missing = []
                    for section in sections:
                        if section not in content:
                            missing.append(section)

                    if missing:
                        self.log_warning(f"{doc_name} 缺少内容: {', '.join(missing)}")
                    else:
                        self.log_pass(f"发现 {doc_name}")
                except Exception as e:
                    self.log_warning(f"无法读取 {doc_name}: {str(e)[:50]}")
            else:
                self.log_fail(f"缺失 {doc_name}")

    def _print_summary(self) -> bool:
        """打印检查总结"""
        passed = len(self.results["passed"])
        warnings = len(self.results["warning"])
        failed = len(self.results["failed"])
        errors = len(self.results["error"])

        passed + warnings + failed + errors

        print(
            f"\n通过: {Colors.GREEN}{passed}{Colors.END} | "
            f"警告: {Colors.YELLOW}{warnings}{Colors.END} | "
            f"失败: {Colors.RED}{failed}{Colors.END} | "
            f"错误: {Colors.RED}{errors}{Colors.END}"
        )

        if failed > 0 or errors > 0:
            print(f"\n{Colors.RED}[ERROR] 项目未就绪部署{Colors.END}")
            print(f"请解决 {failed + errors} 个关键问题:")
            for issue in self.results["failed"] + self.results["error"]:
                print(f"  - {issue}")
            return False
        elif warnings > 0:
            print(f"\n{Colors.YELLOW}[WARN] 项目基本就绪，但有 {warnings} 个警告项{Colors.END}")
            return True
        else:
            print(f"\n{Colors.GREEN}[OK] 项目已就绪部署！{Colors.END}")
            return True

    def export_results(self, format: str = "json"):
        """导出检查结果"""
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "summary": {
                "total": sum(len(v) for v in self.results.values()),
                "passed": len(self.results["passed"]),
                "warnings": len(self.results["warning"]),
                "failed": len(self.results["failed"]),
                "errors": len(self.results["error"]),
            },
        }

        if format == "json":
            output_file = self.project_root / "production_readiness_report.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            print(f"\n✓ 报告已导出到: {output_file}")
            return output_file

        return None


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="生产就绪状态检查")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--export", choices=["json"], help="导出报告格式")
    parser.add_argument("--project-root", default=".", help="项目根目录")

    args = parser.parse_args()

    checker = ProductionReadinessChecker(project_root=args.project_root)
    checker.verbose = args.verbose

    success = checker.check_all()

    if args.export:
        checker.export_results(format=args.export)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
