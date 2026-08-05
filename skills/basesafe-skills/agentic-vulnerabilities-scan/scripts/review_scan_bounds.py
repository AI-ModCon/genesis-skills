#!/usr/bin/env python3
"""Fail closed when an interactive scan exceeds its initial bounds."""

import os
from pathlib import Path
import sys

from ruyaml import YAML


DEFAULT_MAX_PLUGINS = 2
DEFAULT_MAX_STRATEGIES = 2
DEFAULT_MAX_TESTS_PER_PLUGIN = 2
DEFAULT_MAX_TOTAL_TESTS = 4


def scan_dir() -> Path:
    target_dir = Path.cwd().resolve()
    return Path(
        os.environ.get("AGENTIC_SCAN_DIR", target_dir / ".agentic-vulnerabilities-scan")
    ).expanduser().resolve()


def configured_items(value: object, label: str) -> list[tuple[str, dict]]:
    if not isinstance(value, list):
        raise ValueError(f"redteam.{label} must be a list")
    items = []
    for entry in value:
        if isinstance(entry, str):
            items.append((entry, {}))
        elif isinstance(entry, dict) and isinstance(entry.get("id"), str):
            items.append((entry["id"], entry))
        else:
            raise ValueError(f"redteam.{label} contains an invalid entry")
    return items


def interactive_limit(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        limit = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a positive integer") from error
    if limit < 1:
        raise ValueError(f"{name} must be a positive integer")
    return limit


def main() -> int:
    config_path = scan_dir() / "promptfooconfig.yaml"
    try:
        config = YAML(typ="safe").load(config_path.read_text(encoding="utf-8"))
        if not isinstance(config, dict) or not isinstance(config.get("redteam"), dict):
            raise ValueError("missing redteam configuration")
        redteam = config["redteam"]
        plugins = configured_items(redteam.get("plugins"), "plugins")
        strategies = configured_items(redteam.get("strategies"), "strategies")
        default_tests = redteam.get("numTests", 5)
        if not isinstance(default_tests, int) or isinstance(default_tests, bool) or default_tests < 1:
            raise ValueError("redteam.numTests must be a positive integer")
        limits = {
            "plugins": interactive_limit("INTERACTIVE_SCAN_MAX_PLUGINS", DEFAULT_MAX_PLUGINS),
            "strategies": interactive_limit("INTERACTIVE_SCAN_MAX_STRATEGIES", DEFAULT_MAX_STRATEGIES),
            "tests_per_plugin": interactive_limit(
                "INTERACTIVE_SCAN_MAX_TESTS_PER_PLUGIN", DEFAULT_MAX_TESTS_PER_PLUGIN
            ),
            "total_tests": interactive_limit(
                "INTERACTIVE_SCAN_MAX_TOTAL_TESTS", DEFAULT_MAX_TOTAL_TESTS
            ),
        }
        test_counts = []
        for _, item in plugins:
            count = item.get("numTests", default_tests)
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise ValueError("plugin numTests values must be positive integers")
            test_counts.append(count)
    except (OSError, ValueError) as error:
        print(f"Interactive scan preflight could not summarize bounds: {error}.", file=sys.stderr)
        return 1

    test_count = sum(test_counts)
    print(
        "Interactive scan preflight: "
        f"{len(plugins)} plugin(s), {len(strategies)} strategy/strategies, "
        f"{test_count} configured plugin test(s). Limits: "
        f"{limits['plugins']} plugin(s), {limits['strategies']} strategy/strategies, "
        f"{limits['tests_per_plugin']} test(s) per plugin, {limits['total_tests']} total test(s)."
    )
    violations = []
    if len(plugins) > limits["plugins"]:
        violations.append(f"plugins {len(plugins)} > {limits['plugins']}")
    if len(strategies) > limits["strategies"]:
        violations.append(f"strategies {len(strategies)} > {limits['strategies']}")
    if any(count > limits["tests_per_plugin"] for count in test_counts):
        violations.append(f"tests per plugin exceed {limits['tests_per_plugin']}")
    if test_count > limits["total_tests"]:
        violations.append(f"total tests {test_count} > {limits['total_tests']}")
    if violations:
        print(
            "Interactive scan preflight blocked execution: " + "; ".join(violations) + ". "
            "Reduce the configuration or set approved INTERACTIVE_SCAN_MAX_* limits, "
            "then rerun the phase.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
