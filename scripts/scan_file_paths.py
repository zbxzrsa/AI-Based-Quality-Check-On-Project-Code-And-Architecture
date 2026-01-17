#!/usr/bin/env python3
"""
File Path Compliance Scanner

This script recursively scans the project directory to identify files or folders
containing non-ASCII characters (like Chinese characters) or spaces.

Usage:
    python scripts/scan_file_paths.py [--fix] [--output-format json|text]

Requirements:
    - Python 3.6+
    - No external dependencies (uses only standard library)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class PathComplianceScanner:
    """Scanner for file path compliance issues."""
    
    def __init__(self, root_path: str = "."):
        """
        Initialize the scanner.
        
        Args:
            root_path (str): Root directory to scan (default: current directory)
        """
        self.root_path = Path(root_path).resolve()
        self.issues = []
        
    def is_ascii(self, text: str) -> bool:
        """
        Check if a string contains only ASCII characters.
        
        Args:
            text (str): String to check
            
        Returns:
            bool: True if string contains only ASCII characters
        """
        try:
            text.encode('ascii')
            return True
        except UnicodeEncodeError:
            return False
    
    def contains_spaces(self, path: Path) -> bool:
        """
        Check if a path contains spaces.
        
        Args:
            path (Path): Path to check
            
        Returns:
            bool: True if path contains spaces
        """
        return ' ' in str(path)
    
    def should_skip_directory(self, path: Path) -> bool:
        """
        Determine if a directory should be skipped during scanning.
        
        Args:
            path (Path): Directory path to check
            
        Returns:
            bool: True if directory should be skipped
        """
        skip_dirs = {
            '.git', '.vscode', 'node_modules', '__pycache__', 
            '.pytest_cache', '.venv', 'venv', 'env', '.next',
            'dist', 'build', '.nuxt', '.svelte-kit', '.astro'
        }
        
        # Check if any part of the path contains skip directories
        path_parts = path.parts
        for part in path_parts:
            if part in skip_dirs:
                return True
        
        # Skip hidden files/directories (starting with .)
        if any(part.startswith('.') for part in path_parts):
            return True
            
        return False
    
    def scan_directory(self, directory: Path) -> None:
        """
        Recursively scan a directory for path compliance issues.
        
        Args:
            directory (Path): Directory to scan
        """
        try:
            # Skip directories that should be ignored
            if self.should_skip_directory(directory):
                return
                
            # List all items in the directory
            try:
                items = list(directory.iterdir())
            except (PermissionError, OSError):
                # Skip directories that can't be read
                return
                
            for item in items:
                try:
                    # Check for non-ASCII characters
                    if not self.is_ascii(str(item)):
                        self.issues.append({
                            'path': str(item),
                            'relative_path': str(item.relative_to(self.root_path)),
                            'name': item.name,
                            'type': 'directory' if item.is_dir() else 'file',
                            'issue_type': 'non_ascii',
                            'description': 'Contains non-ASCII characters'
                        })
                    
                    # Check for spaces
                    if self.contains_spaces(item):
                        self.issues.append({
                            'path': str(item),
                            'relative_path': str(item.relative_to(self.root_path)),
                            'name': item.name,
                            'type': 'directory' if item.is_dir() else 'file',
                            'issue_type': 'spaces',
                            'description': 'Contains spaces in name'
                        })
                    
                    # Recursively scan subdirectories
                    if item.is_dir():
                        self.scan_directory(item)
                        
                except (PermissionError, OSError):
                    # Skip files/directories that can't be accessed
                    continue
                    
        except (PermissionError, OSError):
            # Skip directories that can't be read
            return
    
    def scan(self) -> List[Dict]:
        """
        Perform the full scan of the project directory.
        
        Returns:
            List[Dict]: List of compliance issues found
        """
        print(f"🔍 Scanning directory: {self.root_path}")
        print("📁 This may take a moment for large projects...")
        print()
        
        self.scan_directory(self.root_path)
        return self.issues
    
    def generate_git_mv_commands(self) -> List[str]:
        """
        Generate git mv commands to fix path issues while preserving history.
        
        Returns:
            List[str]: List of git mv commands
        """
        commands = []
        
        for issue in self.issues:
            if issue['issue_type'] == 'non_ascii' or issue['issue_type'] == 'spaces':
                old_path = Path(issue['path'])
                new_name = self.sanitize_name(old_path.name)
                new_path = old_path.parent / new_name
                
                # Generate git mv command
                git_mv_cmd = f"git mv \"{old_path}\" \"{new_path}\""
                commands.append(git_mv_cmd)
        
        return commands
    
    def sanitize_name(self, name: str) -> str:
        """
        Sanitize a filename by removing non-ASCII characters and spaces.
        
        Args:
            name (str): Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Remove non-ASCII characters
        ascii_name = ''.join(c for c in name if ord(c) < 128)
        
        # Replace spaces with underscores
        sanitized = ascii_name.replace(' ', '_')
        
        # Remove multiple consecutive underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        
        # Ensure we have a valid filename
        if not sanitized:
            sanitized = 'file'
        
        # Preserve file extension if it exists
        if '.' in name and name.rfind('.') > name.rfind('/'):
            ext = name[name.rfind('.'):]
            if self.is_ascii(ext):
                sanitized += ext
        
        return sanitized
    
    def print_report(self, output_format: str = 'text') -> None:
        """
        Print the compliance report.
        
        Args:
            output_format (str): Output format ('text' or 'json')
        """
        if output_format == 'json':
            self.print_json_report()
        else:
            self.print_text_report()
    
    def print_text_report(self) -> None:
        """Print the compliance report in text format."""
        if not self.issues:
            print("✅ All file paths are compliant!")
            print("🎉 No non-ASCII characters or spaces found in file paths.")
            print()
            print("This ensures compatibility with npm installations and CI/CD pipelines.")
            return
        
        print(f"❌ Found {len(self.issues)} path compliance issue(s):")
        print()
        
        # Group issues by type
        non_ascii_issues = [i for i in self.issues if i['issue_type'] == 'non_ascii']
        space_issues = [i for i in self.issues if i['issue_type'] == 'spaces']
        
        if non_ascii_issues:
            print("🔤 Non-ASCII Characters:")
            for i, issue in enumerate(non_ascii_issues, 1):
                print(f"  {i}. {issue['type'].title()}: {issue['relative_path']}")
                print(f"     Name: {issue['name']}")
                print()
        
        if space_issues:
            print("␣ Spaces in Names:")
            for i, issue in enumerate(space_issues, 1):
                print(f"  {i}. {issue['type'].title()}: {issue['relative_path']}")
                print(f"     Name: {issue['name']}")
                print()
        
        print("🔧 Recommended Actions:")
        print("  1. Rename files/directories to use only ASCII characters")
        print("  2. Replace spaces with underscores or hyphens")
        print("  3. Use git mv to preserve history when renaming")
        print("  4. Consider moving the project to a path without special characters")
        print()
        
        # Show git mv commands
        commands = self.generate_git_mv_commands()
        if commands:
            print("📝 Git Commands to Fix Issues (preserves history):")
            for cmd in commands:
                print(f"  {cmd}")
            print()
        
        print("⚠️  Warning: These issues may cause npm installation failures")
        print("   and CI/CD pipeline problems, especially on Windows systems.")
    
    def print_json_report(self) -> None:
        """Print the compliance report in JSON format."""
        report = {
            'scan_path': str(self.root_path),
            'total_issues': len(self.issues),
            'issues': self.issues,
            'git_mv_commands': self.generate_git_mv_commands(),
            'summary': {
                'non_ascii_issues': len([i for i in self.issues if i['issue_type'] == 'non_ascii']),
                'space_issues': len([i for i in self.issues if i['issue_type'] == 'spaces']),
                'compliant': len(self.issues) == 0
            }
        }
        
        print(json.dumps(report, indent=2))


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Scan project directory for file path compliance issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/scan_file_paths.py
  python scripts/scan_file_paths.py --output-format json
  python scripts/scan_file_paths.py /path/to/project
        """
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Root directory to scan (default: current directory)'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    args = parser.parse_args()
    
    # Initialize scanner
    scanner = PathComplianceScanner(args.path)
    
    # Perform scan
    issues = scanner.scan()
    
    # Print report
    scanner.print_report(args.output_format)
    
    # Exit with appropriate code
    sys.exit(0 if len(issues) == 0 else 1)


if __name__ == '__main__':
    main()
