#!/usr/bin/env python3
"""Manage Globus tokens for authenticated IRI API calls."""

import argparse
import json
import os
import stat
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

CLIENT_ID = "fae5c579-490a-4d76-b6eb-d78f65caeb63"
RESOURCE_SERVER = "auth.globus.org"
FACILITY_SCOPE_MAP = {
    "nersc": {
        "scope": (
            "https://auth.globus.org/scopes/"
            "ed3e577d-f7f3-4639-b96e-ff5a8445d699/iri_api"
        ),
        "label": "NERSC IRI API",
        "validate_url": "https://api.iri.nersc.gov/api/v1/account/projects",
    },
    "alcf": {
        "scope": (
            "https://auth.globus.org/scopes/"
            "6be511f6-a071-471f-9bc0-02a0d0836723/filesystem"
        ),
        "label": "ALCF IRI API",
        "validate_url": "https://api.alcf.anl.gov/api/v1/account/projects",
    },
}
DEFAULT_FACILITIES = tuple(FACILITY_SCOPE_MAP)
REQUIRED_SCOPES = {
    "openid",
    "profile",
    "email",
    "urn:globus:auth:scope:auth.globus.org:view_identities",
}
SCOPE_LABELS = {
    config["scope"]: config["label"] for config in FACILITY_SCOPE_MAP.values()
}


def default_token_file() -> Path:
    return Path.home() / ".globus" / "auth_tokens.json"


def parse_scope_string(scope_string: str) -> Set[str]:
    return set(scope_string.split()) if scope_string else set()


def ensure_private_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)


def load_tokens(token_file: Path) -> Optional[Dict[str, Any]]:
    if not token_file.exists():
        return None
    with token_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_tokens(token_file: Path, tokens: Dict[str, Any]) -> None:
    ensure_private_parent_dir(token_file)
    tmp = token_file.with_suffix(".tmp")
    with os.fdopen(
        os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(tokens, f, indent=2)
    os.replace(tmp, token_file)
    os.chmod(token_file, stat.S_IRUSR | stat.S_IWUSR)


def get_refresh_token(stored_tokens: Dict[str, Any]) -> Optional[str]:
    if "refresh_token" in stored_tokens:
        return stored_tokens.get("refresh_token")

    auth_tokens = stored_tokens.get(RESOURCE_SERVER)
    if isinstance(auth_tokens, dict):
        return auth_tokens.get("refresh_token")

    return None


def get_selected_facilities(args: argparse.Namespace) -> List[str]:
    return list(dict.fromkeys(args.facilities))


def get_required_other_scopes(facilities: List[str]) -> Set[str]:
    return {FACILITY_SCOPE_MAP[facility]["scope"] for facility in facilities}


def get_requested_scopes(facilities: List[str]) -> Set[str]:
    return REQUIRED_SCOPES | get_required_other_scopes(facilities)


def get_token_for_scope(
    token_response_data: Dict[str, Any], scope: str, *, label: str = "auxiliary"
) -> Dict[str, Any]:
    for token_data in token_response_data.get("other_tokens", []):
        if scope in parse_scope_string(token_data.get("scope", "")):
            return token_data
    raise RuntimeError(f"Missing token for required {label} scope: {scope}")


def get_facility_token(token_response_data: Dict[str, Any], facility: str) -> Dict[str, Any]:
    scope = FACILITY_SCOPE_MAP[facility]["scope"]
    label = FACILITY_SCOPE_MAP[facility]["label"]
    return get_token_for_scope(token_response_data, scope, label=label)


def get_refresh_token_for_scope(stored_tokens: Dict[str, Any], scope: str) -> Optional[str]:
    try:
        return get_token_for_scope(
            stored_tokens,
            scope,
            label=SCOPE_LABELS.get(scope, "auxiliary"),
        ).get("refresh_token")
    except RuntimeError:
        return None


def replace_token_for_scope(
    token_response_data: Dict[str, Any], scope: str, refreshed_token_data: Dict[str, Any]
) -> Dict[str, Any]:
    merged = dict(token_response_data)
    other_tokens = list(merged.get("other_tokens", []))
    for index, token_data in enumerate(other_tokens):
        if scope in parse_scope_string(token_data.get("scope", "")):
            other_tokens[index] = refreshed_token_data
            break
    else:
        other_tokens.append(refreshed_token_data)
    merged["other_tokens"] = other_tokens
    return merged


def merge_auth_token_data(
    token_response_data: Dict[str, Any], refreshed_auth_data: Dict[str, Any]
) -> Dict[str, Any]:
    merged = dict(refreshed_auth_data)
    merged["other_tokens"] = list(token_response_data.get("other_tokens", []))
    return merged


def validate_auth_data(auth_data: Dict[str, Any], facilities: List[str]) -> Dict[str, Any]:
    if auth_data.get("resource_server") != RESOURCE_SERVER:
        raise RuntimeError(
            f"Missing token for required resource server: {RESOURCE_SERVER}"
        )

    granted = parse_scope_string(auth_data.get("scope", ""))
    missing = REQUIRED_SCOPES - granted
    if missing:
        raise RuntimeError(f"Missing required scopes: {sorted(missing)}")

    for facility in facilities:
        get_facility_token(auth_data, facility)

    return auth_data


def validate_iri_token(facility_token_data: Dict[str, Any], validate_url: str) -> Any:
    request = urllib.request.Request(
        validate_url,
        headers={
            "accept": "application/json",
            "Authorization": f"Bearer {facility_token_data['access_token']}",
            "User-Agent": "iri-api-client/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        details = body.strip() or exc.reason
        raise RuntimeError(
            f"IRI validation failed with HTTP {exc.code} from {validate_url}: {details}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"IRI validation request failed for {validate_url}: {exc.reason}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"IRI validation returned non-JSON data from {validate_url}"
        ) from exc

    if isinstance(data, dict):
        session_info = data.get("session_info")
        if isinstance(session_info, dict):
            authentications = session_info.get("authentications")
            if isinstance(authentications, dict) and not authentications:
                raise RuntimeError(
                    "IRI validation succeeded but session_info.authentications is empty. "
                    "Re-run with --force-login --prompt-login and use a Chrome incognito window."
                )

    return data


def token_status(tokens: Dict[str, Any], facilities: List[str]) -> Dict[str, Any]:
    now = int(time.time())
    auth_expires_at = int(tokens.get("expires_at_seconds", 0) or 0)
    auth_granted = parse_scope_string(tokens.get("scope", ""))
    auth_missing = sorted(REQUIRED_SCOPES - auth_granted)

    facilities_status = {}
    for facility in facilities:
        config = FACILITY_SCOPE_MAP[facility]
        token_data = None
        missing_scopes = [config["scope"]]
        expires_at = None
        granted_scopes = []
        resource_server = None
        has_access_token = False
        has_refresh_token = False
        ttl = None
        try:
            token_data = get_facility_token(tokens, facility)
            granted_set = parse_scope_string(token_data.get("scope", ""))
            missing_scopes = sorted({config["scope"]} - granted_set)
            expires_at = int(token_data.get("expires_at_seconds", 0) or 0) or None
            granted_scopes = sorted(granted_set)
            resource_server = token_data.get("resource_server")
            has_access_token = bool(token_data.get("access_token"))
            has_refresh_token = bool(token_data.get("refresh_token"))
            ttl = (expires_at - now) if expires_at else None
        except RuntimeError:
            token_data = None

        facilities_status[facility] = {
            "label": config["label"],
            "has_access_token": has_access_token,
            "has_refresh_token": has_refresh_token,
            "expires_at_seconds": expires_at,
            "ttl_seconds": ttl,
            "granted_scopes": granted_scopes,
            "missing_required_scopes": missing_scopes,
            "valid_for_required_scopes": not missing_scopes,
            "resource_server": resource_server,
            "token_found": token_data is not None,
            "validate_url": config["validate_url"],
        }

    return {
        "facilities": facilities_status,
        "auth_resource_server": tokens.get("resource_server"),
        "auth_has_access_token": bool(tokens.get("access_token")),
        "auth_has_refresh_token": bool(get_refresh_token(tokens)),
        "auth_expires_at_seconds": auth_expires_at or None,
        "auth_ttl_seconds": (auth_expires_at - now) if auth_expires_at else None,
        "auth_granted_scopes": sorted(auth_granted),
        "auth_missing_required_scopes": auth_missing,
        "auth_valid_for_required_scopes": not auth_missing,
    }


def print_status_human(token_file: Path, status: Dict[str, Any], facilities: List[str]) -> None:
    print(f"token_file: {token_file}")
    print(f"selected_facilities: {' '.join(facilities)}")
    for facility in facilities:
        facility_status = status["facilities"][facility]
        print(f"[{facility}] label: {facility_status['label']}")
        for key in [
            "has_access_token",
            "has_refresh_token",
            "expires_at_seconds",
            "ttl_seconds",
            "valid_for_required_scopes",
            "resource_server",
            "token_found",
        ]:
            print(f"[{facility}] {key}: {facility_status[key]}")
        print(f"[{facility}] granted_scopes: {' '.join(facility_status['granted_scopes'])}")
        if facility_status["missing_required_scopes"]:
            print(
                f"[{facility}] missing_required_scopes: "
                f"{' '.join(facility_status['missing_required_scopes'])}"
            )
    print("auth_granted_scopes:", " ".join(status["auth_granted_scopes"]))
    if status["auth_missing_required_scopes"]:
        print(
            "auth_missing_required_scopes:",
            " ".join(status["auth_missing_required_scopes"]),
        )


def interactive_login(facilities: List[str], prompt_login: bool = False) -> Dict[str, Any]:
    try:
        import globus_sdk
        from globus_sdk.exc import GlobusAPIError
    except ModuleNotFoundError as exc:
        raise RuntimeError("globus-sdk is required for login: pip install globus-sdk") from exc

    client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    client.oauth2_start_flow(
        requested_scopes=" ".join(sorted(get_requested_scopes(facilities))),
        refresh_tokens=True,
    )
    print("Open this URL, login, and consent:")
    prompt = "login" if prompt_login else globus_sdk.MISSING
    print(client.oauth2_get_authorize_url(prompt=prompt))
    code = input("\nEnter authorization code: ").strip()
    if not code:
        raise RuntimeError(
            "No authorization code entered. Re-run the script and paste the code "
            "shown by Globus after login."
        )
    try:
        token_response = client.oauth2_exchange_code_for_tokens(code)
    except GlobusAPIError as exc:
        if exc.http_status == 400:
            raise RuntimeError(
                "Authorization code exchange failed. The code was empty, invalid, "
                "expired, or already used. Re-run the script and complete the "
                "Globus login flow again."
            ) from exc
        raise RuntimeError(
            f"Authorization code exchange failed with HTTP {exc.http_status}. "
            "Re-run the script and try again."
        ) from exc
    return token_response.data


def refresh_tokens(refresh_token: str) -> Optional[Dict[str, Any]]:
    try:
        import globus_sdk
        from globus_sdk.exc import GlobusAPIError
    except ModuleNotFoundError as exc:
        raise RuntimeError("globus-sdk is required for refresh: pip install globus-sdk") from exc

    client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    try:
        token_response = client.oauth2_refresh_token(refresh_token)
        return token_response.data
    except GlobusAPIError as exc:
        print(f"Refresh failed ({exc.http_status}); switching to interactive login.")
        return None


def refresh_stored_tokens(
    stored_tokens: Dict[str, Any], facilities: List[str]
) -> Tuple[Optional[Dict[str, Any]], bool]:
    refreshed_tokens = dict(stored_tokens)
    used_refresh = False

    auth_refresh_token = get_refresh_token(stored_tokens)
    if auth_refresh_token:
        auth_data = refresh_tokens(auth_refresh_token)
        if auth_data is not None:
            refreshed_tokens = merge_auth_token_data(refreshed_tokens, auth_data)
            used_refresh = True

    for facility in facilities:
        scope = FACILITY_SCOPE_MAP[facility]["scope"]
        refresh_token = get_refresh_token_for_scope(stored_tokens, scope)
        if refresh_token:
            refreshed_token_data = refresh_tokens(refresh_token)
            if refreshed_token_data is not None:
                refreshed_tokens = replace_token_for_scope(
                    refreshed_tokens, scope, refreshed_token_data
                )
                used_refresh = True

        try:
            get_facility_token(refreshed_tokens, facility)
        except RuntimeError:
            return None, used_refresh

    if used_refresh:
        return refreshed_tokens, True

    return None, False


def cmd_status(args: argparse.Namespace) -> int:
    facilities = get_selected_facilities(args)
    tokens = load_tokens(args.token_file)
    if tokens is None:
        if args.json:
            print(
                json.dumps(
                    {
                        "token_file": str(args.token_file),
                        "exists": False,
                        "selected_facilities": facilities,
                        "status": None,
                    },
                    indent=2,
                )
            )
        else:
            print(f"token_file: {args.token_file}")
            print("exists: false")
            print(f"selected_facilities: {' '.join(facilities)}")
        return 1

    status = token_status(tokens, facilities)
    if args.json:
        print(
            json.dumps(
                {
                    "token_file": str(args.token_file),
                    "exists": True,
                    "selected_facilities": facilities,
                    "status": status,
                },
                indent=2,
            )
        )
    else:
        print_status_human(args.token_file, status, facilities)
    return 0


def cmd_ensure(args: argparse.Namespace) -> int:
    if args.force_login and args.refresh_only:
        raise RuntimeError("Choose only one of --force-login or --refresh-only")

    facilities = get_selected_facilities(args)
    if args.validate_iri and args.validate_facility not in facilities:
        raise RuntimeError(
            f"--validate-iri requires including the '{args.validate_facility}' facility"
        )

    tokens = None if args.force_login else load_tokens(args.token_file)
    auth_data = None  # type: Optional[Dict[str, Any]]
    used_refresh = False

    if tokens:
        status = token_status(tokens, facilities)
        facility_valid = all(
            status["facilities"][facility]["has_access_token"]
            and status["facilities"][facility]["valid_for_required_scopes"]
            and status["facilities"][facility]["ttl_seconds"] is not None
            and status["facilities"][facility]["ttl_seconds"] >= args.min_ttl
            for facility in facilities
        )
        if facility_valid:
            auth_data = tokens
        else:
            auth_data, used_refresh = refresh_stored_tokens(tokens, facilities)

    if auth_data is None:
        if args.refresh_only:
            facility_labels = ", ".join(
                FACILITY_SCOPE_MAP[facility]["label"] for facility in facilities
            )
            raise RuntimeError(
                "Refresh-only mode failed. No usable saved refresh token was found "
                f"or token refresh did not return all required tokens for: {facility_labels}."
            )
        auth_data = interactive_login(facilities, prompt_login=args.prompt_login)

    try:
        validate_auth_data(auth_data, facilities)
    except RuntimeError as exc:
        if used_refresh and "Missing token for required " in str(exc):
            print(
                "Refreshed tokens did not include all required facility tokens; "
                "switching to interactive login."
            )
            auth_data = interactive_login(facilities, prompt_login=args.prompt_login)
            validate_auth_data(auth_data, facilities)
        else:
            raise

    save_tokens(args.token_file, auth_data)

    validation_data = None  # type: Any
    validation_url = None
    if args.validate_iri:
        validate_token_data = get_facility_token(auth_data, args.validate_facility)
        validation_url = (
            args.iri_validate_url
            or FACILITY_SCOPE_MAP[args.validate_facility]["validate_url"]
        )
        validation_data = validate_iri_token(validate_token_data, validation_url)

    status = token_status(auth_data, facilities)
    tokens_by_facility = {
        facility: get_facility_token(auth_data, facility) for facility in facilities
    }
    if args.json:
        output = {
            "token_file": str(args.token_file),
            "selected_facilities": facilities,
            "status": status,
            "access_tokens": {
                facility: (
                    tokens_by_facility[facility].get("access_token")
                    if args.print_token
                    else None
                )
                for facility in facilities
            },
            "iri_validate_facility": args.validate_facility if args.validate_iri else None,
            "iri_validate_url": validation_url,
            "iri_validation": validation_data if args.validate_iri else None,
        }
        print(json.dumps(output, indent=2))
    else:
        if args.validate_iri:
            print(
                f"IRI validation succeeded for {FACILITY_SCOPE_MAP[args.validate_facility]['label']} "
                f"against {validation_url}"
            )
            if isinstance(validation_data, dict):
                session_info = validation_data.get("session_info")
                if isinstance(session_info, dict):
                    session_id = session_info.get("session_id")
                    if session_id:
                        print(f"IRI session_id: {session_id}")
            elif isinstance(validation_data, list):
                print(f"IRI validation response items: {len(validation_data)}")

        print(f"Saved token data to {args.token_file}")
        print(f"Selected facilities: {', '.join(facilities)}")
        print(f"Granted Globus Auth scopes: {auth_data.get('scope', '')}")
        for facility in facilities:
            label = FACILITY_SCOPE_MAP[facility]["label"]
            token_data = tokens_by_facility[facility]
            expires_at = token_data.get("expires_at_seconds")
            if expires_at:
                ttl = int(expires_at - time.time())
                print(f"{label} access token valid for ~{max(ttl, 0)} seconds.")
            print(f"{label} token resource server: {token_data.get('resource_server')}")
            print(f"{label} token scopes: {token_data.get('scope', '')}")

        if args.print_token:
            for facility in facilities:
                label = FACILITY_SCOPE_MAP[facility]["label"]
                print(f"\n{label} access token:")
                print(tokens_by_facility[facility]["access_token"])
        else:
            print(
                "Selected facility access tokens not printed "
                "(use --print-token to display them)."
            )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect, refresh, validate, or obtain Globus tokens for IRI APIs."
    )
    parser.add_argument(
        "--token-file",
        type=Path,
        default=default_token_file(),
        help="Path to token JSON (default: ~/.globus/auth_tokens.json)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Inspect token file state")
    status_parser.add_argument("--json", action="store_true", help="Emit JSON output")
    status_parser.add_argument(
        "--facilities",
        nargs="+",
        choices=sorted(FACILITY_SCOPE_MAP),
        default=list(DEFAULT_FACILITIES),
        help=(
            "Facility tokens to inspect "
            f"(default: {' '.join(DEFAULT_FACILITIES)})"
        ),
    )
    status_parser.set_defaults(func=cmd_status)

    ensure_parser = subparsers.add_parser(
        "ensure",
        help="Ensure usable facility IRI tokens exist (reuse, refresh, or interactive login)",
    )
    ensure_parser.add_argument(
        "--min-ttl",
        type=int,
        default=300,
        help="Minimum TTL in seconds for reusing existing facility access tokens",
    )
    ensure_parser.add_argument(
        "--force-login",
        action="store_true",
        help="Skip reuse/refresh and force interactive login",
    )
    ensure_parser.add_argument(
        "--refresh-only",
        action="store_true",
        help="Refresh saved tokens only; do not fall back to interactive login",
    )
    ensure_parser.add_argument(
        "--prompt-login",
        action="store_true",
        help="Add prompt=login to the authorize URL to force IdP re-authentication",
    )
    ensure_parser.add_argument(
        "--validate-iri",
        action="store_true",
        help="Validate a selected facility token by calling an IRI endpoint",
    )
    ensure_parser.add_argument(
        "--validate-facility",
        choices=sorted(FACILITY_SCOPE_MAP),
        default="nersc",
        help="Facility token to validate when using --validate-iri (default: nersc)",
    )
    ensure_parser.add_argument(
        "--iri-validate-url",
        default=None,
        help="IRI endpoint used by --validate-iri (defaults to the selected facility)",
    )
    ensure_parser.add_argument(
        "--print-token",
        action="store_true",
        help="Include selected facility access tokens in output",
    )
    ensure_parser.add_argument(
        "--facilities",
        nargs="+",
        choices=sorted(FACILITY_SCOPE_MAP),
        default=list(DEFAULT_FACILITIES),
        help=(
            "Facility tokens to request and manage "
            f"(default: {' '.join(DEFAULT_FACILITIES)})"
        ),
    )
    ensure_parser.add_argument("--json", action="store_true", help="Emit JSON output")
    ensure_parser.set_defaults(func=cmd_ensure)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
