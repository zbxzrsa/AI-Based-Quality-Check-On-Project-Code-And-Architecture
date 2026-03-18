import logging

logger = logging.getLogger(__name__)

import re
import subprocess
import sys


def run_collection():
    logger.info("Running pytest collection...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only"],
        capture_output=True,
        text=True,
        cwd="d:\\Desktop\\AI-Based-Quality-Check-On-Project-Code-And-Architecture\\backend",
    )

    with open("pytest_collection_output.log", "w", encoding="utf-8") as f:
        f.write(result.stdout)
        f.write("\n" + "=" * 50 + "\n")
        f.write(result.stderr)

    errors = []

    # Regex to find error blocks in pytest output
    # Example: _____ ERROR collecting tests/test_file.py _____________
    error_header_re = re.compile(r"_{5,} ERROR collecting (.*?) _{5,}")

    lines = result.stdout.splitlines()
    for i, line in enumerate(lines):
        match = error_header_re.search(line)
        if match:
            file_path = match.group(1)
            # Capture the next few lines for the error message
            error_msg = ""
            for j in range(i + 1, min(i + 10, len(lines))):
                if (
                    lines[j].strip().startswith("E   ")
                    or "ImportError" in lines[j]
                    or "ModuleNotFoundError" in lines[j]
                ):
                    error_msg = lines[j].strip()
                    break
            errors.append(f"{file_path}: {error_msg}")

    with open("collection_errors_summary.txt", "w", encoding="utf-8") as f:
        f.write(f"Total collection errors found: {len(errors)}\n\n")
        for err in errors:
            f.write(err + "\n")

    logger.info("Summary written to collection_errors_summary.txt. Found {len(errors)} errors.")


if __name__ == "__main__":
    run_collection()
