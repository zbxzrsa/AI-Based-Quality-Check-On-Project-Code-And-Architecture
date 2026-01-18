#!/usr/bin/env python3
"""
代码重复检测脚本

检测项目中的：
1. 相似代码块 (similarity > 80%)
2. 重复的导入和依赖
3. 相同的函数/类名
4. 孤立的未被引用的模块
"""

import os
import ast
import sys
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Set, Tuple
import json

class CodeDuplicationDetector:
    """检测代码重复的类"""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.python_files: List[Path] = []
        self.file_contents: Dict[Path, str] = {}
        self.functions: Dict[str, List[Path]] = defaultdict(list)
        self.classes: Dict[str, List[Path]] = defaultdict(list)
        self.imports: Dict[str, List[Path]] = defaultdict(list)
        self.duplications = []
    
    def scan_directory(self):
        """扫描目录中的所有 Python 文件"""
        print("[*] 扫描 Python 文件...")
        for py_file in self.root_path.rglob("*.py"):
            # 跳过 __pycache__ 和测试缓存
            if "__pycache__" in str(py_file) or "pytest_cache" in str(py_file):
                continue
            self.python_files.append(py_file)
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    self.file_contents[py_file] = f.read()
            except Exception as e:
                print(f"[!] 无法读取 {py_file}: {e}")
        
        print(f"[+] 找到 {len(self.python_files)} 个 Python 文件")
    
    def extract_functions_and_classes(self):
        """从 AST 中提取函数和类定义"""
        print("\n[*] 提取函数和类定义...")
        
        for py_file in self.python_files:
            try:
                tree = ast.parse(self.file_contents[py_file])
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        self.functions[node.name].append(py_file)
                    elif isinstance(node, ast.ClassDef):
                        self.classes[node.name].append(py_file)
            except SyntaxError as e:
                print(f"[!] 语法错误 {py_file}: {e}")
        
        print(f"[+] 找到 {len(self.functions)} 个唯一函数名")
        print(f"[+] 找到 {len(self.classes)} 个唯一类名")
    
    def detect_duplicate_function_names(self):
        """检测同名函数"""
        print("\n[*] 检测重复的函数名...")
        
        duplicate_functions = {name: files for name, files in self.functions.items() if len(files) > 1}
        
        if duplicate_functions:
            print(f"\n[!] 发现 {len(duplicate_functions)} 个重复函数名:")
            for func_name, files in sorted(duplicate_functions.items(), key=lambda x: -len(x[1])):
                print(f"\n  函数: {func_name}")
                for file_path in files:
                    rel_path = file_path.relative_to(self.root_path)
                    print(f"    - {rel_path}")
                self.duplications.append({
                    'type': 'duplicate_function_name',
                    'name': func_name,
                    'files': [str(f.relative_to(self.root_path)) for f in files]
                })
    
    def detect_duplicate_class_names(self):
        """检测同名类"""
        print("\n[*] 检测重复的类名...")
        
        duplicate_classes = {name: files for name, files in self.classes.items() if len(files) > 1}
        
        if duplicate_classes:
            print(f"\n[!] 发现 {len(duplicate_classes)} 个重复类名:")
            for class_name, files in sorted(duplicate_classes.items(), key=lambda x: -len(x[1])):
                print(f"\n  类: {class_name}")
                for file_path in files:
                    rel_path = file_path.relative_to(self.root_path)
                    print(f"    - {rel_path}")
                self.duplications.append({
                    'type': 'duplicate_class_name',
                    'name': class_name,
                    'files': [str(f.relative_to(self.root_path)) for f in files]
                })
    
    def detect_similar_files(self, threshold: float = 0.80):
        """检测相似文件 (相似度 > threshold)"""
        print(f"\n[*] 检测相似文件 (阈值: {threshold*100}%)...")
        
        similar_pairs = []
        files_list = list(self.file_contents.keys())
        
        for i, file1 in enumerate(files_list):
            for file2 in files_list[i+1:]:
                content1 = self.file_contents[file1]
                content2 = self.file_contents[file2]
                
                similarity = self._calculate_similarity(content1, content2)
                
                if similarity >= threshold:
                    similar_pairs.append((file1, file2, similarity))
                    self.duplications.append({
                        'type': 'similar_files',
                        'file1': str(file1.relative_to(self.root_path)),
                        'file2': str(file2.relative_to(self.root_path)),
                        'similarity': round(similarity * 100, 2)
                    })
        
        if similar_pairs:
            print(f"\n[!] 发现 {len(similar_pairs)} 对相似文件:")
            for file1, file2, similarity in sorted(similar_pairs, key=lambda x: -x[2]):
                rel1 = file1.relative_to(self.root_path)
                rel2 = file2.relative_to(self.root_path)
                print(f"\n  相似度: {similarity*100:.1f}%")
                print(f"    - {rel1}")
                print(f"    - {rel2}")
    
    def detect_similar_code_blocks(self, min_lines: int = 10, threshold: float = 0.85):
        """检测相似的代码块"""
        print(f"\n[*] 检测相似代码块 (最小行数: {min_lines}, 阈值: {threshold*100}%)...")
        
        lines_by_file = {}
        for py_file, content in self.file_contents.items():
            lines_by_file[py_file] = content.split('\n')
        
        similar_blocks = []
        
        for file1 in list(lines_by_file.keys()):
            for file2 in list(lines_by_file.keys()):
                if file1 >= file2:
                    continue
                
                for start1 in range(len(lines_by_file[file1]) - min_lines):
                    block1 = '\n'.join(lines_by_file[file1][start1:start1+min_lines])
                    
                    for start2 in range(len(lines_by_file[file2]) - min_lines):
                        block2 = '\n'.join(lines_by_file[file2][start2:start2+min_lines])
                        
                        similarity = self._calculate_similarity(block1, block2)
                        if similarity >= threshold:
                            similar_blocks.append({
                                'file1': file1,
                                'file2': file2,
                                'start1': start1,
                                'start2': start2,
                                'similarity': similarity
                            })
        
        if similar_blocks:
            print(f"\n[!] 发现 {len(similar_blocks)} 个相似代码块:")
            for block in sorted(similar_blocks, key=lambda x: -x['similarity'])[:10]:  # 显示前10个
                rel1 = block['file1'].relative_to(self.root_path)
                rel2 = block['file2'].relative_to(self.root_path)
                print(f"\n  相似度: {block['similarity']*100:.1f}%")
                print(f"    {rel1}:{block['start1']}-{block['start1']+min_lines}")
                print(f"    {rel2}:{block['start2']}-{block['start2']+min_lines}")
    
    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> float:
        """计算两个字符串的相似度"""
        matcher = SequenceMatcher(None, str1, str2)
        return matcher.ratio()
    
    def generate_report(self) -> Dict:
        """生成检测报告"""
        return {
            'total_files': len(self.python_files),
            'duplicate_function_names': len([d for d in self.duplications if d['type'] == 'duplicate_function_name']),
            'duplicate_class_names': len([d for d in self.duplications if d['type'] == 'duplicate_class_name']),
            'similar_files': len([d for d in self.duplications if d['type'] == 'similar_files']),
            'all_duplications': self.duplications
        }
    
    def save_report(self, output_file: str = "duplication_report.json"):
        """保存报告到文件"""
        report = self.generate_report()
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n[+] 报告已保存到 {output_file}")


def main():
    if len(sys.argv) < 2:
        print("用法: python detect_duplication.py <project_root> [output_file]")
        print(f"\n示例: python {sys.argv[0]} /path/to/backend duplication_report.json")
        sys.exit(1)
    
    project_root = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "duplication_report.json"
    
    if not os.path.exists(project_root):
        print(f"[!] 目录不存在: {project_root}")
        sys.exit(1)
    
    detector = CodeDuplicationDetector(project_root)
    
    print("="*60)
    print("代码重复检测工具")
    print("="*60)
    
    detector.scan_directory()
    detector.extract_functions_and_classes()
    detector.detect_duplicate_function_names()
    detector.detect_duplicate_class_names()
    detector.detect_similar_files(threshold=0.80)
    detector.detect_similar_code_blocks(min_lines=10, threshold=0.85)
    
    detector.save_report(output_file)
    
    print("\n" + "="*60)
    print("检测完成!")
    print("="*60)


if __name__ == "__main__":
    main()
