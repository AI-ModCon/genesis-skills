#!/usr/bin/env python3
"""Submit and manage Globus Compute jobs using globus-compute-sdk.

Uses the official SDK with user_endpoint_config for template-capable
endpoints. Pass NERSC_ACCOUNT, OPTIONS, COMMAND at submit time.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    from globus_compute_sdk import Client, Executor
except ImportError:
    print(
        "Error: globus-compute-sdk required.\n"
        "  uv pip install globus-compute-sdk\n"
        "  # or: pip install globus-compute-sdk",
        file=sys.stderr,
    )
    sys.exit(1)

TUTORIAL_ENDPOINT = "4b116d3c-1703-4f8f-9f6f-39921e5864df"
CONFIG_PATH = Path.home() / ".globus_compute" / "gc_skill_config.json"


# ---------------------------------------------------------------------------
# Config management
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def _resolve_endpoint(explicit: str | None) -> str:
    """Resolve endpoint ID: explicit arg > config default > tutorial."""
    if explicit:
        return explicit
    config = _load_config()
    return config.get("default_endpoint", TUTORIAL_ENDPOINT)


def _build_user_config(args: argparse.Namespace) -> dict | None:
    """Build user_endpoint_config from CLI flags."""
    config = {}
    if getattr(args, "account", None):
        config["NERSC_ACCOUNT"] = args.account
    if getattr(args, "options", None):
        # Convert literal \n to actual newlines for SBATCH directives
        config["OPTIONS"] = args.options.replace("\\n", "\n")
    if getattr(args, "worker_init", None):
        config["COMMAND"] = args.worker_init
    return config if config else None


def _get_client() -> Client:
    """Get authenticated Globus Compute client."""
    return Client()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_config(args: argparse.Namespace) -> int:
    """View or update skill configuration."""
    config = _load_config()

    if args.config_action == "show":
        if not config:
            print("No config set. Using defaults.")
            print(f"  endpoint: {TUTORIAL_ENDPOINT} (tutorial)")
            return 0
        print(json.dumps(config, indent=2))
        return 0

    elif args.config_action == "set-endpoint":
        config["default_endpoint"] = args.endpoint_id
        if args.name:
            config["endpoint_name"] = args.name
        _save_config(config)
        name = args.name or config.get("endpoint_name", "")
        label = f" ({name})" if name else ""
        print(f"Default endpoint set: {args.endpoint_id}{label}")
        print(f"Config saved: {CONFIG_PATH}")
        return 0

    elif args.config_action == "reset":
        if CONFIG_PATH.exists():
            CONFIG_PATH.unlink()
            print("Config reset to defaults.")
        else:
            print("No config to reset.")
        return 0

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Check auth and endpoint status."""
    gcc = _get_client()
    ep_id = _resolve_endpoint(getattr(args, "endpoint_id", None))
    is_tutorial = ep_id == TUTORIAL_ENDPOINT
    config = _load_config()
    ep_name = config.get("endpoint_name", "tutorial" if is_tutorial else "")

    try:
        ep = gcc.get_endpoint_status(ep_id)
        if args.json:
            print(json.dumps({
                "endpoint_id": ep_id,
                "endpoint_name": ep_name,
                "status": ep,
            }, indent=2))
        else:
            label = f" ({ep_name})" if ep_name else ""
            print(f"Endpoint: {ep_id}{label}")
            print(f"Status:   {ep}")
            print("Auth:     OK")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list_endpoints(args: argparse.Namespace) -> int:
    """List endpoints visible to this user."""
    gcc = _get_client()
    config = _load_config()
    default_ep = config.get("default_endpoint", "")

    try:
        endpoints = gcc.get_endpoints()
        if not endpoints:
            print("No endpoints found. Use the tutorial endpoint for testing:")
            print(f"  {TUTORIAL_ENDPOINT}")
            return 0
        if args.json:
            print(json.dumps(endpoints, indent=2))
        else:
            print(f"{'ID':<38}  {'NAME':<25}  DEFAULT")
            print("-" * 75)
            for ep in endpoints:
                eid = ep.get("uuid", ep.get("id", "?"))
                name = ep.get("display_name") or ep.get("name", "?")
                marker = " *" if eid == default_ep else ""
                print(f"{eid:<38}  {name:<25}{marker}")
        return 0
    except Exception as e:
        print(f"Error listing endpoints: {e}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Register and run a function from a .py file."""
    ep_id = _resolve_endpoint(getattr(args, "endpoint_id", None))
    func_path = Path(args.function_file)
    if not func_path.exists():
        print(f"Error: {func_path} not found", file=sys.stderr)
        return 1

    code = func_path.read_text()
    namespace: dict[str, Any] = {}
    exec(compile(code, func_path, "exec"), namespace)  # noqa: S102

    func_name = args.function_name or next(
        (k for k, v in namespace.items() if callable(v) and not k.startswith("_")),
        None,
    )
    if not func_name or func_name not in namespace:
        print(f"Error: no callable found in {func_path}", file=sys.stderr)
        return 1

    func = namespace[func_name]
    task_args = json.loads(args.args) if args.args else []
    task_kwargs = json.loads(args.kwargs) if args.kwargs else {}
    user_config = _build_user_config(args)

    print(f"Submitting {func_name}({task_args}, {task_kwargs}) -> {ep_id}...")
    if user_config:
        print(f"user_endpoint_config: {json.dumps(user_config, indent=2)}")

    executor_kwargs: dict[str, Any] = {"endpoint_id": ep_id}
    if user_config:
        executor_kwargs["user_endpoint_config"] = user_config

    with Executor(**executor_kwargs) as ex:
        future = ex.submit(func, *task_args, **task_kwargs)
        print("Waiting for result...")
        try:
            result = future.result(timeout=args.timeout)
            if args.json:
                print(json.dumps({"status": "success", "result": str(result)}))
            else:
                print(f"SUCCESS: {func_name}({task_args}) = {result}")
            return 0
        except TimeoutError:
            if args.timeout:
                print(f"Timeout after {args.timeout}s", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"FAILED: {e}", file=sys.stderr)
            return 1


def cmd_sample(args: argparse.Namespace) -> int:
    """Run get_hostname() end-to-end on an endpoint."""
    ep_id = _resolve_endpoint(getattr(args, "endpoint_id", None))
    user_config = _build_user_config(args)

    def get_hostname():
        import socket
        return socket.gethostname()

    print(f"Running get_hostname() on endpoint {ep_id}...")
    if user_config:
        print(f"user_endpoint_config: {json.dumps(user_config, indent=2)}")

    executor_kwargs: dict[str, Any] = {"endpoint_id": ep_id}
    if user_config:
        executor_kwargs["user_endpoint_config"] = user_config

    with Executor(**executor_kwargs) as ex:
        future = ex.submit(get_hostname)
        print("Waiting for result...")
        try:
            result = future.result(timeout=args.timeout)
            if args.json:
                print(json.dumps({"status": "success", "hostname": result}))
            else:
                print(f"SUCCESS: hostname = {result}")
            return 0
        except TimeoutError:
            if args.timeout:
                print(f"Timeout after {args.timeout}s", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"FAILED: {e}", file=sys.stderr)
            return 1


def cmd_submit(args: argparse.Namespace) -> int:
    """Submit a previously registered function by UUID."""
    ep_id = _resolve_endpoint(getattr(args, "endpoint_id", None))
    func_id = args.function_id
    task_args = json.loads(args.args) if args.args else []
    task_kwargs = json.loads(args.kwargs) if args.kwargs else {}

    gcc = _get_client()
    print(f"Submitting {func_id} -> {ep_id}...")
    task_id = gcc.run(func_id, endpoint_id=ep_id, args=task_args, kwargs=task_kwargs)
    print(f"Task UUID: {task_id}")

    if args.wait:
        return _poll(gcc, task_id, args.timeout, args.poll, args.json)
    if args.json:
        print(json.dumps({"task_id": task_id}))
    return 0


def cmd_result(args: argparse.Namespace) -> int:
    """Get result of a previously submitted task."""
    gcc = _get_client()
    return _poll(gcc, args.task_id, args.timeout, args.poll, args.json)


def _poll(gcc: Client, task_id: str, timeout: int, poll: float, as_json: bool) -> int:
    """Poll for task completion."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = gcc.get_result(task_id)
            if as_json:
                print(json.dumps({"status": "success", "result": str(result)}))
            else:
                print(f"SUCCESS: {result}")
            return 0
        except Exception as e:
            err = str(e)
            if "pending" in err.lower() or "waiting" in err.lower() or "running" in err.lower():
                print("  [waiting] ...", end="\r")
                time.sleep(poll)
            else:
                if as_json:
                    print(json.dumps({"status": "failed", "error": err}))
                else:
                    print(f"FAILED: {err}", file=sys.stderr)
                return 1

    print(f"\nTimeout after {timeout}s", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Shared argument helpers
# ---------------------------------------------------------------------------

def _add_nersc_args(parser: argparse.ArgumentParser) -> None:
    """Add NERSC user_endpoint_config flags to a subparser."""
    parser.add_argument(
        "--account",
        help="NERSC allocation (e.g., m1651). Maps to NERSC_ACCOUNT template var",
    )
    parser.add_argument(
        "--options",
        help=(
            'SLURM scheduler options. Maps to OPTIONS template var. '
            'e.g., "#SBATCH -C gpu\\n#SBATCH -q debug\\n#SBATCH --gpus-per-node=4"'
        ),
    )
    parser.add_argument(
        "--worker-init",
        help=(
            'Commands to run before worker starts. Maps to COMMAND template var. '
            'e.g., "module load python; source activate myenv"'
        ),
    )


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Globus Compute job manager (NERSC, template-capable endpoints)"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    sub = parser.add_subparsers(dest="command", required=True)

    # config
    cfg = sub.add_parser("config", help="View or update configuration")
    cfg_sub = cfg.add_subparsers(dest="config_action", required=True)
    cfg_sub.add_parser("show", help="Show current config")
    se = cfg_sub.add_parser("set-endpoint", help="Set default endpoint")
    se.add_argument("endpoint_id", help="Endpoint UUID")
    se.add_argument("--name", help="Friendly name for the endpoint")
    cfg_sub.add_parser("reset", help="Reset config to defaults")

    # status
    st = sub.add_parser("status", help="Check auth and endpoint status")
    st.add_argument("endpoint_id", nargs="?", help="Endpoint UUID (default: from config)")

    # list-endpoints
    sub.add_parser("list-endpoints", help="List your endpoints")

    # sample
    sa = sub.add_parser("sample", help="Run get_hostname() end-to-end")
    sa.add_argument("endpoint_id", nargs="?", help="Endpoint UUID (default: from config)")
    sa.add_argument("--timeout", type=int, default=None, help="Timeout in seconds (default: wait indefinitely)")
    _add_nersc_args(sa)

    # run
    ru = sub.add_parser("run", help="Run a function from a .py file")
    ru.add_argument("function_file", help="Path to .py file with function")
    ru.add_argument("--endpoint", dest="endpoint_id", default=None)
    ru.add_argument("--function-name", help="Name of function (default: first callable)")
    ru.add_argument("--args", help='JSON array, e.g. \'[1, 2]\'')
    ru.add_argument("--kwargs", help='JSON object, e.g. \'{"x": 1}\'')
    ru.add_argument("--timeout", type=int, default=None, help="Timeout in seconds (default: wait indefinitely)")
    _add_nersc_args(ru)

    # submit (by function UUID)
    sm = sub.add_parser("submit", help="Submit by function UUID")
    sm.add_argument("endpoint_id", nargs="?")
    sm.add_argument("function_id")
    sm.add_argument("--args", help="JSON array")
    sm.add_argument("--kwargs", help="JSON object")
    sm.add_argument("--wait", action="store_true")
    sm.add_argument("--timeout", type=int, default=180)
    sm.add_argument("--poll", type=float, default=3)

    # result
    re = sub.add_parser("result", help="Get task result")
    re.add_argument("task_id")
    re.add_argument("--timeout", type=int, default=300)
    re.add_argument("--poll", type=float, default=3)

    args = parser.parse_args()
    dispatch = {
        "config": cmd_config,
        "status": cmd_status,
        "list-endpoints": cmd_list_endpoints,
        "sample": cmd_sample,
        "run": cmd_run,
        "submit": cmd_submit,
        "result": cmd_result,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
