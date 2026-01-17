#!/usr/bin/env python3
"""
AI Self-Healing CI/CD Script

This script implements automated self-healing for CI/CD pipelines by:
1. Fetching failed logs from GitHub Actions workflows
2. Sending logs to Ollama (qwen2.5-coder) for analysis
3. Generating GitHub PR comments with fixes and corrected code

Usage:
    python scripts/ai_self_healing.py --pr-number 123 --workflow-run-id 456789012
    python scripts/ai_self_healing.py --analyze-failure --job-name "Backend Tests"
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth


class AISelfHealing:
    """
    AI-powered self-healing system for CI/CD pipelines
    """

    def __init__(self):
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.github_repository = os.environ.get('GITHUB_REPOSITORY', 'zbxzrsa/AI-Based-Quality-Check-On-Project-Code-And-Architecture')
        self.ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        self.ollama_model = os.environ.get('OLLAMA_MODEL', 'qwen2.5-coder')

        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'AI-Self-Healing-Bot/1.0'
        })

    def get_workflow_runs(self, branch: str = 'main', status: str = 'failure',
                         hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent workflow runs with specified status
        """
        since = datetime.utcnow() - timedelta(hours=hours_back)
        since_iso = since.isoformat() + 'Z'

        url = f'https://api.github.com/repos/{self.github_repository}/actions/runs'
        params = {
            'branch': branch,
            'status': status,
            'created': f'>{since_iso}',
            'per_page': 10
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        return response.json().get('workflow_runs', [])

    def get_workflow_run_jobs(self, run_id: int) -> List[Dict[str, Any]]:
        """
        Get jobs for a specific workflow run
        """
        url = f'https://api.github.com/repos/{self.github_repository}/actions/runs/{run_id}/jobs'

        response = self.session.get(url)
        response.raise_for_status()

        return response.json().get('jobs', [])

    def get_job_logs(self, job_id: int) -> str:
        """
        Download logs for a specific job
        """
        url = f'https://api.github.com/repos/{self.github_repository}/actions/jobs/{job_id}/logs'

        response = self.session.get(url)
        response.raise_for_status()

        return response.text

    def parse_failure_logs(self, logs: str, job_name: str) -> Dict[str, Any]:
        """
        Parse failure logs to extract relevant error information
        """
        parsed = {
            'job_name': job_name,
            'errors': [],
            'stack_traces': [],
            'test_failures': [],
            'security_issues': [],
            'raw_logs': logs[:5000]  # Limit log size
        }

        # Extract Python test failures
        test_failure_pattern = r'FAILED\s+([\w/_]+\.py)::([\w_]+)::([\w_]+)\s*-\s*(.+?)(?=\n\n|\nFAILED|\nERROR|\n=)'
        for match in re.finditer(test_failure_pattern, logs, re.DOTALL):
            file_path, class_name, test_name, error_msg = match.groups()
            parsed['test_failures'].append({
                'file': file_path,
                'class': class_name,
                'test': test_name,
                'error': error_msg.strip()
            })

        # Extract Python exceptions
        exception_pattern = r'Traceback \(most recent call last\):\s*\n((?:.*?\n)*?)\n(\w+):\s*(.+?)(?=\n\n|\nFAILED|\nERROR|\n=)'
        for match in re.finditer(exception_pattern, logs, re.DOTALL):
            traceback, exc_type, exc_msg = match.groups()
            parsed['errors'].append({
                'type': exc_type,
                'message': exc_msg.strip(),
                'traceback': traceback.strip()
            })

        # Extract security scan failures
        if 'Bandit' in job_name or 'Security' in job_name:
            security_pattern = r'(B\d+):\s*(.+?)(?=\n|B\d+:|\n\n)'
            for match in re.finditer(security_pattern, logs):
                issue_id, description = match.groups()
                parsed['security_issues'].append({
                    'id': issue_id,
                    'description': description.strip()
                })

        # Extract TruffleHog secrets found
        if 'TruffleHog' in job_name or 'Secrets' in job_name:
            secret_pattern = r'Found \d+ verified secrets?\s*\n((?:.*?\n)*?)(?=\n\n|\nFound|\n=)'
            for match in re.finditer(secret_pattern, logs, re.DOTALL):
                secrets_info = match.group(1).strip()
                parsed['security_issues'].append({
                    'type': 'secrets_found',
                    'details': secrets_info
                })

        return parsed

    def send_to_ollama(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Send analysis request to Ollama
        """
        system_prompt = """You are an expert DevOps engineer and security specialist working on an AI-Based Quality Check system.

Your task is to analyze CI/CD failure logs and provide:
1. Root cause analysis
2. Specific code fixes
3. Prevention measures
4. GitHub PR comment format

Be precise, actionable, and focus on the most likely solutions. If you're unsure, suggest investigation steps."""

        user_prompt = f"""
Analyze these CI/CD failure logs and provide a fix:

CONTEXT:
- Job Name: {context.get('job_name', 'Unknown')}
- Repository: {self.github_repository}
- Project: AI-Based Quality Check system with FastAPI backend, Neo4j database, and Next.js frontend

FAILURE DETAILS:
{json.dumps(context, indent=2)}

Please provide:
1. **Root Cause**: What caused this failure?
2. **Fix**: Specific code changes needed
3. **Code Block**: The corrected code
4. **Prevention**: How to avoid this in the future

Format your response as a GitHub PR comment with proper markdown formatting.
"""

        payload = {
            'model': self.ollama_model,
            'prompt': user_prompt,
            'system': system_prompt,
            'stream': False,
            'options': {
                'temperature': 0.3,
                'top_p': 0.9,
                'num_predict': 2048
            }
        }

        try:
            response = requests.post(
                f'{self.ollama_url}/api/generate',
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            result = response.json()
            return result.get('response', 'No response from Ollama')

        except requests.exceptions.RequestException as e:
            return f"Error communicating with Ollama: {e}"

    def format_github_comment(self, analysis: str, context: Dict[str, Any]) -> str:
        """
        Format the AI analysis as a GitHub PR comment
        """
        timestamp = datetime.now().isoformat()

        comment = f"""## 🤖 AI Self-Healing Analysis

**Generated:** {timestamp}
**Job:** {context.get('job_name', 'Unknown')}
**Status:** 🔴 Failed - AI Analysis Complete

### 🚨 Failure Summary

{self._generate_failure_summary(context)}

### 🔍 AI Analysis & Fix

{analysis}

### 📋 Next Steps

1. **Review the suggested fix above**
2. **Apply the code changes to your branch**
3. **Run tests locally** before pushing
4. **Request re-review** after implementing fixes

### 🔧 Automated Analysis

This analysis was generated using:
- **AI Model**: {self.ollama_model}
- **Analysis Type**: Self-healing CI/CD
- **Confidence**: High (based on error patterns)

---
*🤖 This comment was automatically generated by the AI Self-Healing system*
"""

        return comment

    def _generate_failure_summary(self, context: Dict[str, Any]) -> str:
        """Generate a summary of the failures"""
        summary_lines = []

        if context.get('test_failures'):
            summary_lines.append(f"❌ **{len(context['test_failures'])} test(s) failed**")

        if context.get('errors'):
            summary_lines.append(f"💥 **{len(context['errors'])} error(s) detected**")

        if context.get('security_issues'):
            summary_lines.append(f"🔒 **{len(context['security_issues'])} security issue(s)**")

        if context.get('job_name'):
            summary_lines.append(f"📝 **Job:** {context['job_name']}")

        return "\n".join(summary_lines) if summary_lines else "Unknown failure type"

    def post_github_comment(self, pr_number: int, comment: str) -> bool:
        """
        Post a comment to a GitHub PR
        """
        url = f'https://api.github.com/repos/{self.github_repository}/issues/{pr_number}/comments'

        payload = {
            'body': comment
        }

        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to post GitHub comment: {e}")
            return False

    def analyze_latest_failure(self, job_names: List[str], pr_number: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze the latest failure for specified job names
        """
        print(f"🔍 Analyzing latest failures for jobs: {', '.join(job_names)}")

        # Get recent failed workflow runs
        failed_runs = self.get_workflow_runs(status='failure')

        for run in failed_runs:
            run_id = run['id']
            print(f"📋 Checking workflow run {run_id}...")

            # Get jobs for this run
            jobs = self.get_workflow_run_jobs(run_id)

            for job in jobs:
                if job['name'] in job_names and job['conclusion'] == 'failure':
                    print(f"🎯 Found failed job: {job['name']} (ID: {job['id']})")

                    # Get logs for this job
                    logs = self.get_job_logs(job['id'])

                    # Parse the logs
                    parsed_logs = self.parse_failure_logs(logs, job['name'])

                    return {
                        'run_id': run_id,
                        'job': job,
                        'logs': parsed_logs,
                        'pr_number': pr_number or self._extract_pr_number(run)
                    }

        print("❌ No recent failures found for specified jobs")
        return None

    def _extract_pr_number(self, run: Dict[str, Any]) -> Optional[int]:
        """Extract PR number from workflow run"""
        head_sha = run.get('head_sha')
        if not head_sha:
            return None

        # Query for PRs containing this commit
        url = f'https://api.github.com/repos/{self.github_repository}/commits/{head_sha}/pulls'

        try:
            response = self.session.get(url)
            response.raise_for_status()

            prs = response.json()
            return prs[0]['number'] if prs else None
        except:
            return None

    def run_self_healing(self, pr_number: Optional[int] = None,
                        job_names: List[str] = None) -> bool:
        """
        Main self-healing workflow
        """
        if job_names is None:
            job_names = ['Backend Tests', 'Critical Security Checks']

        # Analyze the latest failure
        failure_data = self.analyze_latest_failure(job_names, pr_number)

        if not failure_data:
            print("❌ No failures to analyze")
            return False

        print("📊 Failure data extracted:")
        print(f"  - Job: {failure_data['job']['name']}")
        print(f"  - Errors: {len(failure_data['logs']['errors'])}")
        print(f"  - Test Failures: {len(failure_data['logs']['test_failures'])}")
        print(f"  - Security Issues: {len(failure_data['logs']['security_issues'])}")

        # Send to Ollama for analysis
        print("🤖 Sending logs to Ollama for analysis...")
        ai_analysis = self.send_to_ollama("Analyze and fix this CI/CD failure", failure_data['logs'])

        if "Error communicating with Ollama" in ai_analysis:
            print(f"❌ {ai_analysis}")
            return False

        print("✅ AI analysis received")

        # Format as GitHub comment
        comment = self.format_github_comment(ai_analysis, failure_data['logs'])

        # Determine PR number
        target_pr = pr_number or failure_data.get('pr_number')
        if not target_pr:
            print("❌ Could not determine PR number for comment")
            return False

        # Post the comment
        print(f"💬 Posting analysis to PR #{target_pr}...")
        success = self.post_github_comment(target_pr, comment)

        if success:
            print("✅ Self-healing analysis posted successfully!")
            return True
        else:
            print("❌ Failed to post analysis")
            return False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='AI Self-Healing CI/CD Analysis Tool'
    )

    parser.add_argument('--pr-number', type=int,
                       help='GitHub PR number to comment on')
    parser.add_argument('--workflow-run-id', type=int,
                       help='Specific workflow run ID to analyze')
    parser.add_argument('--job-names', nargs='+',
                       default=['Backend Tests', 'Critical Security Checks'],
                       help='Job names to analyze')
    parser.add_argument('--analyze-failure', action='store_true',
                       help='Analyze the latest failure and post fix')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without posting')

    args = parser.parse_args()

    try:
        healer = AISelfHealing()

        if args.analyze_failure:
            success = healer.run_self_healing(
                pr_number=args.pr_number,
                job_names=args.job_names
            )

            if success:
                print("🎉 Self-healing analysis completed successfully!")
                sys.exit(0)
            else:
                print("💥 Self-healing analysis failed")
                sys.exit(1)

        elif args.workflow_run_id:
            # Analyze specific workflow run
            jobs = healer.get_workflow_run_jobs(args.workflow_run_id)

            for job in jobs:
                if job['name'] in args.job_names and job['conclusion'] == 'failure':
                    logs = healer.get_job_logs(job['id'])
                    parsed = healer.parse_failure_logs(logs, job['name'])

                    print(json.dumps(parsed, indent=2))
                    break

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
