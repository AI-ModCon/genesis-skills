from pathlib import Path
import sys
from ruyaml.scalarstring import LiteralScalarString

from verify_target import (
    SCAN_DIR,
    PROMPTFOO_CONFIG_PATH,
    REDTEAM_TESTS_PATH,
    ABORT,
    ExitWithMessage,
    update_promptfoo_config,
)

FINDINGS_PATH = SCAN_DIR / "findings.md"


def main(path: Path = FINDINGS_PATH) -> None:

    try:
        with path.open("r", encoding="utf-8") as f:
            findings = f.read()
    except OSError as error:
        raise ExitWithMessage(f"Could not read {FINDINGS_PATH.name}.{ABORT}") from error

    update_promptfoo_config({"redteam": {"purpose": LiteralScalarString(findings)}})

    print("Findings recorded. Proceed to step 3.")


if __name__ == "__main__":

    try:
        main()
    except ExitWithMessage as error:
        print(error)
        sys.exit(1)
