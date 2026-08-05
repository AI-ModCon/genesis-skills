#!/usr/bin/env python3
"""Call IRI API endpoints using OpenAPI operation IDs or method/path."""

import argparse
import json
import mimetypes
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

FACILITY_CONFIG = {
    "nersc": {
        "base_url": "https://api.iri.nersc.gov",
        "openapi_url": "https://api.iri.nersc.gov/openapi.json",
        "scope": (
            "https://auth.globus.org/scopes/"
            "ed3e577d-f7f3-4639-b96e-ff5a8445d699/iri_api"
        ),
        "label": "NERSC IRI API",
    },
    "alcf": {
        "base_url": "https://api.alcf.anl.gov",
        "openapi_url": "https://api.alcf.anl.gov/openapi.json",
        "scope": (
            "https://auth.globus.org/scopes/"
            "6be511f6-a071-471f-9bc0-02a0d0836723/filesystem"
        ),
        "label": "ALCF IRI API",
    },
}
DEFAULT_FACILITY = "nersc"


class UsageError(Exception):
    pass


def default_openapi_path() -> Path:
    return Path(__file__).resolve().parent.parent / "references" / "openapi.json"


def default_token_file() -> Path:
    return Path.home() / ".globus" / "auth_tokens.json"


def resolve_base_url(facility: str) -> str:
    return FACILITY_CONFIG[facility]["base_url"]


def resolve_openapi_url(facility: str) -> str:
    return FACILITY_CONFIG[facility]["openapi_url"]


def load_openapi(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_openapi_from_url(url: str, timeout: int) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "iri-api-client/1.0"}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def load_selected_openapi(args: argparse.Namespace) -> Dict[str, Any]:
    if args.openapi_url:
        return load_openapi_from_url(args.openapi_url, getattr(args, "timeout", 30))
    return load_openapi(args.openapi)


def parse_kv(values: Optional[List[str]]) -> Dict[str, str]:
    out = {}  # type: Dict[str, str]
    for item in values or []:
        if "=" not in item:
            raise UsageError(f"Expected key=value, got: {item}")
        key, value = item.split("=", 1)
        out[key] = value
    return out


def find_operation(
    spec: Dict[str, Any],
    operation_id: Optional[str],
    method: Optional[str],
    path: Optional[str],
) -> Tuple[str, str, Dict[str, Any]]:
    if operation_id:
        for api_path, methods in spec.get("paths", {}).items():
            for method_name, operation in methods.items():
                if operation.get("operationId") == operation_id:
                    return method_name.upper(), api_path, operation
        raise UsageError(f"operationId not found: {operation_id}")

    if not (method and path):
        raise UsageError("Provide either --operation-id or both --method and --path")

    methods = spec.get("paths", {}).get(path)
    if not methods:
        raise UsageError(f"Path not found in OpenAPI: {path}")

    operation = methods.get(method.lower())
    if not operation:
        raise UsageError(f"Method {method.upper()} not found for path: {path}")

    return method.upper(), path, operation


def resolve_path(template: str, path_params: Dict[str, str]) -> str:
    names = set(re.findall(r"\{([^{}]+)\}", template))
    missing = sorted(n for n in names if n not in path_params)
    if missing:
        raise UsageError(f"Missing path params for {template}: {', '.join(missing)}")

    resolved = template
    for name in names:
        resolved = resolved.replace("{" + name + "}", urllib.parse.quote(path_params[name], safe=""))
    return resolved


def load_saved_token(token_file: Path) -> Optional[Dict[str, Any]]:
    if not token_file.exists():
        return None
    with token_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_scope_string(scope_string: str) -> Set[str]:
    return set(scope_string.split()) if scope_string else set()


def extract_facility_token(saved: Dict[str, Any], facility: str) -> Optional[Dict[str, Any]]:
    facility_scope = FACILITY_CONFIG[facility]["scope"]
    for token_data in saved.get("other_tokens", []):
        if facility_scope in parse_scope_string(token_data.get("scope", "")):
            return token_data
    return None


def ensure_access_token(
    token_file: Path, min_ttl: int, script_dir: Path, facility: str
) -> str:
    cmd = [
        sys.executable,
        str(script_dir / "token_manager.py"),
        "--token-file",
        str(token_file),
        "ensure",
        "--facilities",
        facility,
        "--min-ttl",
        str(min_ttl),
        "--json",
        "--print-token",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(proc.stdout)
    token = (data.get("access_tokens") or {}).get(facility)
    if not token:
        raise UsageError(f"Token manager did not return an access token for {facility}")
    return token


def get_access_token(
    token_file: Path, min_ttl: int, ensure_token: bool, script_dir: Path, facility: str
) -> str:
    saved = load_saved_token(token_file)
    if saved:
        facility_token = extract_facility_token(saved, facility)
        expires_at = int((facility_token or {}).get("expires_at_seconds", 0) or 0)
        ttl = expires_at - int(time.time()) if expires_at else -1
        token = (facility_token or {}).get("access_token")
        if token and ttl >= min_ttl:
            return token

    if ensure_token:
        return ensure_access_token(token_file, min_ttl, script_dir, facility)

    raise UsageError(
        "No usable access token found. Run token_manager.py ensure or pass --ensure-token."
    )


def encode_multipart(field_name: str, file_path: Path) -> Tuple[bytes, str]:
    boundary = f"----iri-api-{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()

    parts = []  # type: List[bytes]
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        (
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{file_path.name}"\r\n'
        ).encode("utf-8")
    )
    parts.append(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
    parts.append(file_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def call_api(args: argparse.Namespace) -> int:
    spec = load_selected_openapi(args)
    method, openapi_path, operation = find_operation(
        spec, args.operation_id, args.method, args.path
    )

    path_params = parse_kv(args.path_param)
    query_params = parse_kv(args.query)
    resolved_path = resolve_path(openapi_path, path_params)

    query_string = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote, safe="/")
    url = f"{args.base_url.rstrip('/')}{resolved_path}"
    if query_string:
        url = f"{url}?{query_string}"

    operation_security = operation.get("security") or []
    needs_auth = (
        args.auth_mode == "always"
        or (args.auth_mode == "auto" and len(operation_security) > 0)
    )

    headers = {"Accept": "application/json", "User-Agent": "iri-api-client/1.0"}
    if needs_auth:
        if args.bearer_token:
            token = args.bearer_token
        else:
            token = get_access_token(
                token_file=args.token_file,
                min_ttl=args.min_ttl,
                ensure_token=args.ensure_token,
                script_dir=Path(__file__).resolve().parent,
                facility=args.facility,
            )
        headers["Authorization"] = f"Bearer {token}"

    data = None  # type: Optional[bytes]
    if args.upload_file:
        data, ctype = encode_multipart(args.upload_field, args.upload_file)
        headers["Content-Type"] = ctype
    elif args.json_file or args.json_body:
        if args.json_file and args.json_body:
            raise UsageError("Use only one of --json-file or --json-body")
        if args.json_file:
            payload = json.loads(args.json_file.read_text(encoding="utf-8"))
        else:
            payload = json.loads(args.json_body)
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            body = response.read()
            status = response.status
            out_headers = dict(response.headers)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
        out_headers = dict(exc.headers)
        print(f"HTTP {status}", file=sys.stderr)
        if body:
            try:
                print(json.dumps(json.loads(body.decode("utf-8")), indent=2), file=sys.stderr)
            except Exception:
                print(body.decode("utf-8", errors="replace"), file=sys.stderr)
        return 1

    if args.include_status:
        print(f"HTTP {status}")
        if args.include_headers:
            print(json.dumps(out_headers, indent=2))

    if args.output_file:
        args.output_file.write_bytes(body)
        print(f"Wrote response body to {args.output_file}")
        return 0

    if not body:
        return 0

    ctype = out_headers.get("Content-Type", "")
    if "application/json" in ctype:
        print(json.dumps(json.loads(body.decode("utf-8")), indent=2))
    else:
        print(body.decode("utf-8", errors="replace"))
    return 0


def list_ops(args: argparse.Namespace) -> int:
    spec = load_selected_openapi(args)
    rows = []  # type: List[Tuple[str, str, str, bool]]
    for api_path, methods in spec.get("paths", {}).items():
        for method_name, operation in methods.items():
            op_id = operation.get("operationId", "")
            secured = bool(operation.get("security"))
            rows.append((op_id, method_name.upper(), api_path, secured))

    rows.sort()
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "operationId": r[0],
                        "method": r[1],
                        "path": r[2],
                        "secured": r[3],
                    }
                    for r in rows
                ],
                indent=2,
            )
        )
        return 0

    for op_id, method, path, secured in rows:
        auth = "auth" if secured else "public"
        print(f"{op_id}\t{method}\t{path}\t{auth}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IRI API helper for OpenAPI-based calls")
    parser.add_argument(
        "--facility",
        choices=sorted(FACILITY_CONFIG),
        default=DEFAULT_FACILITY,
        help="Target facility API (default: nersc)",
    )
    parser.add_argument(
        "--openapi",
        type=Path,
        default=default_openapi_path(),
        help="Path to OpenAPI JSON (used when --openapi-url is not set)",
    )
    parser.add_argument(
        "--openapi-url",
        help="OpenAPI URL to fetch dynamically (defaults to the selected facility)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-operations", help="List OpenAPI operations")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON output")
    list_parser.set_defaults(func=list_ops)

    call_parser = subparsers.add_parser("call", help="Call an endpoint")
    call_parser.add_argument("--operation-id", help="OpenAPI operationId to call")
    call_parser.add_argument("--method", help="HTTP method (required with --path)")
    call_parser.add_argument("--path", help="OpenAPI path template (required with --method)")
    call_parser.add_argument(
        "--base-url",
        help="API base URL (defaults to the selected facility)",
    )
    call_parser.add_argument(
        "--path-param",
        action="append",
        help="Path parameter as key=value (repeatable)",
    )
    call_parser.add_argument(
        "--query",
        action="append",
        help="Query parameter as key=value (repeatable)",
    )
    call_parser.add_argument("--json-body", help="Inline JSON request body")
    call_parser.add_argument("--json-file", type=Path, help="Path to JSON request body")
    call_parser.add_argument("--upload-file", type=Path, help="File to upload as multipart")
    call_parser.add_argument(
        "--upload-field",
        default="file",
        help="Multipart field name for --upload-file (default: file)",
    )
    call_parser.add_argument(
        "--auth-mode",
        choices=["auto", "always", "never"],
        default="auto",
        help="Auth strategy. auto uses OpenAPI security metadata",
    )
    call_parser.add_argument(
        "--ensure-token",
        action="store_true",
        help="Auto-refresh/login via token_manager.py if token is missing or stale",
    )
    call_parser.add_argument(
        "--bearer-token",
        help="Raw bearer token string (overrides --token-file)",
    )
    call_parser.add_argument(
        "--token-file",
        type=Path,
        default=default_token_file(),
        help="Path to token JSON",
    )
    call_parser.add_argument(
        "--min-ttl",
        type=int,
        default=300,
        help="Minimum TTL in seconds before refreshing token",
    )
    call_parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds",
    )
    call_parser.add_argument(
        "--include-status",
        action="store_true",
        help="Print HTTP status before body",
    )
    call_parser.add_argument(
        "--include-headers",
        action="store_true",
        help="Print response headers (requires --include-status)",
    )
    call_parser.add_argument(
        "--output-file",
        type=Path,
        help="Write raw response body to file instead of stdout",
    )
    call_parser.set_defaults(func=call_api)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.openapi_url is None and args.openapi == default_openapi_path():
        args.openapi_url = resolve_openapi_url(args.facility)
    if getattr(args, "base_url", None) is None:
        args.base_url = resolve_base_url(args.facility)
    try:
        return args.func(args)
    except UsageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
