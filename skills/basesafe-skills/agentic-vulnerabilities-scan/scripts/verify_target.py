"""Prepare an isolated Promptfoo workspace for an authorized target scan."""

import collections
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.error import HTTPError, URLError
import urllib.request

from promptfoo_environment import promptfoo_environment

try:
    from ruyaml import YAML
except ModuleNotFoundError:
    print("Cannot run. Missing dependency: Python package `ruyaml`.")
    sys.exit(1)


if not shutil.which("promptfoo"):
    print("Cannot run. Missing dependency: promptfoo (install it with npm).")
    sys.exit(1)


TARGET_DIR = Path.cwd().resolve()
SCAN_DIR = Path(
    os.environ.get("AGENTIC_SCAN_DIR", TARGET_DIR / ".agentic-vulnerabilities-scan")
).expanduser().resolve()
PROMPTFOO_CONFIG_PATH = SCAN_DIR / "promptfooconfig.yaml"
REDTEAM_TESTS_PATH = SCAN_DIR / "redteam.yaml"
PROVIDER_PATH = SCAN_DIR / "provider.py"
USER_PROMPTFOO_CONFIG_PATH = TARGET_DIR / "promptfooconfig.yaml"
USER_PROVIDER_PATH = TARGET_DIR / "provider.py"
ABORT = "\nAbort the workflow and report this error to the user."

yaml = YAML()
yaml.preserve_quotes = True


class ExitWithMessage(Exception):
    """A safe, actionable message for the invoking agent."""


class NextStep(Exception):
    """A successful verification outcome that tells the caller what to do next."""


def safe_error(action: str) -> ExitWithMessage:
    return ExitWithMessage(f"{action}. See the local Promptfoo output for details.{ABORT}")


def ensure_scan_workspace() -> None:
    """Create or verify the dedicated workspace without touching target files."""
    try:
        SCAN_DIR.relative_to(TARGET_DIR)
    except ValueError as error:
        raise ExitWithMessage("AGENTIC_SCAN_DIR must be inside the target repository." + ABORT) from error
    if SCAN_DIR == TARGET_DIR or SCAN_DIR == Path(SCAN_DIR.anchor):
        raise ExitWithMessage("AGENTIC_SCAN_DIR must name a dedicated subdirectory." + ABORT)

    if SCAN_DIR.exists():
        if not SCAN_DIR.is_dir():
            raise ExitWithMessage(
                f"AGENTIC_SCAN_DIR exists but is not a directory: {SCAN_DIR}." + ABORT
            )
        return

    SCAN_DIR.mkdir(parents=True, mode=0o700)


def read_promptfoo_config(path: Path = PROMPTFOO_CONFIG_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = yaml.load(handle)
    if not isinstance(data, collections.abc.Mapping):
        raise ExitWithMessage(f"{path.name} must contain a YAML mapping." + ABORT)
    return data


def promptfoo_has_providers(path: Path = PROMPTFOO_CONFIG_PATH) -> bool:
    data = read_promptfoo_config(path)
    return bool(data.get("targets") or data.get("providers"))


def validate_promptfoo_config(path: Path = PROMPTFOO_CONFIG_PATH) -> None:
    result = subprocess.run(
        ["promptfoo", "validate", "-c", str(path)],
        cwd=SCAN_DIR,
        capture_output=True,
        text=True,
        timeout=300,
        env=promptfoo_environment(),
    )
    if result.returncode:
        match = re.search(r"Debug log: (.*\.log)", result.stdout)
        detail = f" Debug log: {match.group(1)}." if match else ""
        raise safe_error(f"Promptfoo configuration validation failed{detail}")


def write_promptfoo_config(content: dict, path: Path = PROMPTFOO_CONFIG_PATH) -> None:
    try:
        with path.open(mode="w", encoding="utf-8") as handle:
            yaml.dump(content, handle)
    except OSError as error:
        raise safe_error(f"Could not write {path.name}") from error


def update_promptfoo_config(content: dict, path: Path = PROMPTFOO_CONFIG_PATH) -> None:
    try:
        data = read_promptfoo_config(path)
    except (OSError, ValueError) as error:
        raise safe_error(f"Could not read {path.name}") from error

    def recursive_update(current: dict, update: dict) -> dict:
        for key, value in update.items():
            if isinstance(value, collections.abc.Mapping):
                current[key] = recursive_update(current.get(key, {}), value)
            else:
                current[key] = value
        return current

    write_promptfoo_config(recursive_update(data, content), path)


def copy_asset(asset_name: str, destination: Path) -> None:
    if destination.exists():
        return
    try:
        shutil.copy2(Path(__file__).parent.parent / "assets" / asset_name, destination)
    except OSError as error:
        raise safe_error(f"Could not create {destination.name}") from error


def import_user_config() -> None:
    """Seed the workspace from a user config without changing the source copy."""
    try:
        data = read_promptfoo_config(USER_PROMPTFOO_CONFIG_PATH)
    except (OSError, ValueError) as error:
        raise safe_error("Could not read the user promptfooconfig.yaml") from error

    def normalize_provider(provider: object) -> object:
        if isinstance(provider, dict):
            provider_id = provider.get("id")
            if isinstance(provider_id, str):
                provider["id"] = normalize_file_provider_path(provider_id, TARGET_DIR)
        elif isinstance(provider, str):
            return normalize_file_provider_path(provider, TARGET_DIR)
        return provider

    for key in ("providers", "targets"):
        providers = data.get(key)
        if isinstance(providers, list):
            data[key] = [normalize_provider(provider) for provider in providers]
        elif providers is not None:
            data[key] = normalize_provider(providers)
    write_promptfoo_config(data)


def normalize_file_provider_path(provider_id: str, base_dir: Path) -> str:
    """Keep file-based providers usable after importing config into the workspace."""
    if not provider_id.startswith("file://"):
        return provider_id
    value = provider_id.removeprefix("file://")
    path = Path(value)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return f"file://{path}"


def import_user_provider() -> None:
    try:
        shutil.copy2(USER_PROVIDER_PATH, PROVIDER_PATH)
    except OSError as error:
        raise safe_error("Could not import the user provider.py") from error


def get_provider_env_vars() -> dict[str, str]:
    """Pass only an operator-approved allowlist to persistent providers."""
    requested = os.environ.get("AGENTIC_SCAN_PROVIDER_ENV", "")
    names = [name.strip() for name in requested.split(",") if name.strip()]
    invalid = [name for name in names if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", name)]
    missing = [name for name in names if name not in os.environ]
    if invalid or missing:
        raise ExitWithMessage(
            "AGENTIC_SCAN_PROVIDER_ENV must contain present, uppercase environment "
            f"variable names only (invalid: {', '.join(invalid) or 'none'}; "
            f"missing: {', '.join(missing) or 'none'})." + ABORT
        )
    values = {name: os.environ[name] for name in names}
    values["AGENTIC_SCAN_TARGET_DIR"] = str(TARGET_DIR)
    return values


def preflight_validate() -> None:
    host = os.environ.get("PROMPTFOO_HOST")
    api_key = os.environ.get("PROMPTFOO_API_KEY")
    if not host or not api_key:
        raise ExitWithMessage(
            "Set non-empty PROMPTFOO_HOST and PROMPTFOO_API_KEY values." + ABORT
        )

    result = subprocess.run(
        ["promptfoo", "auth", "login", "--host", host, "--api-key", api_key],
        cwd=SCAN_DIR,
        capture_output=True,
        text=True,
        timeout=300,
        env=promptfoo_environment(),
    )
    if result.returncode:
        raise safe_error("Promptfoo authentication failed")


def require_remote_generation() -> None:
    if os.environ.get("PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION", "").lower() == "true":
        raise ExitWithMessage(
            "Remote Promptfoo red-team generation is required; unset "
            "PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION." + ABORT
        )


def validate_headless_identity() -> None:
    """Read and validate the authorization policy before probing a target."""
    if os.environ.get("AGENTIC_SCAN_HEADLESS") != "true":
        return
    try:
        from validate_scan_policy import PolicyError, read_policy, validate_runtime_environment

        read_policy()
        validate_runtime_environment()
    except PolicyError as error:
        raise ExitWithMessage(f"Headless policy validation failed: {error}" + ABORT) from error


def verify_target() -> None:
    def config_api_endpoint_provider(prompt: str = "Reply with OK.") -> None:
        endpoint = os.environ["MODEL_ENDPOINT"]
        token = os.environ.get("MODEL_AUTH_TOKEN")
        model = os.environ.get("MODEL")
        if not model:
            raise ExitWithMessage("MODEL is required when configuring an HTTP target." + ABORT)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["authorization"] = f"bearer {token}"
        payload = {"messages": [{"role": "user", "content": prompt}]}
        if model:
            payload["model"] = model
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()
        except HTTPError as error:
            raise ExitWithMessage(
                f"The target returned HTTP status {error.code}." + ABORT
            ) from error
        except (URLError, TimeoutError) as error:
            raise safe_error("Could not reach the target endpoint") from error

        config = {"apiBaseUrl": endpoint}
        if token:
            config["apiKey"] = "{{ env.MODEL_AUTH_TOKEN }}"
        update_promptfoo_config({"providers": [{"id": model, "config": config}]})

    def config_cli_provider() -> None:
        command = os.environ["MODEL_COMMAND"]
        if "{PROMPT}" not in command:
            raise ExitWithMessage("MODEL_COMMAND must include a {PROMPT} placeholder." + ABORT)
        copy_asset("provider_cli.py", PROVIDER_PATH)
        update_promptfoo_config(
            {"providers": [{"id": f"file://{PROVIDER_PATH}", "config": get_provider_env_vars()}]}
        )
        raise NextStep(
            f"Created {PROVIDER_PATH.name}. Review its target-specific response parsing, "
            "then run verification again."
        )

    def config_custom_provider() -> None:
        copy_asset("provider_custom.py", PROVIDER_PATH)
        update_promptfoo_config(
            {"providers": [{"id": f"file://{PROVIDER_PATH}", "config": get_provider_env_vars()}]}
        )
        raise NextStep(
            f"Created {PROVIDER_PATH.name}. Edit it to wrap the real target, then run "
            "verification again; do not substitute a simulator."
        )

    if USER_PROMPTFOO_CONFIG_PATH.exists():
        import_user_config()
    elif not PROMPTFOO_CONFIG_PATH.exists():
        copy_asset("superconfig.yaml", PROMPTFOO_CONFIG_PATH)

    if not promptfoo_has_providers():
        if USER_PROVIDER_PATH.is_file():
            import_user_provider()
            update_promptfoo_config(
                {"providers": [{"id": f"file://{PROVIDER_PATH}", "config": get_provider_env_vars()}]}
            )
        elif PROVIDER_PATH.is_file():
            update_promptfoo_config(
                {"providers": [{"id": f"file://{PROVIDER_PATH}", "config": get_provider_env_vars()}]}
            )
        elif "MODEL_ENDPOINT" in os.environ:
            config_api_endpoint_provider()
        elif "MODEL_COMMAND" in os.environ:
            config_cli_provider()
        else:
            config_custom_provider()

    validate_promptfoo_config()
    config_data = read_promptfoo_config()
    providers = config_data.get("providers") or config_data.get("targets", [])
    provider_items = providers if isinstance(providers, list) else [providers]
    python_provider = next(
        (
            item
            for item in provider_items
            if str(item.get("id", "") if isinstance(item, dict) else item).endswith(".py")
        ),
        None,
    )
    if python_provider is not None:
        from smoke_test_provider import smoke_test_python_provider

        provider_config = python_provider.get("config", {}) if isinstance(python_provider, dict) else {}
        provider_id = python_provider.get("id", "") if isinstance(python_provider, dict) else python_provider
        provider_path = Path(str(provider_id).removeprefix("file://"))
        if not provider_path.is_absolute():
            provider_path = (SCAN_DIR / provider_path).resolve()
        success, message = smoke_test_python_provider(provider_path, provider_config)
        if not success:
            raise ExitWithMessage(f"Provider smoke test failed: {message}" + ABORT)

    if REDTEAM_TESTS_PATH.exists() and REDTEAM_TESTS_PATH.stat().st_size:
        raise NextStep("Red-team tests already exist. Proceed to evaluation.")
    raise NextStep("Promptfoo is configured. Proceed to target fingerprinting.")


if __name__ == "__main__":
    try:
        validate_headless_identity()
        ensure_scan_workspace()
        preflight_validate()
        require_remote_generation()
        verify_target()
    except NextStep as outcome:
        print(outcome)
    except ExitWithMessage as error:
        print(error)
        sys.exit(1)
