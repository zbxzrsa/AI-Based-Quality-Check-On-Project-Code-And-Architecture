#!/usr/bin/env python3
"""
Generate Requirements with pip-compile

This script uses pip-tools to generate a requirements.txt file with hashed dependencies
for reproducible builds and security auditing.

Usage:
    python scripts/generate_requirements.py [--input requirements.in] [--output requirements.txt]

Requirements:
    - pip-tools installed (pip install pip-tools)
    - Python 3.6+
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, cwd=None):
    """
    Run a shell command and return the result.
    
    Args:
        command (str): Command to run
        cwd (str): Working directory
        
    Returns:
        tuple: (success: bool, output: str)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"


def install_pip_tools():
    """Install pip-tools if not already installed."""
    print("📦 Checking for pip-tools...")
    
    success, output = run_command("pip show pip-tools")
    if success:
        print("✅ pip-tools is already installed")
        return True
    
    print("📥 Installing pip-tools...")
    success, output = run_command("pip install pip-tools")
    if success:
        print("✅ pip-tools installed successfully")
        return True
    else:
        print(f"❌ Failed to install pip-tools: {output}")
        return False


def create_requirements_in(backend_dir):
    """
    Create a requirements.in file if it doesn't exist.
    
    Args:
        backend_dir (Path): Backend directory path
    """
    requirements_in = backend_dir / "requirements.in"
    
    if requirements_in.exists():
        print(f"📝 Using existing requirements.in: {requirements_in}")
        return
    
    # Create requirements.in from current requirements.txt
    requirements_txt = backend_dir / "requirements.txt"
    if requirements_txt.exists():
        print("📝 Creating requirements.in from requirements.txt...")
        
        # Extract package names and versions
        with open(requirements_txt, 'r') as f:
            lines = f.readlines()
        
        with open(requirements_in, 'w') as f:
            f.write("# Generated requirements.in for pip-compile\n")
            f.write("# This file contains the base dependencies without hashes\n")
            f.write("# Run 'pip-compile' to generate requirements.txt with hashes\n\n")
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Extract package name (before == or >= or <= etc.)
                    if '==' in line:
                        package = line.split('==')[0]
                    elif '>=' in line:
                        package = line.split('>=')[0]
                    elif '<=' in line:
                        package = line.split('<=')[0]
                    elif '>' in line:
                        package = line.split('>')[0]
                    elif '<' in line:
                        package = line.split('<')[0]
                    else:
                        package = line
                    
                    f.write(f"{package}\n")
        
        print(f"✅ Created requirements.in: {requirements_in}")
    else:
        print("❌ No requirements.txt found to create requirements.in from")
        return False
    
    return True


def generate_requirements_txt(backend_dir, output_file=None):
    """
    Generate requirements.txt with hashes using pip-compile.
    
    Args:
        backend_dir (Path): Backend directory path
        output_file (str): Output file name (default: requirements.txt)
    """
    if not output_file:
        output_file = "requirements.txt"
    
    requirements_in = backend_dir / "requirements.in"
    output_path = backend_dir / output_file
    
    print(f"🔄 Generating {output_file} with pip-compile...")
    
    # Run pip-compile
    command = f"pip-compile --output-file={output_file} requirements.in"
    success, output = run_command(command, cwd=backend_dir)
    
    if success:
        print(f"✅ Generated {output_file} successfully")
        print(f"📁 Output file: {output_path}")
        
        # Show summary
        if output_path.exists():
            with open(output_path, 'r') as f:
                lines = f.readlines()
            
            # Count packages
            package_lines = [line for line in lines if line.strip() and not line.startswith('#') and not line.startswith('-')]
            print(f"📦 Total packages: {len(package_lines)}")
            
            # Show first few packages
            print("📋 First 10 packages:")
            for i, line in enumerate(package_lines[:10]):
                print(f"   {i+1}. {line.strip()}")
            
            if len(package_lines) > 10:
                print(f"   ... and {len(package_lines) - 10} more")
        
        return True
    else:
        print(f"❌ Failed to generate requirements.txt: {output}")
        return False


def validate_requirements(backend_dir, requirements_file="requirements.txt"):
    """
    Validate the generated requirements file.
    
    Args:
        backend_dir (Path): Backend directory path
        requirements_file (str): Requirements file to validate
    """
    requirements_path = backend_dir / requirements_file
    
    if not requirements_path.exists():
        print(f"❌ Requirements file not found: {requirements_path}")
        return False
    
    print(f"🔍 Validating {requirements_file}...")
    
    # Check for hashes
    with open(requirements_path, 'r') as f:
        content = f.read()
    
    if '--hash=' in content:
        print("✅ Requirements file contains hashes")
    else:
        print("⚠️  Warning: Requirements file may not contain hashes")
    
    # Check for comments
    lines = content.split('\n')
    comment_lines = [line for line in lines if line.strip().startswith('#')]
    print(f"📝 Found {len(comment_lines)} comment lines")
    
    # Check for packages
    package_lines = [line for line in lines if line.strip() and not line.startswith('#') and not line.startswith('-')]
    print(f"📦 Found {len(package_lines)} packages")
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate requirements.txt with hashed dependencies using pip-compile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_requirements.py
  python scripts/generate_requirements.py --input requirements.in --output requirements-prod.txt
        """
    )
    
    parser.add_argument(
        '--input',
        default='requirements.in',
        help='Input file for pip-compile (default: requirements.in)'
    )
    
    parser.add_argument(
        '--output',
        default='requirements.txt',
        help='Output file name (default: requirements.txt)'
    )
    
    parser.add_argument(
        '--backend-dir',
        default='backend',
        help='Backend directory path (default: backend)'
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    backend_dir = Path(args.backend_dir).resolve()
    
    if not backend_dir.exists():
        print(f"❌ Backend directory not found: {backend_dir}")
        sys.exit(1)
    
    print(f"📁 Backend directory: {backend_dir}")
    print()
    
    # Install pip-tools
    if not install_pip_tools():
        sys.exit(1)
    
    print()
    
    # Create requirements.in if needed
    if not create_requirements_in(backend_dir):
        sys.exit(1)
    
    print()
    
    # Generate requirements.txt
    if not generate_requirements_txt(backend_dir, args.output):
        sys.exit(1)
    
    print()
    
    # Validate the generated file
    if not validate_requirements(backend_dir, args.output):
        sys.exit(1)
    
    print()
    print("🎉 Requirements generation completed successfully!")
    print(f"📄 Generated file: {backend_dir / args.output}")


if __name__ == '__main__':
    main()
