#!/usr/bin/env python3
"""
Select the optimal i2 API model for given requirements.

Fetches live model metadata from /model/info, filters by hard requirements,
scores by preferred features and optimization target, and ranks results.

Usage modes:
  CLI flags:   python3 select_model.py --mode chat --vision required --optimize cost
  Natural lang: python3 select_model.py --describe "coding model with tools, 128K context"
  Interview:   python3 select_model.py --interview
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "https://api.i2-core.american-science-cloud.org"
ENV_KEY_NAME = "AMSC_I2_API_KEY"

# Capability keywords used when parsing natural language descriptions
NL_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "vision": {
        "required": ["vision", "image", "visual", "picture", "photo", "multimodal"],
        "not-needed": ["no vision", "no image", "text only", "text-only"],
    },
    "reasoning": {
        "high": ["reasoning", "think", "complex", "difficult", "hard", "deep", "extended thinking"],
        "not-needed": ["no reasoning", "fast", "quick", "simple", "lightweight"],
    },
    "tools": {
        "required": [
            "tool", "function", "function call", "function calling", "tool use",
            "agent", "coding", "code", "programming",
        ],
        "not-needed": ["no tools", "no functions"],
    },
    "caching": {
        "required": ["cach", "prompt cach", "cache"],
        "not-needed": ["no cach"],
    },
    "optimize": {
        "cost": ["cheap", "cost", "budget", "affordable", "inexpensive", "economical"],
        "capability": ["best", "most capable", "powerful", "strongest", "top", "highest quality"],
        "balanced": ["balanced", "moderate", "middle", "reasonable"],
    },
}

# Interview questions and their mapping to filter flags
INTERVIEW_QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "mode",
        "question": "What type of model do you need?",
        "choices": [("1", "chat", "Chat / completion (text generation)"),
                    ("2", "embedding", "Embedding (vector representations)")],
        "default": "chat",
    },
    {
        "key": "vision",
        "question": "Do you need image/vision input support?",
        "choices": [("1", "not-needed", "No"),
                    ("2", "preferred", "Preferred but not required"),
                    ("3", "required", "Yes, required")],
        "default": "not-needed",
        "skip_if_mode": "embedding",
    },
    {
        "key": "reasoning",
        "question": "What level of reasoning/thinking capability do you need?",
        "choices": [("1", "not-needed", "Standard (fast, routine tasks)"),
                    ("2", "standard", "Standard with good quality"),
                    ("3", "high", "Extended reasoning (complex tasks)")],
        "default": "not-needed",
        "skip_if_mode": "embedding",
    },
    {
        "key": "tools",
        "question": "Do you need function/tool calling support?",
        "choices": [("1", "not-needed", "No"),
                    ("2", "preferred", "Preferred but not required"),
                    ("3", "required", "Yes, required")],
        "default": "not-needed",
        "skip_if_mode": "embedding",
    },
    {
        "key": "min_context",
        "question": "Minimum context window size needed?",
        "choices": [("1", 0, "No minimum"),
                    ("2", 8000, "8K tokens"),
                    ("3", 32000, "32K tokens"),
                    ("4", 128000, "128K tokens"),
                    ("5", 200000, "200K tokens")],
        "default": 0,
    },
    {
        "key": "caching",
        "question": "Do you need prompt caching support?",
        "choices": [("1", "not-needed", "No"),
                    ("2", "preferred", "Preferred but not required"),
                    ("3", "required", "Yes, required")],
        "default": "not-needed",
        "skip_if_mode": "embedding",
    },
    {
        "key": "optimize",
        "question": "What should be optimized?",
        "choices": [("1", "cost", "Minimize cost"),
                    ("2", "capability", "Maximize capability"),
                    ("3", "balanced", "Balanced cost/capability")],
        "default": "balanced",
    },
]


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


def fetch_model_info(base_url: str, key: str) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/model/info"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def parse_nl_description(description: str) -> dict[str, Any]:
    """Parse a natural language description into filter criteria."""
    desc_lower = description.lower()
    filters: dict[str, Any] = {}

    for dimension, keyword_map in NL_KEYWORDS.items():
        for value, keywords in keyword_map.items():
            if any(kw in desc_lower for kw in keywords):
                filters[dimension] = value
                break

    # Parse context length mentions like "128K", "200k", "128000"
    ctx_match = re.search(r"(\d+)\s*k\b", desc_lower)
    if ctx_match:
        filters["min_context"] = int(ctx_match.group(1)) * 1000
    else:
        ctx_match = re.search(r"\b(\d{4,})\b", desc_lower)
        if ctx_match:
            filters["min_context"] = int(ctx_match.group(1))

    return filters


def run_interview(mode_override: str | None = None) -> dict[str, Any]:
    """Run an interactive interview and return filter criteria."""
    print("=== i2 Model Selection Interview ===")
    print("Press Enter to accept the default value shown in [brackets].\n")

    filters: dict[str, Any] = {}
    selected_mode = mode_override or "chat"

    for q in INTERVIEW_QUESTIONS:
        key = q["key"]

        # Skip irrelevant questions based on mode
        skip_mode = q.get("skip_if_mode")
        if skip_mode and selected_mode == skip_mode:
            continue

        print(q["question"])
        choices = q["choices"]
        default_val = q["default"]

        # Find the display label for the default
        default_label = next(
            (label for num, val, label in choices if val == default_val), str(default_val)
        )

        for num, val, label in choices:
            marker = " [default]" if val == default_val else ""
            print(f"  {num}) {label}{marker}")

        raw = input("> ").strip()

        if not raw:
            chosen = default_val
        else:
            match = next(((val, label) for num, val, label in choices if num == raw), None)
            if match is None:
                print(f"  Invalid choice, using default: {default_label}")
                chosen = default_val
            else:
                chosen = match[0]

        filters[key] = chosen
        if key == "mode":
            selected_mode = str(chosen)
        print()

    return filters


def score_model(
    model: dict[str, Any],
    filters: dict[str, Any],
) -> tuple[float, list[str]] | None:
    """
    Score a model against the filter criteria.
    Returns (score, reasons) or None if the model fails a required constraint.

    Higher score = better match.
    """
    info = model.get("model_info", {})
    name = model.get("model_name", "")
    reasons: list[str] = []
    score = 0.0

    # --- Hard filters (required constraints) ---

    mode_filter = filters.get("mode", "chat")
    model_mode = info.get("mode", "")
    if mode_filter == "chat" and model_mode not in ("chat", "completion"):
        return None
    if mode_filter == "embedding" and model_mode != "embedding":
        return None

    if filters.get("vision") == "required" and not info.get("supports_vision"):
        return None

    if filters.get("tools") == "required" and not info.get("supports_function_calling"):
        return None

    if filters.get("caching") == "required" and not info.get("supports_prompt_caching"):
        return None

    min_ctx = filters.get("min_context", 0)
    if min_ctx:
        ctx = info.get("max_input_tokens", 0) or 0
        if ctx < min_ctx:
            return None

    min_out = filters.get("min_output", 0)
    if min_out:
        out = info.get("max_output_tokens", 0) or 0
        if out < min_out:
            return None

    # Exclude high-reasoning variants unless reasoning=high is requested
    is_high_reasoning = name.endswith("-high")
    if filters.get("reasoning") == "high":
        if is_high_reasoning:
            score += 20
            reasons.append("extended reasoning mode")
    else:
        # Penalize high-reasoning models when not requested (they cost the same but are slower)
        if is_high_reasoning:
            score -= 5

    # --- Preferred bonuses ---

    if filters.get("vision") == "preferred" and info.get("supports_vision"):
        score += 5
        reasons.append("vision supported")

    if filters.get("tools") == "preferred" and info.get("supports_function_calling"):
        score += 5
        reasons.append("tool calling supported")

    if filters.get("caching") == "preferred" and info.get("supports_prompt_caching"):
        score += 5
        reasons.append("prompt caching supported")

    # --- Optimization target ---

    optimize = filters.get("optimize", "balanced")
    input_cost = info.get("input_cost_per_token") or 0.0
    output_cost = info.get("output_cost_per_token") or 0.0
    avg_cost = (input_cost + output_cost) / 2.0

    ctx_tokens = info.get("max_input_tokens", 0) or 0
    out_tokens = info.get("max_output_tokens", 0) or 0

    if optimize == "cost":
        # Lower cost = higher score; normalize to a 0-50 range
        if avg_cost > 0:
            cost_score = max(0.0, 50.0 - (avg_cost * 1_000_000 * 2))
            score += cost_score
            reasons.append(f"input ${input_cost * 1_000_000:.4f}/M, output ${output_cost * 1_000_000:.4f}/M")
    elif optimize == "capability":
        # Larger context + more features = higher score
        ctx_score = min(30.0, ctx_tokens / 10_000)
        out_score = min(10.0, out_tokens / 10_000)
        feature_score = sum([
            5 if info.get("supports_vision") else 0,
            5 if info.get("supports_function_calling") else 0,
            5 if info.get("supports_prompt_caching") else 0,
        ])
        score += ctx_score + out_score + feature_score
        reasons.append(f"context={ctx_tokens}, max_output={out_tokens}")
    else:  # balanced
        # Blend cost and capability
        if avg_cost > 0:
            cost_score = max(0.0, 25.0 - (avg_cost * 1_000_000))
            score += cost_score
        ctx_score = min(15.0, ctx_tokens / 20_000)
        score += ctx_score
        reasons.append(f"input ${input_cost * 1_000_000:.4f}/M, context={ctx_tokens}")

    return score, reasons


def is_alias(name: str, all_names: set[str]) -> bool:
    """
    Detect alias models -- names without a version number suffix (e.g. "claude-sonnet"
    when "claude-sonnet-4-6" also exists).
    """
    # If the name has no version digits, check if a versioned variant exists
    if not re.search(r"-\d", name):
        for other in all_names:
            if other != name and other.startswith(name + "-") and re.search(r"-\d", other):
                return True
    return False


def select_models(
    models: list[dict[str, Any]],
    filters: dict[str, Any],
    top_n: int = 3,
) -> list[dict[str, Any]]:
    """Filter, score, and rank models. Returns top_n results."""
    all_names = {m.get("model_name", "") for m in models}

    scored: list[tuple[float, dict[str, Any], list[str]]] = []
    for model in models:
        name = model.get("model_name", "")
        # Skip alias models to avoid duplicates in results
        if is_alias(name, all_names):
            continue
        result = score_model(model, filters)
        if result is not None:
            score, reasons = result
            scored.append((score, model, reasons))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"model_name": m.get("model_name"), "score": s, "reasons": r, "model_info": m.get("model_info", {})}
        for s, m, r in scored[:top_n]
    ]


def print_results(results: list[dict[str, Any]], filters: dict[str, Any]) -> None:
    if not results:
        print("No models matched the specified requirements.")
        return

    optimize = filters.get("optimize", "balanced")
    print(f"Top {len(results)} model(s) -- optimized for: {optimize}\n")

    for i, r in enumerate(results, 1):
        name = r["model_name"]
        info = r["model_info"]
        reasons = r["reasons"]
        input_cost = info.get("input_cost_per_token", 0) or 0
        output_cost = info.get("output_cost_per_token", 0) or 0
        ctx = info.get("max_input_tokens", "?")
        out = info.get("max_output_tokens", "?")

        print(f"  {i}. {name}")
        print(f"     context={ctx}  max_output={out}")
        print(f"     input=${input_cost * 1_000_000:.4f}/M  output=${output_cost * 1_000_000:.4f}/M")
        if reasons:
            print(f"     why: {', '.join(reasons)}")
        print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select the optimal i2 model for your requirements"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--top", type=int, default=3, help="Number of results to show (default: 3)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON output"
    )

    # Input modes (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--describe",
        metavar="TEXT",
        help="Natural language description of requirements",
    )
    input_group.add_argument(
        "--interview",
        action="store_true",
        help="Run an interactive interview to specify requirements",
    )

    # Explicit filter flags
    parser.add_argument(
        "--mode", choices=["chat", "embedding"], default="chat",
        help="Model type (default: chat)"
    )
    parser.add_argument(
        "--vision", choices=["required", "preferred", "not-needed"],
        help="Image/vision input support"
    )
    parser.add_argument(
        "--reasoning", choices=["high", "standard", "not-needed"],
        help="Reasoning capability level"
    )
    parser.add_argument(
        "--tools", choices=["required", "preferred", "not-needed"],
        help="Function/tool calling support"
    )
    parser.add_argument(
        "--min-context", type=int, metavar="TOKENS",
        help="Minimum context window in tokens"
    )
    parser.add_argument(
        "--min-output", type=int, metavar="TOKENS",
        help="Minimum max output tokens"
    )
    parser.add_argument(
        "--caching", choices=["required", "preferred", "not-needed"],
        help="Prompt caching support"
    )
    parser.add_argument(
        "--json-mode", choices=["required", "preferred", "not-needed"],
        dest="json_mode",
        help="JSON output mode support"
    )
    parser.add_argument(
        "--optimize", choices=["cost", "capability", "balanced"], default="balanced",
        help="Optimization target (default: balanced)"
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    key = get_api_key()

    try:
        models = fetch_model_info(args.base_url, key)
    except RuntimeError as exc:
        print(f"Error fetching model info: {exc}", file=sys.stderr)
        return 1

    # Build filters from the chosen input mode
    if args.interview:
        filters = run_interview()
    elif args.describe:
        filters = parse_nl_description(args.describe)
        print(f"Parsed requirements: {json.dumps(filters, indent=2)}\n")
    else:
        # Build from explicit CLI flags
        filters = {"mode": args.mode, "optimize": args.optimize}
        if args.vision:
            filters["vision"] = args.vision
        if args.reasoning:
            filters["reasoning"] = args.reasoning
        if args.tools:
            filters["tools"] = args.tools
        if args.min_context:
            filters["min_context"] = args.min_context
        if args.min_output:
            filters["min_output"] = args.min_output
        if args.caching:
            filters["caching"] = args.caching
        if args.json_mode:
            filters["json_mode"] = args.json_mode

    results = select_models(models, filters, top_n=args.top)

    if args.json:
        print(json.dumps({"filters": filters, "results": results}, indent=2))
        return 0

    print_results(results, filters)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
