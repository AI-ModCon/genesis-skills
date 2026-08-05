"""
Smoke test for Python-based promptfoo providers.

Tests that provider.py can be imported and its call_api function
can be invoked successfully with a simple test prompt.
"""

import asyncio
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any


def smoke_test_python_provider(
    provider_path: Path = Path("provider.py"), config: dict | None = None
) -> tuple[bool, str]:
    """
    Test that a Python provider can be loaded and called.

    Args:
        provider_path: Path to the provider.py file (relative to cwd)

    Returns:
        tuple of (success: bool, message: str)
    """

    if not provider_path.exists():
        return False, f"Provider file not found: {provider_path}"

    try:
        spec = importlib.util.spec_from_file_location("agentic_scan_provider", provider_path)
        if not spec or not spec.loader:
            return False, "Could not load the provider module"
        provider = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(provider)
    except Exception as e:
        return False, "Failed to load provider. Check the local provider implementation."

    # Check if call_api exists
    if not hasattr(provider, 'call_api'):
        return False, "Provider does not have a call_api function"

    call_api = provider.call_api

    # Prepare test inputs
    test_prompt = "Hello, this is a test."
    test_options = {'config': config or {}}
    test_context = {}

    try:
        # Check if call_api is async or sync
        if inspect.iscoroutinefunction(call_api):
            # Async version
            result = asyncio.run(call_api(test_prompt, test_options, test_context))
        else:
            # Sync version
            result = call_api(test_prompt, test_options, test_context)
    except Exception as e:
        return False, "Provider call_api failed. Check the local provider implementation."

    # Validate response structure
    if not isinstance(result, dict):
        return False, "Provider returned an invalid response type"

    if "output" not in result:
        return False, "Provider response missing required 'output' field"

    if not isinstance(result["output"], str):
        return False, "Provider response has an invalid output field"

    # Check if there was an error
    if result.get("error"):
        return False, "Provider returned an error. Check the local provider implementation."

    # If output is empty, that might indicate a problem
    if not result["output"].strip():
        return False, "Provider returned empty output (this may indicate a configuration issue)"

    return True, "Provider smoke test passed"


if __name__ == "__main__":
    success, message = smoke_test_python_provider()
    print(message)
    sys.exit(0 if success else 1)
