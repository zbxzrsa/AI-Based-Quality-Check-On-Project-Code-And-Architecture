import logging

logger = logging.getLogger(__name__)

import json
import subprocess
from datetime import datetime
from pathlib import Path


def run_command(command, cwd=None):
    logger.info("Running: {' '.join(command)}")
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def main():
    backend_dir = Path(__file__).parent.parent.absolute()
    report = {"timestamp": datetime.now().isoformat(), "tools": {}}

    # 1. Pylint
    logger.info("--- Running Pylint ---")
    pylint_cmd = ["pylint", "app", "--output-format=json", "--exit-zero"]
    _, stdout, stderr = run_command(pylint_cmd, cwd=backend_dir)
    try:
        report["tools"]["pylint"] = json.loads(stdout) if stdout else []
    except json.JSONDecodeError:
        report["tools"]["pylint"] = {"error": "Failed to parse pylint JSON", "raw": stdout}

    # 2. Mypy
    logger.info("--- Running Mypy ---")
    mypy_cmd = ["mypy", "app", "--ignore-missing-imports"]
    code, stdout, stderr = run_command(mypy_cmd, cwd=backend_dir)
    report["tools"]["mypy"] = {"returncode": code, "output": stdout}

    # 3. Radon Complexity
    logger.info("--- Running Radon Cyclomatic Complexity ---")
    radon_cc_cmd = ["radon", "cc", "app", "-a", "-s", "-j"]
    _, stdout, stderr = run_command(radon_cc_cmd, cwd=backend_dir)
    try:
        report["tools"]["radon_cc"] = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        report["tools"]["radon_cc"] = {"error": "Failed to parse radon JSON", "raw": stdout}

    # 4. Radon Maintainability Index
    logger.info("--- Running Radon Maintainability Index ---")
    radon_mi_cmd = ["radon", "mi", "app", "-j"]
    _, stdout, stderr = run_command(radon_mi_cmd, cwd=backend_dir)
    try:
        report["tools"]["radon_mi"] = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        report["tools"]["radon_mi"] = {"error": "Failed to parse radon JSON", "raw": stdout}

    # 5. Bandit Security
    logger.info("--- Running Bandit Security Scanner ---")
    bandit_cmd = ["bandit", "-r", "app", "-f", "json", "--exit-zero"]
    _, stdout, stderr = run_command(bandit_cmd, cwd=backend_dir)
    try:
        report["tools"]["bandit"] = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        report["tools"]["bandit"] = {"error": "Failed to parse bandit JSON", "raw": stdout}

    # Save Report
    report_path = backend_dir / "code_quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("\nReport generated successfully: {report_path}")


if __name__ == "__main__":
    main()
