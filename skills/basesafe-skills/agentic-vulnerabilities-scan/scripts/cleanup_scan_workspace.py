"""Remove a scan workspace created by agentic-vulnerabilities-scan."""

import os
from pathlib import Path
import shutil
import sys


TARGET_DIR = Path.cwd().resolve()
SCAN_DIR = Path(
    os.environ.get("AGENTIC_SCAN_DIR", TARGET_DIR / ".agentic-vulnerabilities-scan")
).expanduser().resolve()
def main() -> None:
    try:
        SCAN_DIR.relative_to(TARGET_DIR)
    except ValueError as error:
        raise ValueError("Refusing to remove a directory outside the target repository.") from error
    if SCAN_DIR == TARGET_DIR or SCAN_DIR == Path(SCAN_DIR.anchor):
        raise ValueError("Refusing to remove a non-workspace directory.")
    if not SCAN_DIR.is_dir():
        raise ValueError("Scan workspace does not exist or is not a directory.")
    shutil.rmtree(SCAN_DIR)
    print(f"Removed scan workspace: {SCAN_DIR}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(f"Cleanup did not run: {error}", file=sys.stderr)
        sys.exit(1)
