#!/usr/bin/env python3
"""Call the AmSC Model Access Gateway (MAG): list-models, chat, embed.

Reads the PAT from AMSC_TOKEN (never printed). Stdlib only.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://mag.genesis.americansciencecloud.org"
ENV_TOKEN_NAME = "AMSC_TOKEN"


def get_token() -> str:
    token = os.environ.get(ENV_TOKEN_NAME, "").strip()
    if not token:
        sys.exit(
            f"Error: {ENV_TOKEN_NAME} is not set. Generate a PAT at "
            "https://my.amsc.energy.gov/dashboard (project -> Personal Access Tokens) "
            "and export it in your current shell session."
        )
    return token


def request(url, token, payload=None, extra_headers=None, timeout=120, retries=0):
    """Return (status, headers, response); raise RuntimeError on failure.

    The response is the open file-like urllib response; the caller reads or iterates it.
    """
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json",
               "User-Agent": "amsc-mag-skill"}
    headers.update(extra_headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    attempt = 0
    while True:
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            return resp.status, dict(resp.headers), resp
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            hint = " (PAT expired or invalid: generate a new one)" if exc.code == 401 else ""
            # Only gateway-level failures are retried; a 500 on POST may have been processed.
            retryable = exc.code in (502, 503, 504)
            if not retryable or attempt >= retries:
                raise RuntimeError(f"HTTP {exc.code}{hint}: {body}") from exc
        except urllib.error.URLError as exc:
            if attempt >= retries:
                raise RuntimeError(f"Network error: {exc.reason}") from exc
        time.sleep(min(2 ** attempt, 30))
        attempt += 1


def routing_headers(args):
    pairs = {
        "X-AmSC-MAG-Provider": args.provider,
        "X-AmSC-MAG-Effort": args.effort,
        "X-AmSC-MAG-Service-Tier": args.service_tier,
        "X-AmSC-MAG-Compression": args.compression,
    }
    return {k: v for k, v in pairs.items() if v}


def cmd_list_models(args):
    _, _, resp = request(f"{args.base_url.rstrip('/')}/v1/models", get_token(), timeout=args.timeout)
    data = json.loads(resp.read().decode("utf-8"))
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    for m in sorted(data.get("data", []), key=lambda m: m.get("id", "")):
        print(m.get("id"))
    return 0


def cmd_chat(args):
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": args.message})
    payload = {"model": args.model, "messages": messages, "stream": args.stream}
    if args.max_tokens:
        # Reasoning tokens count against this limit; keep it >= ~2000 for reasoning models.
        payload["max_completion_tokens"] = args.max_tokens
    url = f"{args.base_url.rstrip('/')}/v1/chat/completions"
    _, headers, resp = request(
        url, get_token(), payload, routing_headers(args), args.timeout, args.max_retries
    )
    applied = {k.lower(): v for k, v in headers.items()}.get("x-amsc-mag-applied")
    if args.stream:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                obj = json.loads(chunk)
            except json.JSONDecodeError:
                continue
            if "error" in obj:
                print(f"Error: {obj['error']}", file=sys.stderr)
                return 1
            delta = (obj.get("choices") or [{}])[0].get("delta", {})
            if delta.get("content"):
                print(delta["content"], end="", flush=True)
        print()
    else:
        data = json.loads(resp.read().decode("utf-8"))
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
    if applied:
        print(f"[X-AmSC-MAG-Applied: {applied}]", file=sys.stderr)
    return 0


def cmd_embed(args):
    url = f"{args.base_url.rstrip('/')}/v1/embeddings"
    _, _, resp = request(
        url, get_token(), {"model": args.model, "input": args.input},
        timeout=args.timeout, retries=args.max_retries,
    )
    data = json.loads(resp.read().decode("utf-8"))
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    vec = data.get("data", [{}])[0].get("embedding", [])
    print(f"model: {data.get('model', args.model)}")
    print(f"vector_length: {len(vec)}")
    print(f"first_5_values: {vec[:5]}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="MAG helper: list-models, chat, embed")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"default: {DEFAULT_BASE_URL}")
    sub = p.add_subparsers(dest="command", required=True)

    lm = sub.add_parser("list-models", help="List live model ids")
    lm.add_argument("--json", action="store_true")
    lm.add_argument("--timeout", type=int, default=30)
    lm.set_defaults(func=cmd_list_models)

    ch = sub.add_parser("chat", help="Send a chat completion")
    ch.add_argument("--model", required=True, help="e.g. claude-sonnet or gpt-5.4:high@openai")
    ch.add_argument("--message", required=True)
    ch.add_argument("--system")
    ch.add_argument("--stream", action="store_true")
    ch.add_argument("--max-tokens", type=int)
    ch.add_argument("--provider", help="openai|amazon|google|microsoft")
    ch.add_argument("--effort", help="none|minimal|low|medium|high|xhigh|max")
    ch.add_argument("--service-tier", choices=["flex", "standard"])
    ch.add_argument("--compression", choices=["compact", "compressed", "off"])
    ch.add_argument("--json", action="store_true")
    ch.add_argument("--timeout", type=int, default=120)
    ch.add_argument("--max-retries", type=int, default=0)
    ch.set_defaults(func=cmd_chat)

    em = sub.add_parser("embed", help="Generate an embedding")
    em.add_argument("--model", required=True)
    em.add_argument("--input", required=True)
    em.add_argument("--json", action="store_true")
    em.add_argument("--timeout", type=int, default=60)
    em.add_argument("--max-retries", type=int, default=0)
    em.set_defaults(func=cmd_embed)
    return p


def main():
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except (RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
