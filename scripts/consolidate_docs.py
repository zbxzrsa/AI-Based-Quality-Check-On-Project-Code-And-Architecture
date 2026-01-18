import os
import shutil
from pathlib import Path

def ensure_dir(directory):
    """Ensure directory exists, create if it doesn't."""
    os.makedirs(directory, exist_ok=True)

def read_file(filepath):
    """Read file content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""

def write_file(filepath, content):
    """Write content to file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing to {filepath}: {e}")
        return False

def main():
    base_dir = Path(__file__).parent.parent
    docs_dir = base_dir / 'docs'
    
    # Create docs directory if it doesn't exist
    ensure_dir(docs_dir)
    
    # 1. Consolidate Phase 3 documents
    phase3_files = [
        'PHASE_3_FINAL_DELIVERY.md',
        'PHASE_3_FINAL_CHECKLIST.md',
        'PHASE_3_FILE_INDEX.md',
        'PHASE_3_COMPLETION_SUMMARY.md',
        'PHASE_3_OPERATIONS_GUIDE.md',
        'PHASE_3_IMPLEMENTATION_CHECKLIST.md'
    ]
    
    phase3_content = "# Phase 3 Implementation\n\n"
    for file in phase3_files:
        file_path = base_dir / file
        if file_path.exists():
            content = read_file(file_path)
            phase3_content += f"## {file}\n\n{content}\n\n"
    
    phase3_output = docs_dir / 'PHASE_3_IMPLEMENTATION.md'
    write_file(phase3_output, phase3_content)
    print(f"Consolidated Phase 3 documents into {phase3_output}")
    
    # 2. Consolidate Security documents
    security_files = [
        'SECURITY_FIXES_SUMMARY.md',
        'SECURITY.md',
        'docs/SECURITY_COMPLIANCE_IMPLEMENTATION.md'
    ]
    
    security_content = "# Security Documentation\n\n"
    for file in security_files:
        file_path = base_dir / file
        if file_path.exists():
            content = read_file(file_path)
            security_content += f"## {file}\n\n{content}\n\n"
    
    security_output = docs_dir / 'SECURITY.md'
    write_file(security_output, security_content)
    print(f"Consolidated security documents into {security_output}")
    
    # 3. Handle Quick References
    quick_ref_content = read_file(base_dir / 'QUICK_REFERENCE.md') or \
                      read_file(base_dir / 'PHASE_3_QUICK_REFERENCE.md') or \
                      "# Quick Reference\n\n*No quick reference content found.*\n"
    
    quick_ref_output = docs_dir / 'QUICK_REFERENCE.md'
    write_file(quick_ref_output, quick_ref_content)
    print(f"Created quick reference at {quick_ref_output}")
    
    # 4. Handle Implementation Report
    impl_report_content = read_file(base_dir / 'IMPLEMENTATION_REPORT.md') or ""
    phase3_summary = read_file(base_dir / 'PHASE_3_COMPLETION_SUMMARY.md') or ""
    
    final_impl_report = f"# Implementation Report\n\n{impl_report_content}\n\n## Phase 3 Summary\n\n{phase3_summary}"
    
    impl_report_output = docs_dir / 'IMPLEMENTATION_REPORT.md'
    write_file(impl_report_output, final_impl_report)
    print(f"Created implementation report at {impl_report_output}")
    
    # 5. Clean up old files
    print("\nCleaning up old files...")
    files_to_remove = phase3_files + ['QUICK_REFERENCE.md', 'PHASE_3_QUICK_REFERENCE.md', 'IMPLEMENTATION_REPORT.md']
    
    for file in files_to_remove:
        file_path = base_dir / file
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"✓ Removed {file}")
            except Exception as e:
                print(f"! Failed to remove {file}: {e}")
    
    print("\nDocumentation consolidation complete!")
    print("Please review the files in the 'docs' directory.")
    print("If everything looks good, uncomment the cleanup section in the script to remove the old files.")

if __name__ == "__main__":
    main()
