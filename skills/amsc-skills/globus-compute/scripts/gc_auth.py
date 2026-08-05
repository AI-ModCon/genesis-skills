#!/usr/bin/env python3
"""Manage Globus tokens for Globus Compute using globus_sdk."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import globus_sdk
    from globus_sdk.token_storage import SQLiteTokenStorage
except ImportError:
    print("Error: globus_sdk >= 4 is required. pip install -U 'globus-sdk>=4'", file=sys.stderr)
    sys.exit(1)

# Globus Compute native app client ID (public)
GC_NATIVE_CLIENT_ID = "4cf29807-cf21-49ec-9443-ff9a3fb9f81c"

COMPUTE_SCOPE = "https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all"
OPENID_SCOPE = "openid"
COMPUTE_RESOURCE_SERVER = "funcx_service"

# Match globus-compute-sdk's token storage location and namespace
# so login via gc_auth.py works for gc_run.py (SDK) and vice versa
DEFAULT_TOKEN_DB = Path.home() / ".globus_compute" / "storage.db"
NAMESPACE = "user/production"


def get_token_storage(db_path: Path) -> SQLiteTokenStorage:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteTokenStorage(filepath=db_path, namespace=NAMESPACE)


def get_authorizer(db_path: Path) -> globus_sdk.RefreshTokenAuthorizer:
    """Return a valid RefreshTokenAuthorizer for Globus Compute."""
    storage = get_token_storage(db_path)
    token_data = storage.get_token_data(COMPUTE_RESOURCE_SERVER)
    if token_data is None:
        raise RuntimeError("Not logged in. Run: python3 gc_auth.py login")

    auth_client = globus_sdk.NativeAppAuthClient(GC_NATIVE_CLIENT_ID)
    return globus_sdk.RefreshTokenAuthorizer(
        token_data.refresh_token,
        auth_client,
        access_token=token_data.access_token,
        expires_at=token_data.expires_at_seconds,
        on_refresh=lambda r: storage.store_token_response(r),
    )


def do_login(db_path: Path) -> None:
    """Run native app device code flow and save tokens."""
    auth_client = globus_sdk.NativeAppAuthClient(GC_NATIVE_CLIENT_ID)
    auth_client.oauth2_start_flow(
        requested_scopes=[COMPUTE_SCOPE, OPENID_SCOPE],
        refresh_tokens=True,
    )
    auth_url = auth_client.oauth2_get_authorize_url()

    print(f"\nTo authenticate, visit:\n  {auth_url}\n")
    auth_code = input("Enter the auth code: ").strip()

    token_response = auth_client.oauth2_exchange_code_for_tokens(auth_code)
    storage = get_token_storage(db_path)
    storage.store_token_response(token_response)
    print(f"Login successful. Tokens saved to {db_path}")


def cmd_status(args: argparse.Namespace) -> int:
    storage = get_token_storage(args.token_db)
    token_data = storage.get_token_data(COMPUTE_RESOURCE_SERVER)

    if token_data is None:
        info = {"status": "not_logged_in", "token_db": str(args.token_db)}
        if args.json:
            print(json.dumps(info))
        else:
            print("Not logged in. Run: python3 gc_auth.py login")
        return 1

    now = time.time()
    exp = token_data.expires_at_seconds or 0
    ttl = max(0, int(exp - now))
    status = "valid" if ttl > 60 else ("expired" if ttl == 0 else "expiring_soon")

    info = {
        "status": status,
        "ttl_seconds": ttl,
        "resource_server": COMPUTE_RESOURCE_SERVER,
        "token_db": str(args.token_db),
    }
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"Status:   {status}")
        print(f"TTL:      {ttl}s")
        print(f"Token DB: {args.token_db}")
    return 0 if status == "valid" else 1


def cmd_login(args: argparse.Namespace) -> int:
    if not args.force:
        storage = get_token_storage(args.token_db)
        if storage.get_token_data(COMPUTE_RESOURCE_SERVER) is not None:
            # Try refreshing first
            try:
                auth = get_authorizer(args.token_db)
                auth.ensure_valid_token()
                print("Already logged in and token is valid.")
                print("Use --force to re-authenticate.")
                return 0
            except Exception:
                pass
    try:
        do_login(args.token_db)
        return 0
    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        return 1


def cmd_logout(args: argparse.Namespace) -> int:
    if args.token_db.exists():
        args.token_db.unlink()
        print(f"Removed {args.token_db}")
    else:
        print("Not logged in.")
    return 0


def cmd_token(args: argparse.Namespace) -> int:
    """Print a valid access token (auto-refreshes via globus_sdk)."""
    try:
        auth = get_authorizer(args.token_db)
        auth.ensure_valid_token()
        print(auth.get_authorization_header().split(" ", 1)[1])
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Globus Compute auth manager (uses globus_sdk)")
    parser.add_argument(
        "--token-db",
        type=Path,
        default=DEFAULT_TOKEN_DB,
        help=f"SQLite token database (default: {DEFAULT_TOKEN_DB})",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable output")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show current token status")

    login_p = sub.add_parser("login", help="Authenticate with Globus")
    login_p.add_argument("--force", action="store_true", help="Force new login even if token valid")

    sub.add_parser("logout", help="Remove saved tokens")
    sub.add_parser("token", help="Print valid access token (auto-refreshes)")

    args = parser.parse_args()
    dispatch = {
        "status": cmd_status,
        "login": cmd_login,
        "logout": cmd_logout,
        "token": cmd_token,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
