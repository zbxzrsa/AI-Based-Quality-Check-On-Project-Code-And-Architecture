"""
Git diff parser utilities
Parse git diff format and extract changes
"""
import re
from typing import List, Dict, Any, Tuple


class DiffParser:
    """
    Parse git diff format and extract change information
    """
    
    @staticmethod
    def parse_diff(diff_text: str) -> List[Dict[str, Any]]:
        """
        Parse git diff text into structured format
        
        Args:
            diff_text: Git diff text
            
        Returns:
            List of file changes with line-level details
        """
        if not diff_text:
            return []
        
        files = []
        current_file = None
        current_hunk = None
        
        lines = diff_text.split('\n')
        
        for line in lines:
            # New file header
            if line.startswith('diff --git'):
                if current_file:
                    files.append(current_file)
                
                # Extract filenames
                match = re.search(r'diff --git a/(.*?) b/(.*?)$', line)
                if match:
                    current_file = {
                        'old_path': match.group(1),
                        'new_path': match.group(2),
                        'hunks': [],
                        'additions': 0,
                        'deletions': 0,
                        'status': 'modified'
                    }
            
            # File status
            elif line.startswith('new file'):
                if current_file:
                    current_file['status'] = 'added'
            
            elif line.startswith('deleted file'):
                if current_file:
                    current_file['status'] = 'deleted'
            
            elif line.startswith('rename from'):
                if current_file:
                    current_file['status'] = 'renamed'
            
            # Hunk header
            elif line.startswith('@@'):
                match = re.search(r'@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)', line)
                if match and current_file:
                    current_hunk = {
                        'old_start': int(match.group(1)),
                        'old_lines': int(match.group(2)) if match.group(2) else 1,
                        'new_start': int(match.group(3)),
                        'new_lines': int(match.group(4)) if match.group(4) else 1,
                        'context': match.group(5).strip(),
                        'changes': []
                    }
                    current_file['hunks'].append(current_hunk)
            
            # Hunk content
            elif current_hunk is not None:
                if line.startswith('+') and not line.startswith('+++'):
                    current_hunk['changes'].append({
                        'type': 'addition',
                        'line': line[1:],
                        'line_number': current_hunk['new_start'] + len([c for c in current_hunk['changes'] if c['type'] in ['addition', 'context']])
                    })
                    current_file['additions'] += 1
                
                elif line.startswith('-') and not line.startswith('---'):
                    current_hunk['changes'].append({
                        'type': 'deletion',
                        'line': line[1:],
                        'line_number': current_hunk['old_start'] + len([c for c in current_hunk['changes'] if c['type'] in ['deletion', 'context']])
                    })
                    current_file['deletions'] += 1
                
                elif line.startswith(' '):
                    current_hunk['changes'].append({
                        'type': 'context',
                        'line': line[1:]
                    })
        
        # Add last file
        if current_file:
            files.append(current_file)
        
        return files
    
    @staticmethod
    def get_changed_lines(diff_text: str) -> Dict[str, List[int]]:
        """
        Extract line numbers that were changed
        
        Args:
            diff_text: Git diff text
            
        Returns:
            Dictionary mapping file paths to list of changed line numbers
        """
        files = DiffParser.parse_diff(diff_text)
        changed_lines = {}
        
        for file in files:
            file_path = file['new_path']
            lines = []
            
            for hunk in file['hunks']:
                for change in hunk['changes']:
                    if change['type'] in ['addition', 'deletion']:
                        if 'line_number' in change:
                            lines.append(change['line_number'])
            
            if lines:
                changed_lines[file_path] = sorted(set(lines))
        
        return changed_lines
    
    @staticmethod
    def calculate_change_stats(diff_text: str) -> Dict[str, int]:
        """
        Calculate overall change statistics
        
        Args:
            diff_text: Git diff text
            
        Returns:
            Dictionary with change statistics
        """
        files = DiffParser.parse_diff(diff_text)
        
        stats = {
            'files_changed': len(files),
            'additions': sum(f['additions'] for f in files),
            'deletions': sum(f['deletions'] for f in files),
            'total_changes': 0
        }
        
        stats['total_changes'] = stats['additions'] + stats['deletions']
        
        return stats
    
    @staticmethod
    def filter_changes_by_extension(
        diff_text: str,
        extensions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter changes by file extension
        
        Args:
            diff_text: Git diff text
            extensions: List of extensions to include (e.g., ['.py', '.js'])
            
        Returns:
            Filtered list of file changes
        """
        files = DiffParser.parse_diff(diff_text)
        filtered = []
        
        for file in files:
            file_ext = '.' + file['new_path'].split('.')[-1] if '.' in file['new_path'] else ''
            if file_ext in extensions:
                filtered.append(file)
        
        return filtered
    
    @staticmethod
    def extract_added_code(diff_text: str) -> Dict[str, List[str]]:
        """
        Extract only the added code lines
        
        Args:
            diff_text: Git diff text
            
        Returns:
            Dictionary mapping file paths to lists of added lines
        """
        files = DiffParser.parse_diff(diff_text)
        added_code = {}
        
        for file in files:
            file_path = file['new_path']
            added_lines = []
            
            for hunk in file['hunks']:
                for change in hunk['changes']:
                    if change['type'] == 'addition':
                        added_lines.append(change['line'])
            
            if added_lines:
                added_code[file_path] = added_lines
        
        return added_code
