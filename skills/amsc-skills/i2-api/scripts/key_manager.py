#!/usr/bin/env python3
"""Validate the i2 API key and check spend/budget via /user/info."""

import argparse
import json
import os
import sys
from typing import Any

import requests

DEFAULT_BASE_URL = "https://api.i2-core.american-science-cloud.org"
ENV_KEY_NAME = "AMSC_I2_API_KEY"


def get_api_key() -> str:
    key = os.environ.get(ENV_KEY_NAME, "").strip()
    if not key:
        print(
            f"Error: {ENV_KEY_NAME} is not set. "
            "Generate a key at https://api.i2-core.american-science-cloud.org/ "
            "and export it as an environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def make_request(url: str, key: str, timeout: int = 30) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.response.status_code}: {exc.response.text}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def cmd_status(args: argparse.Namespace) -> int:
    key = get_api_key()
    url = f"{args.base_url.rstrip('/')}/v1/models"

    result: dict[str, Any] = {"key_set": True, "key_valid": False, "model_count": 0}

    try:
        data = make_request(url, key)
        models = data.get("data", [])
        result["key_valid"] = True
        result["model_count"] = len(models)
    except RuntimeError as exc:
        result["error"] = str(exc)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["key_valid"] else 1

    if result["key_valid"]:
        print(f"key_set: {result['key_set']}")
        print(f"key_valid: {result['key_valid']}")
        print(f"model_count: {result['model_count']}")
    else:
        print(f"key_set: {result['key_set']}")
        print(f"key_valid: {result['key_valid']}")
        print(f"error: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1

    return 0


def cmd_spend(args: argparse.Namespace) -> int:
    key = get_api_key()
    # /user/info is served from the LiteLLM proxy -- note the different base path
    url = f"{args.base_url.rstrip('/')}/user/info"

    try:
        data = make_request(url, key)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    # Extract the most useful fields from the LiteLLM /user/info response
    info = data.get("info", data)
    budget_duration = info.get("budget_duration")
    max_budget = info.get("max_budget")
    spend = info.get("spend")
    remaining = (max_budget - spend) if (max_budget is not None and spend is not None) else None

    print(f"spend: {spend}")
    print(f"max_budget: {max_budget}")
    print(f"remaining: {remaining}")
    if budget_duration:
        print(f"budget_duration: {budget_duration}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the i2 API key and check spend/budget"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser(
        "status", help="Check if the API key is set and valid"
    )
    status_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON output"
    )
    status_parser.set_defaults(func=cmd_status)

    spend_parser = subparsers.add_parser(
        "spend", help="Show budget and current spend from /user/info"
    )
    spend_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON output"
    )
    spend_parser.set_defaults(func=cmd_spend)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
