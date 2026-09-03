#!/usr/bin/env python3
"""Run a scan phase, enforcing headless policy validation when enabled."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from promptfoo_environment import promptfoo_environment


def promptfoo_command(phase: str) -> list[str]:
    if phase == "generate":
        return ["promptfoo", "redteam", "generate"]
    return [
        "promptfoo",
        "redteam",
        "eval",
        "--output",
        "results.json",
        "--max-concurrency",
        "1",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate", "evaluate"))
    args = parser.parse_args()
    if not shutil.which("promptfoo"):
        raise RuntimeError("promptfoo is not installed.")

    target_dir = Path.cwd().resolve()
    if os.environ.get("AGENTIC_SCAN_HEADLESS") == "true":
        wrapper = Path(__file__).with_name("run_headless_scan_phase.py")
        result = subprocess.run([sys.executable, str(wrapper), args.phase], cwd=target_dir, env=os.environ)
        sys.exit(result.returncode)

    if os.environ.get("PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION", "").lower() == "true":
        raise RuntimeError("Remote Promptfoo red-team generation is required for this skill.")
    scan_dir = Path(
        os.environ.get("AGENTIC_SCAN_DIR", target_dir / ".agentic-vulnerabilities-scan")
    ).expanduser().resolve()
    reviewer = Path(__file__).with_name("review_scan_bounds.py")
    preflight = subprocess.run([sys.executable, str(reviewer)], cwd=target_dir, env=os.environ)
    if preflight.returncode:
        print("Interactive scan preflight failed; Promptfoo was not started.", file=sys.stderr)
        sys.exit(preflight.returncode)
    result = subprocess.run(
        promptfoo_command(args.phase), cwd=scan_dir, env=promptfoo_environment(args.phase)
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
