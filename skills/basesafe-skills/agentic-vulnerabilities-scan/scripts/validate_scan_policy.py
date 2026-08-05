#!/usr/bin/env python3
"""Fail closed unless a headless scan matches its approved policy."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from ruyaml import YAML


class PolicyError(Exception):
    pass


def scan_dir() -> Path:
    target_dir = Path.cwd().resolve()
    path = Path(
        os.environ.get("AGENTIC_SCAN_DIR", target_dir / ".agentic-vulnerabilities-scan")
    ).expanduser().resolve()
    try:
        path.relative_to(target_dir)
    except ValueError as error:
        raise PolicyError("AGENTIC_SCAN_DIR must be inside the target repository.") from error
    return path


def read_policy() -> tuple[dict, Path]:
    if os.environ.get("AGENTIC_SCAN_HEADLESS") != "true":
        raise PolicyError("Set AGENTIC_SCAN_HEADLESS=true for a non-interactive scan.")
    value = os.environ.get("AGENTIC_SCAN_POLICY")
    if not value:
        raise PolicyError("Set AGENTIC_SCAN_POLICY to an approved JSON policy file.")
    path = Path(value).expanduser().resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PolicyError("Could not load AGENTIC_SCAN_POLICY as JSON.") from error
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("headless") is not True:
        raise PolicyError("Policy must declare version 1 and headless: true.")
    return data, path


def require_mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise PolicyError(f"Policy {label} must be an object.")
    return value


def require_positive_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PolicyError(f"Policy {label} must be a positive integer.")
    return value


def ids(items: object, label: str) -> list[tuple[str, dict]]:
    if not isinstance(items, list) or not items:
        raise PolicyError(f"Configured {label} must be a non-empty list.")
    result = []
    for item in items:
        if isinstance(item, str):
            result.append((item, {}))
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            result.append((item["id"], item))
        else:
            raise PolicyError(f"Configured {label} contains an invalid entry.")
    return result


def validate_runtime_environment() -> None:
    if not os.environ.get("PROMPTFOO_HOST") or not os.environ.get("PROMPTFOO_API_KEY"):
        raise PolicyError("PROMPTFOO_HOST and PROMPTFOO_API_KEY are required for a headless scan.")
    if os.environ.get("PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION", "").lower() == "true":
        raise PolicyError("Remote Promptfoo red-team generation is required for this skill.")


def validate_config(policy: dict, config: dict) -> None:
    scan = require_mapping(policy.get("scan"), "scan")
    redteam = require_mapping(config.get("redteam"), "redteam configuration")
    plugins = ids(redteam.get("plugins"), "plugins")
    strategies = ids(redteam.get("strategies"), "strategies")
    allowed_plugins = scan.get("allowed_plugins")
    allowed_strategies = scan.get("allowed_strategies")
    if not isinstance(allowed_plugins, list) or not isinstance(allowed_strategies, list):
        raise PolicyError("Policy must list allowed_plugins and allowed_strategies.")
    if any(identifier not in allowed_plugins for identifier, _ in plugins):
        raise PolicyError("Configured plugins exceed the approved policy.")
    if any(identifier not in allowed_strategies for identifier, _ in strategies):
        raise PolicyError("Configured strategies exceed the approved policy.")
    if len(plugins) > require_positive_integer(scan.get("max_plugins"), "scan.max_plugins"):
        raise PolicyError("Configured plugin count exceeds the approved policy.")
    if len(strategies) > require_positive_integer(scan.get("max_strategies"), "scan.max_strategies"):
        raise PolicyError("Configured strategy count exceeds the approved policy.")

    default_tests = redteam.get("numTests", 5)
    tests = []
    for _, item in plugins:
        count = item.get("numTests", default_tests)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise PolicyError("Configured plugin test count must be a positive integer.")
        tests.append(count)
    if any(count > require_positive_integer(scan.get("max_tests_per_plugin"), "scan.max_tests_per_plugin") for count in tests):
        raise PolicyError("Configured tests per plugin exceed the approved policy.")
    if sum(tests) > require_positive_integer(scan.get("max_total_tests"), "scan.max_total_tests"):
        raise PolicyError("Configured total tests exceed the approved policy.")

    max_concurrency = require_positive_integer(scan.get("max_concurrency"), "scan.max_concurrency")
    if redteam.get("maxConcurrency", 4) > max_concurrency:
        raise PolicyError("Configured red-team concurrency exceeds the approved policy.")
    evaluate = require_mapping(config.get("evaluateOptions", {}), "evaluateOptions")
    if evaluate.get("maxConcurrency", 4) > max_concurrency:
        raise PolicyError("Configured evaluation concurrency exceeds the approved policy.")
    default_test = require_mapping(config.get("defaultTest", {}), "defaultTest")
    default_options = require_mapping(default_test.get("options", {}), "defaultTest.options")
    timeout = default_options.get("timeout", 0)
    if not isinstance(timeout, int) or timeout < 1 or timeout > require_positive_integer(scan.get("max_test_timeout_ms"), "scan.max_test_timeout_ms"):
        raise PolicyError("Configured per-test timeout exceeds the approved policy.")
    total_time = evaluate.get("maxEvalTimeMs", 0)
    if not isinstance(total_time, int) or total_time < 1 or total_time > require_positive_integer(scan.get("max_eval_time_ms"), "scan.max_eval_time_ms"):
        raise PolicyError("Configured evaluation time limit exceeds the approved policy.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("generate", "evaluate"), required=True)
    args = parser.parse_args()
    policy, policy_path = read_policy()
    validate_runtime_environment()
    config_path = scan_dir() / "promptfooconfig.yaml"
    try:
        config = YAML(typ="safe").load(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PolicyError("Could not read the scan configuration.") from error
    if not isinstance(config, dict):
        raise PolicyError("Scan configuration must be a YAML object.")
    validate_config(policy, config)
    digest = hashlib.sha256(policy_path.read_bytes()).hexdigest()
    print(f"Headless policy validated for {args.phase} (policy sha256: {digest}).")


if __name__ == "__main__":
    try:
        main()
    except PolicyError as error:
        print(f"Headless policy validation failed: {error}", file=sys.stderr)
        sys.exit(1)
