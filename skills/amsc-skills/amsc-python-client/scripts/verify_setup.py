#!/usr/bin/env python3
"""Verify amsc-client installation and configuration."""

import sys


def check_import():
    """Check amsc_client is importable."""
    try:
        import amsc_client  # noqa: F401
        print("[OK] amsc_client importable")
        return True
    except ImportError as e:
        print(f"[FAIL] Cannot import amsc_client: {e}")
        print("  Run: .claude/skills/amsc-python-client/scripts/install.sh")
        return False


def check_version():
    """Print installed version."""
    try:
        from amsc_client._version import __version__
        print(f"[OK] Version: {__version__}")
    except Exception:
        print("[WARN] Could not determine version")


def check_config():
    """Check if config file exists."""
    from pathlib import Path
    config_path = Path.home() / ".amsc" / "config.yaml"
    if config_path.exists():
        print(f"[OK] Config found: {config_path}")
    else:
        print(f"[INFO] No config file at {config_path} (optional — can use env vars or constructor args)")


def check_tokens():
    """Check if cached tokens exist."""
    from pathlib import Path
    credentials_path = Path.home() / ".amsc" / "credentials.json"
    if credentials_path.exists():
        print(f"[OK] Cached credentials found: {credentials_path}")
    else:
        print("[INFO] No cached tokens (will authenticate on first API call)")


def check_globus():
    """Check if globus-sdk is available."""
    try:
        import globus_sdk  # noqa: F401
        print("[OK] globus-sdk available")
    except ImportError:
        print("[INFO] globus-sdk not installed (install with: pip install amsc-client[globus])")


def check_client_init():
    """Try to instantiate client (no auth call)."""
    try:
        from amsc_client import Client
        client = Client(token="test-token-placeholder")
        assert client.catalog is not None
        print("[OK] Client instantiation works (no API call made)")
    except Exception as e:
        print(f"[WARN] Client instantiation issue: {e}")


def main():
    print("=== AmSC Python Client Setup Verification ===\n")

    if not check_import():
        sys.exit(1)

    check_version()
    check_config()
    check_tokens()
    check_globus()
    check_client_init()

    print("\n=== Verification complete ===")


if __name__ == "__main__":
    main()
