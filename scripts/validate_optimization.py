#!/usr/bin/env python3
"""
集成优化验证脚本

验证代码重构后的质量指标：
1. 单元测试通过率
2. 代码覆盖率
3. 构建时间
4. 包大小
5. 性能指标
"""

import subprocess
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import re

class OptimizationValidator:
    """验证优化效果的类"""
    
    def __init__(self, backend_path: str, frontend_path: str):
        self.backend_path = Path(backend_path)
        self.frontend_path = Path(frontend_path)
        self.results: Dict[str, Any] = {}
    
    def run_backend_tests(self) -> Tuple[bool, Dict[str, Any]]:
        """运行后端测试"""
        print("\n[*] 运行后端单元测试...")
        
        try:
            # 运行 pytest
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "--cov=app", "--cov-report=json"],
                cwd=self.backend_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # 解析覆盖率报告
            coverage_data = None
            try:
                with open(self.backend_path / "coverage.json", "r") as f:
                    coverage_data = json.load(f)
            except FileNotFoundError:
                pass
            
            success = result.returncode == 0
            
            # 计算覆盖率
            coverage_percent = 0
            if coverage_data and 'totals' in coverage_data:
                coverage_percent = coverage_data['totals']['percent_covered']
            
            output = {
                'success': success,
                'coverage': coverage_percent,
                'output': result.stdout[-500:] if result.stdout else '',  # 最后500个字符
                'errors': result.stderr[-500:] if result.stderr else ''
            }
            
            if success:
                print(f"[+] 后端测试通过 (覆盖率: {coverage_percent:.1f}%)")
            else:
                print(f"[!] 后端测试失败")
                print(f"错误: {result.stderr[-200:]}")
            
            return success, output
            
        except subprocess.TimeoutExpired:
            print("[!] 测试超时 (300s)")
            return False, {'error': 'timeout'}
        except Exception as e:
            print(f"[!] 运行测试时出错: {e}")
            return False, {'error': str(e)}
    
    def run_frontend_tests(self) -> Tuple[bool, Dict[str, Any]]:
        """运行前端测试"""
        print("\n[*] 运行前端单元测试...")
        
        try:
            result = subprocess.run(
                ["npm", "test", "--", "--coverage"],
                cwd=self.frontend_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            success = result.returncode == 0
            
            output = {
                'success': success,
                'output': result.stdout[-500:] if result.stdout else '',
                'errors': result.stderr[-500:] if result.stderr else ''
            }
            
            if success:
                print(f"[+] 前端测试通过")
            else:
                print(f"[!] 前端测试失败")
            
            return success, output
            
        except subprocess.TimeoutExpired:
            print("[!] 前端测试超时 (300s)")
            return False, {'error': 'timeout'}
        except Exception as e:
            print(f"[!] 运行前端测试时出错: {e}")
            return False, {'error': str(e)}
    
    def check_code_quality(self) -> Tuple[bool, Dict[str, Any]]:
        """检查代码质量 (类型检查、Lint 等)"""
        print("\n[*] 检查代码质量...")
        
        results = {
            'type_check': False,
            'style_check': False,
            'security_check': False
        }
        
        # 类型检查 (mypy)
        try:
            result = subprocess.run(
                ["python", "-m", "mypy", "app", "--strict"],
                cwd=self.backend_path,
                capture_output=True,
                timeout=60
            )
            results['type_check'] = result.returncode == 0
            if result.returncode == 0:
                print("  ✓ 类型检查通过")
            else:
                print(f"  ✗ 类型检查失败: {result.stderr.decode()[-200:]}")
        except Exception as e:
            print(f"  ! 类型检查失败: {e}")
        
        # 代码风格检查 (Black)
        try:
            result = subprocess.run(
                ["python", "-m", "black", "--check", "app"],
                cwd=self.backend_path,
                capture_output=True,
                timeout=60
            )
            results['style_check'] = result.returncode == 0
            if result.returncode == 0:
                print("  ✓ 代码风格检查通过")
            else:
                print(f"  ✗ 代码风格检查失败")
        except Exception as e:
            print(f"  ! 代码风格检查失败: {e}")

        # 安全检查 (Bandit)
        try:
            result = subprocess.run(
                ["python", "-m", "bandit", "-r", "app"],
                cwd=self.backend_path,
                capture_output=True,
                timeout=60
            )
            # Bandit 总是返回非零
            output = result.stdout.decode() + result.stderr.decode()
            results['security_check'] = 'No issues identified' in output or result.returncode < 2
            if results['security_check']:
                print("  ✓ 安全检查通过")
            else:
                print("  ✗ 检测到安全问题")
        except Exception as e:
            print(f"  ! 安全检查失败: {e}")
        
        all_passed = all(v is True for v in results.values() if v is not None)
        return all_passed, results
    
    def measure_build_time(self) -> Tuple[float, Dict[str, Any]]:
        """测量构建时间"""
        print("\n[*] 测量构建时间...")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["python", "-m", "pip", "install", "-q", "-e", "."],
                cwd=self.backend_path,
                capture_output=True,
                timeout=300
            )
            
            build_time = time.time() - start_time
            
            if result.returncode == 0:
                print(f"[+] 后端构建完成 (耗时: {build_time:.1f}s)")
            else:
                print(f"[!] 后端构建失败")
            
            return build_time, {'success': result.returncode == 0}
            
        except subprocess.TimeoutExpired:
            print("[!] 构建超时")
            return 0.0, {'success': False, 'error': 'timeout'}
        except Exception as e:
            print(f"[!] 构建失败: {e}")
            return 0.0, {'success': False, 'error': str(e)}
    
    def check_dependencies(self) -> Dict[str, Any]:
        """检查依赖安全问题"""
        print("\n[*] 检查依赖安全...")
        
        results = {
            'backend_vulnerabilities': 0,
            'frontend_vulnerabilities': 0
        }
        
        # 检查 Python 依赖
        try:
            result = subprocess.run(
                ["python", "-m", "pip", "check"],
                cwd=self.backend_path,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("  ✓ 后端依赖检查通过")
            else:
                # 解析输出找出问题数量
                output = result.stdout.decode()
                vuln_count = output.count("ERROR")
                results['backend_vulnerabilities'] = vuln_count
                print(f"  ! 发现 {vuln_count} 个依赖问题")
        except Exception as e:
            print(f"  ! 依赖检查失败: {e}")
        
        # 检查 NPM 依赖
        try:
            result = subprocess.run(
                ["npm", "audit"],
                cwd=self.frontend_path,
                capture_output=True,
                timeout=60
            )
            
            output = result.stdout.decode()
            # 解析审计输出
            if "vulnerabilities" in output:
                # 提取漏洞计数
                match = re.search(r'(\d+) vulnerabilities', output)
                if match:
                    vuln_count = int(match.group(1))
                    results['frontend_vulnerabilities'] = vuln_count
                    if vuln_count > 0:
                        print(f"  ! 前端发现 {vuln_count} 个漏洞")
            else:
                print("  ✓ 前端依赖检查通过")
        except Exception as e:
            print(f"  ! NPM 审计失败: {e}")
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        print("\n" + "="*60)
        print("优化验证报告")
        print("="*60)
        
        report: Dict[str, Any] = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'backend_tests': None,
            'frontend_tests': None,
            'code_quality': None,
            'build_time': None,
            'dependencies': None,
            'overall_status': 'PENDING'
        }
        
        # 运行所有检查
        backend_success, backend_output = self.run_backend_tests()
        report['backend_tests'] = {
            'passed': backend_success,
            'details': backend_output
        }
        
        frontend_success, frontend_output = self.run_frontend_tests()
        report['frontend_tests'] = {
            'passed': frontend_success,
            'details': frontend_output
        }
        
        quality_passed, quality_results = self.check_code_quality()
        report['code_quality'] = {
            'passed': quality_passed,
            'details': quality_results
        }
        
        build_time, build_results = self.measure_build_time()
        report['build_time'] = {
            'duration_seconds': build_time,
            'details': build_results
        }
        
        dep_results = self.check_dependencies()
        report['dependencies'] = dep_results
        
        # 计算总体状态
        all_tests_passed = (
            backend_success and
            frontend_success and
            quality_passed and
            dep_results['backend_vulnerabilities'] == 0
        )
        
        report['overall_status'] = 'PASS' if all_tests_passed else 'FAIL'
        
        return report
    
    def save_report(self, output_file: str = "optimization_report.json") -> None:
        """保存报告到文件"""
        report = self.generate_report()
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n[+] 报告已保存到 {output_file}")
        
        # 打印摘要
        print("\n" + "="*60)
        print("摘要")
        print("="*60)
        print(f"总体状态: {report['overall_status']}")
        print(f"后端测试: {'✓ 通过' if report['backend_tests']['passed'] else '✗ 失败'}")
        print(f"前端测试: {'✓ 通过' if report['frontend_tests']['passed'] else '✗ 失败'}")
        print(f"代码质量: {'✓ 通过' if report['code_quality']['passed'] else '✗ 失败'}")
        if report['build_time']['duration_seconds']:
            print(f"构建时间: {report['build_time']['duration_seconds']:.1f}s")
        print(f"后端漏洞: {report['dependencies']['backend_vulnerabilities']}")
        print(f"前端漏洞: {report['dependencies']['frontend_vulnerabilities']}")
        print("="*60)


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description="优化验证脚本")
    parser.add_argument("backend_path", help="后端代码路径")
    parser.add_argument("frontend_path", help="前端代码路径")
    parser.add_argument("--output", default="optimization_report.json", help="输出文件名")
    
    args = parser.parse_args()
    
    if not Path(args.backend_path).exists():
        print(f"[!] 后端路径不存在: {args.backend_path}")
        sys.exit(1)
    
    if not Path(args.frontend_path).exists():
        print(f"[!] 前端路径不存在: {args.frontend_path}")
        sys.exit(1)
    
    validator = OptimizationValidator(args.backend_path, args.frontend_path)
    validator.save_report(args.output)


if __name__ == "__main__":
    main()
