#!/usr/bin/env python3
"""Call i2 API endpoints: list-models, model-info, chat, embed, cost-estimate."""

import argparse
import json
import os
import sys
import time
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


def make_request(
    url: str,
    key: str,
    method: str = "GET",
    body: bytes | None = None,
    content_type: str = "application/json",
    timeout: int = 60,
    max_retries: int = 0,
) -> tuple[int, dict[str, str], bytes]:
    """Make an HTTP request with optional retry/backoff. Returns (status, headers, body)."""
    headers: dict[str, str] = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    if body is not None:
        headers["Content-Type"] = content_type

    attempt = 0
    while True:
        try:
            resp = requests.request(
                method, url, headers=headers, data=body, timeout=timeout
            )
            resp.raise_for_status()
            return resp.status_code, dict(resp.headers), resp.content
        except requests.HTTPError as exc:
            if exc.response.status_code < 500 or attempt >= max_retries:
                raise RuntimeError(
                    f"HTTP {exc.response.status_code}: {exc.response.text}"
                ) from exc
        except requests.RequestException as exc:
            if attempt >= max_retries:
                raise RuntimeError(f"Network error: {exc}") from exc

        sleep_secs = min(1 * (2 ** attempt), 30)
        print(
            f"Request failed (attempt {attempt + 1}/{max_retries + 1}), "
            f"retrying in {sleep_secs}s...",
            file=sys.stderr,
        )
        time.sleep(sleep_secs)
        attempt += 1


def stream_chat(
    url: str,
    key: str,
    payload: dict[str, Any],
    timeout: int = 120,
    max_retries: int = 0,
) -> int:
    """Stream a chat completion, printing content chunks as they arrive."""
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    attempt = 0
    while True:
        try:
            with requests.post(
                url, headers=headers, json=payload, stream=True, timeout=timeout
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            print(content, end="", flush=True)
                    except json.JSONDecodeError:
                        pass
            print()  # newline after stream ends
            return 0
        except requests.HTTPError as exc:
            if exc.response.status_code < 500 or attempt >= max_retries:
                print(f"HTTP {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
                return 1
        except requests.RequestException as exc:
            if attempt >= max_retries:
                print(f"Network error: {exc}", file=sys.stderr)
                return 1

        sleep_secs = min(1 * (2 ** attempt), 30)
        print(
            f"Stream failed (attempt {attempt + 1}/{max_retries + 1}), "
            f"retrying in {sleep_secs}s...",
            file=sys.stderr,
        )
        time.sleep(sleep_secs)
        attempt += 1


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_list_models(args: argparse.Namespace) -> int:
    key = get_api_key()
    url = f"{args.base_url.rstrip('/')}/v1/models"

    try:
        _, _, body = make_request(url, key, timeout=args.timeout)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    data = json.loads(body.decode("utf-8"))

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    models = data.get("data", [])
    chat_models = [m["id"] for m in models if m.get("object") == "model"]

    # Group by a rough heuristic -- embed models contain "embed" in their id
    embed_ids = [m for m in chat_models if "embed" in m.lower()]
    chat_ids = [m for m in chat_models if m not in embed_ids]

    print("Chat / Completion Models:")
    for m in sorted(chat_ids):
        print(f"  {m}")
    print()
    print("Embedding Models:")
    for m in sorted(embed_ids):
        print(f"  {m}")

    return 0


def cmd_model_info(args: argparse.Namespace) -> int:
    key = get_api_key()
    url = f"{args.base_url.rstrip('/')}/model/info"

    try:
        _, _, body = make_request(url, key, timeout=args.timeout)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    data = json.loads(body.decode("utf-8"))
    models: list[dict[str, Any]] = data.get("data", [])

    # Filter to a single model if requested
    if args.model:
        models = [m for m in models if m.get("model_name") == args.model]
        if not models:
            print(f"Error: model '{args.model}' not found", file=sys.stderr)
            return 1

    # Extract a specific property if requested
    if args.property:
        result = []
        for m in models:
            model_info = m.get("model_info", {})
            value = model_info.get(args.property, m.get(args.property))
            result.append({"model_name": m.get("model_name"), args.property: value})
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for r in result:
                print(f"{r['model_name']}: {r[args.property]}")
        return 0

    if args.json:
        print(json.dumps({"data": models}, indent=2))
        return 0

    # Human-readable summary
    for m in models:
        name = m.get("model_name", "?")
        info = m.get("model_info", {})
        mode = info.get("mode", "?")
        ctx = info.get("max_input_tokens", "?")
        out = info.get("max_output_tokens", "?")
        input_cost = info.get("input_cost_per_token")
        output_cost = info.get("output_cost_per_token")
        caching = info.get("supports_prompt_caching", False)
        vision = info.get("supports_vision", False)
        tools = info.get("supports_function_calling", False)

        input_cost_str = f"${input_cost * 1_000_000:.4f}/M" if input_cost else "?"
        output_cost_str = f"${output_cost * 1_000_000:.4f}/M" if output_cost else "?"

        print(f"{name}")
        print(f"  mode={mode}  context={ctx}  max_output={out}")
        print(f"  input={input_cost_str}  output={output_cost_str}")
        print(f"  vision={vision}  tools={tools}  caching={caching}")
        print()

    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    key = get_api_key()
    url = f"{args.base_url.rstrip('/')}/v1/chat/completions"

    messages: list[dict[str, str]] = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.message})

    payload: dict[str, Any] = {"model": args.model, "messages": messages, "stream": args.stream}
    if args.max_tokens:
        payload["max_tokens"] = args.max_tokens

    if args.stream:
        return stream_chat(url, key, payload, timeout=args.timeout, max_retries=args.max_retries)

    body_bytes = json.dumps(payload).encode("utf-8")
    try:
        _, resp_headers, resp_body = make_request(
            url, key, method="POST", body=body_bytes, timeout=args.timeout,
            max_retries=args.max_retries,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    data = json.loads(resp_body.decode("utf-8"))

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    print(content)

    # Show cost if available in response headers
    cost = resp_headers.get("x-litellm-response-cost")
    if cost:
        print(f"\n[cost: ${cost}]", file=sys.stderr)

    return 0


def cmd_embed(args: argparse.Namespace) -> int:
    key = get_api_key()
    url = f"{args.base_url.rstrip('/')}/v1/embeddings"

    payload = {"model": args.model, "input": args.input}
    body_bytes = json.dumps(payload).encode("utf-8")

    try:
        _, _, resp_body = make_request(
            url, key, method="POST", body=body_bytes, timeout=args.timeout,
            max_retries=args.max_retries,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    data = json.loads(resp_body.decode("utf-8"))

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    embedding = data.get("data", [{}])[0].get("embedding", [])
    print(f"model: {data.get('model', args.model)}")
    print(f"vector_length: {len(embedding)}")
    print(f"first_5_values: {embedding[:5]}")

    return 0


def cmd_cost_estimate(args: argparse.Namespace) -> int:
    key = get_api_key()
    url = f"{args.base_url.rstrip('/')}/cost/calculate"

    payload: dict[str, Any] = {
        "model": args.model,
        "prompt_tokens": args.input_tokens,
        "completion_tokens": args.output_tokens,
    }
    body_bytes = json.dumps(payload).encode("utf-8")

    try:
        _, _, resp_body = make_request(
            url, key, method="POST", body=body_bytes, timeout=args.timeout,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    data = json.loads(resp_body.decode("utf-8"))

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    cost = data.get("cost", data)
    print(f"model: {args.model}")
    print(f"input_tokens: {args.input_tokens}")
    print(f"output_tokens: {args.output_tokens}")
    print(f"estimated_cost: {cost}")

    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="i2 API helper: list-models, model-info, chat, embed, cost-estimate"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-models
    lm = subparsers.add_parser("list-models", help="List available model IDs")
    lm.add_argument("--json", action="store_true", help="Emit raw JSON")
    lm.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    lm.set_defaults(func=cmd_list_models)

    # model-info
    mi = subparsers.add_parser("model-info", help="Show detailed model metadata")
    mi.add_argument("--model", help="Filter to a specific model name")
    mi.add_argument("--property", help="Extract a specific model_info property for all models")
    mi.add_argument("--json", action="store_true", help="Emit raw JSON")
    mi.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    mi.set_defaults(func=cmd_model_info)

    # chat
    chat = subparsers.add_parser("chat", help="Send a chat completion request")
    chat.add_argument("--model", required=True, help="Model name (e.g. claude-sonnet)")
    chat.add_argument("--message", required=True, help="User message text")
    chat.add_argument("--system", help="Optional system prompt")
    chat.add_argument("--stream", action="store_true", help="Stream response chunks")
    chat.add_argument("--max-tokens", type=int, help="Maximum output tokens")
    chat.add_argument("--json", action="store_true", help="Emit raw JSON (non-streaming only)")
    chat.add_argument("--timeout", type=int, default=120, help="Request timeout in seconds")
    chat.add_argument(
        "--max-retries", type=int, default=0,
        help="Retry count with exponential backoff (default: 0)"
    )
    chat.set_defaults(func=cmd_chat)

    # embed
    embed = subparsers.add_parser("embed", help="Generate an embedding vector")
    embed.add_argument("--model", required=True, help="Embedding model name")
    embed.add_argument("--input", required=True, help="Text to embed")
    embed.add_argument("--json", action="store_true", help="Emit raw JSON")
    embed.add_argument("--timeout", type=int, default=60, help="Request timeout in seconds")
    embed.add_argument("--max-retries", type=int, default=0, help="Retry count")
    embed.set_defaults(func=cmd_embed)

    # cost-estimate
    ce = subparsers.add_parser("cost-estimate", help="Estimate cost for a model call")
    ce.add_argument("--model", required=True, help="Model name")
    ce.add_argument("--input-tokens", type=int, required=True, help="Number of input tokens")
    ce.add_argument("--output-tokens", type=int, required=True, help="Number of output tokens")
    ce.add_argument("--json", action="store_true", help="Emit raw JSON")
    ce.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    ce.set_defaults(func=cmd_cost_estimate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
