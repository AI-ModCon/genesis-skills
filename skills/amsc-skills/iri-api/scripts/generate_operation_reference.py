#!/usr/bin/env python3
"""Generate a concise operation reference from OpenAPI JSON."""

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Markdown endpoint reference")
    parser.add_argument("--openapi", type=Path, required=True, help="Path to OpenAPI JSON")
    parser.add_argument("--output", type=Path, required=True, help="Output Markdown path")
    return parser.parse_args()


def load_spec(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def required_params(operation: dict[str, Any]) -> list[str]:
    params = operation.get("parameters", [])
    return [p.get("name") for p in params if p.get("required") and p.get("name")]


def request_content_types(operation: dict[str, Any]) -> list[str]:
    request_body = operation.get("requestBody") or {}
    content = request_body.get("content") or {}
    return sorted(content.keys())


def generate_markdown(spec: dict[str, Any]) -> str:
    public_ops: list[str] = []
    auth_ops: list[str] = []

    header = [
        "# IRI API Operations",
        "",
        "Generated from `openapi.json`.",
        "",
        "Columns:",
        "- `operationId`: OpenAPI operation identifier",
        "- `auth`: `public` or `auth` based on operation security metadata",
        "- `required_params`: required path/query parameters",
        "- `body`: request content types if request body is supported",
        "",
        "| operationId | method | path | auth | required_params | body |",
        "|---|---|---|---|---|---|",
    ]

    for api_path, methods in spec.get("paths", {}).items():
        for method_name, op in methods.items():
            op_id = op.get("operationId", "")
            auth = "auth" if op.get("security") else "public"
            req = ",".join(required_params(op))
            body = ",".join(request_content_types(op))
            row = f"| {op_id} | {method_name.upper()} | `{api_path}` | {auth} | {req} | {body} |"
            if auth == "public":
                public_ops.append(row)
            else:
                auth_ops.append(row)

    lines = header + sorted(public_ops) + sorted(auth_ops)
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    spec = load_spec(args.openapi)
    markdown = generate_markdown(spec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
