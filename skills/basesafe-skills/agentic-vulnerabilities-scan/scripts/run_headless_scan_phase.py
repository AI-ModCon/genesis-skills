#!/usr/bin/env python3
"""Validate a headless scan policy and run one Promptfoo phase atomically."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def promptfoo_environment(phase: str) -> dict[str, str]:
    """Treat failed red-team assertions as findings, not runner failures."""
    environment = os.environ.copy()
    if phase == "evaluate":
        environment["PROMPTFOO_FAILED_TEST_EXIT_CODE"] = "0"
    return environment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate", "evaluate"))
    args = parser.parse_args()
    if not shutil.which("promptfoo"):
        raise RuntimeError("promptfoo is not installed.")

    target_dir = Path.cwd().resolve()
    scan_dir = Path(
        os.environ.get("AGENTIC_SCAN_DIR", target_dir / ".agentic-vulnerabilities-scan")
    ).expanduser().resolve()
    validator = Path(__file__).with_name("validate_scan_policy.py")
    validation = subprocess.run(
        [sys.executable, str(validator), "--phase", args.phase],
        cwd=target_dir,
        env=os.environ,
    )
    if validation.returncode:
        sys.exit(validation.returncode)

    command = ["promptfoo", "redteam", "generate"]
    if args.phase == "evaluate":
        command = [
            "promptfoo",
            "redteam",
            "eval",
            "--output",
            "results.json",
            "--max-concurrency",
            "1",
        ]
    result = subprocess.run(command, cwd=scan_dir, env=promptfoo_environment(args.phase))
    sys.exit(result.returncode)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
