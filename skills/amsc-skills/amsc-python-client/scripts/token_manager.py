#!/usr/bin/env python3
"""Manage AmSC authentication tokens for frictionless API access.

Provides status checks, token validation, and guided login flows
so Claude can ensure auth is ready before running operations.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path


CREDENTIALS_FILE = Path.home() / ".amsc" / "credentials.json"
CONFIG_FILE = Path.home() / ".amsc" / "config.yaml"

# Facility Globus configs — self-contained, no dependency on built-in pkg data
FACILITY_CONFIGS = {
    "alcf": {
        "globus_client_id": "8b84fc2d-49e9-49ea-b54d-b3a29a70cf31",
        "globus_scope": (
            "https://auth.globus.org/scopes/"
            "6be511f6-a071-471f-9bc0-02a0d0836723/filesystem"
        ),
        "globus_resource_server": "",
        "globus_auth_params": {
            "session_required_policies": "a128e981-c9a5-417a-97ab-8571c9831bff",
        },
        "base_url": "https://api.alcf.anl.gov",
        "display_name": "Argonne Leadership Computing Facility",
    },
    "nersc": {
        "globus_client_id": "fae5c579-490a-4d76-b6eb-d78f65caeb63",
        "globus_scope": (
            "openid profile email "
            "urn:globus:auth:scope:auth.globus.org:view_identities "
            "https://auth.globus.org/scopes/"
            "ed3e577d-f7f3-4639-b96e-ff5a8445d699/iri_api"
        ),
        "globus_resource_server": "ed3e577d-f7f3-4639-b96e-ff5a8445d699",
        "globus_auth_params": {},
        "base_url": "https://api.iri.nersc.gov",
        "display_name": "National Energy Research Scientific Computing Center",
    },
}

# Cache key = globus_{client_id}
FACILITY_CACHE_KEYS = {
    name: f"globus_{cfg['globus_client_id']}"
    for name, cfg in FACILITY_CONFIGS.items()
}

# AmSC gateway default
AMSC_GLOBUS_CLIENT_ID = "e4f48665-38b5-4833-a89e-849c71f5b3e3"


def check_install():
    """Check if amsc-client is importable."""
    try:
        import amsc_client  # noqa: F401
        return True
    except ImportError:
        return False


def load_credentials():
    """Load cached credentials from disk."""
    if not CREDENTIALS_FILE.exists():
        return {}
    try:
        with open(CREDENTIALS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def token_ttl(entry):
    """Return seconds until token expires, or None if unknown."""
    expires_at = entry.get("expires_at")
    if expires_at:
        return int(expires_at - time.time())
    return None


def token_entry_status(entry):
    """Summarize a single cached token entry."""
    if not entry:
        return {"cached": False}
    ttl = token_ttl(entry)
    return {
        "cached": True,
        "has_access_token": bool(entry.get("access_token")),
        "has_refresh_token": bool(entry.get("refresh_token")),
        "expires_at": entry.get("expires_at"),
        "ttl_seconds": ttl,
        "expired": ttl is not None and ttl <= 0,
        "usable": ttl is not None and ttl > 60,
    }


def cmd_status(args):
    """Show current auth state for AmSC and facilities."""
    installed = check_install()
    creds = load_credentials()

    result = {
        "amsc_client_installed": installed,
        "credentials_file": str(CREDENTIALS_FILE),
        "credentials_file_exists": CREDENTIALS_FILE.exists(),
        "config_file_exists": CONFIG_FILE.exists(),
        "cached_keys": list(creds.keys()),
        "facilities": {},
    }

    # Check each known facility
    for facility, cache_key in FACILITY_CACHE_KEYS.items():
        entry = creds.get(cache_key)
        result["facilities"][facility] = token_entry_status(entry)

    # Check AmSC gateway token
    amsc_key = f"globus_{AMSC_GLOBUS_CLIENT_ID}"
    amsc_entry = creds.get(amsc_key)
    result["amsc_gateway"] = token_entry_status(amsc_entry)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"amsc-client installed: {installed}")
        print(f"credentials file: {CREDENTIALS_FILE}")
        print(f"  exists: {CREDENTIALS_FILE.exists()}")
        print(f"config file: {CONFIG_FILE}")
        print(f"  exists: {CONFIG_FILE.exists()}")
        print()
        for name, status in result["facilities"].items():
            print(f"facility/{name}:")
            if not status["cached"]:
                print("  cached: false (login required)")
            else:
                ttl = status["ttl_seconds"]
                if ttl is not None:
                    print(f"  ttl: {ttl}s ({'EXPIRED' if ttl <= 0 else 'valid'})")
                print(f"  has_refresh_token: {status['has_refresh_token']}")
        gw = result["amsc_gateway"]
        print("amsc_gateway:")
        if not gw["cached"]:
            print("  cached: false (login required)")
        else:
            ttl = gw.get("ttl_seconds")
            if ttl is not None:
                print(f"  ttl: {ttl}s ({'EXPIRED' if ttl <= 0 else 'valid'})")

    return 0


def cmd_ensure(args):
    """Ensure a valid token exists for the target scope."""
    if not check_install():
        print(
            "Error: amsc-client not installed. Run:\n"
            "  .claude/skills/amsc-python-client/scripts/install.sh",
            file=sys.stderr,
        )
        return 1

    target = args.target  # "alcf", "nersc", or "amsc"
    min_ttl = args.min_ttl

    # Check cached token first
    creds = load_credentials()
    if target in FACILITY_CACHE_KEYS:
        cache_key = FACILITY_CACHE_KEYS[target]
    else:
        cache_key = f"globus_{AMSC_GLOBUS_CLIENT_ID}"

    entry = creds.get(cache_key)
    status = token_entry_status(entry)

    # If token is usable and has enough TTL, skip login
    if status.get("usable") and (status.get("ttl_seconds") or 0) >= min_ttl:
        if not args.force_login:
            msg = {
                "action": "reused",
                "target": target,
                "ttl_seconds": status["ttl_seconds"],
            }
            if args.json:
                print(json.dumps(msg, indent=2))
            else:
                print(
                    f"Token for {target} is valid "
                    f"({status['ttl_seconds']}s remaining). No action needed."
                )
            return 0

    # Need to login or refresh — use the SDK
    if target in ("alcf", "nersc"):
        return _ensure_facility(target, args)
    else:
        return _ensure_amsc(args)


def _ensure_facility(facility_name, args):
    """Ensure facility auth via amsc-client SDK."""
    from amsc_client import Client

    cfg = FACILITY_CONFIGS[facility_name]
    client = Client(token="placeholder")

    # Always register explicitly — don't rely on built-in config
    # which may not exist in older amsc-client versions
    client.register_facility(
        name=facility_name,
        base_url=cfg["base_url"],
        display_name=cfg["display_name"],
        auth_method="globus",
        globus_client_id=cfg["globus_client_id"],
        globus_scope=cfg["globus_scope"],
        globus_resource_server=cfg["globus_resource_server"],
        globus_auth_params=cfg["globus_auth_params"],
    )
    fac = client.facility(facility_name)

    if args.force_login:
        client._token_registry.invalidate_token(facility_name)

    # Trigger login by requesting a token
    try:
        token = client._token_registry.get_token(facility_name)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Validate by calling a public endpoint
    if args.validate:
        try:
            info = fac.info()
            facility_display = getattr(info, "name", facility_name)
        except Exception as e:
            print(f"Warning: validation call failed: {e}", file=sys.stderr)
            facility_display = facility_name
    else:
        facility_display = facility_name

    # Re-read cached status
    creds = load_credentials()
    cache_key = FACILITY_CACHE_KEYS.get(facility_name, "")
    entry = creds.get(cache_key)
    status = token_entry_status(entry)

    msg = {
        "action": "authenticated",
        "target": facility_name,
        "facility": facility_display,
        "ttl_seconds": status.get("ttl_seconds"),
        "validated": args.validate,
    }

    if args.json:
        print(json.dumps(msg, indent=2))
    else:
        ttl = status.get("ttl_seconds", "unknown")
        print(f"Authenticated to {facility_name} ({ttl}s remaining)")
        if args.validate:
            print(f"Validation: OK (facility={facility_display})")

    return 0


def _ensure_amsc(args):
    """Ensure AmSC gateway auth."""
    from amsc_client import Client

    app_id = AMSC_GLOBUS_CLIENT_ID
    client = Client(
        base_url="https://api.american-science-cloud.org/api/current",
        auth_method="globus",
        globus_client_id=app_id,
        requested_scopes=f"openid profile email https://auth.globus.org/scopes/{app_id}/amsc_test",
        resource_server=app_id,
        use_id_token=True,
    )

    if args.force_login:
        client._authenticator.invalidate()

    try:
        token = client._authenticator.get_token()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    creds = load_credentials()
    cache_key = f"globus_{app_id}"
    entry = creds.get(cache_key)
    status = token_entry_status(entry)

    msg = {
        "action": "authenticated",
        "target": "amsc",
        "ttl_seconds": status.get("ttl_seconds"),
    }

    if args.json:
        print(json.dumps(msg, indent=2))
    else:
        ttl = status.get("ttl_seconds", "unknown")
        print(f"Authenticated to AmSC gateway ({ttl}s remaining)")

    return 0


def cmd_clear(args):
    """Clear cached tokens to force re-authentication."""
    target = args.target

    if target == "all":
        if CREDENTIALS_FILE.exists():
            CREDENTIALS_FILE.unlink()
            print(f"Removed {CREDENTIALS_FILE}")
        else:
            print("No cached credentials found.")
        return 0

    creds = load_credentials()
    if not creds:
        print("No cached credentials found.")
        return 0

    if target in FACILITY_CACHE_KEYS:
        key = FACILITY_CACHE_KEYS[target]
    else:
        key = f"globus_{AMSC_GLOBUS_CLIENT_ID}"

    if key in creds:
        del creds[key]
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(creds, f, indent=2)
        os.chmod(CREDENTIALS_FILE, 0o600)
        print(f"Cleared cached token for {target}")
    else:
        print(f"No cached token found for {target}")

    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Manage AmSC authentication tokens"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    sp = subparsers.add_parser("status", help="Show auth state")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_status)

    # ensure
    sp = subparsers.add_parser(
        "ensure", help="Ensure valid token (login/refresh if needed)"
    )
    sp.add_argument(
        "target",
        choices=["alcf", "nersc", "amsc"],
        help="Auth target: alcf, nersc, or amsc (gateway)",
    )
    sp.add_argument("--min-ttl", type=int, default=300)
    sp.add_argument("--force-login", action="store_true")
    sp.add_argument("--validate", action="store_true",
                    help="Validate token against API")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_ensure)

    # clear
    sp = subparsers.add_parser("clear", help="Clear cached tokens")
    sp.add_argument(
        "target",
        choices=["alcf", "nersc", "amsc", "all"],
        help="Which tokens to clear",
    )
    sp.set_defaults(func=cmd_clear)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
