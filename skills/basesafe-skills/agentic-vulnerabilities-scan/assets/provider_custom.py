"""Promptfoo provider template for a custom Python target.

Edit the marked section to import and call the real target. This code executes
the target in the already-authorized sandbox; never replace it with a simulator.
"""

import asyncio
from contextlib import contextmanager
import inspect
import json
import os
import re
from typing import Iterator, TypedDict


class ProviderResponse(TypedDict, total=False):
    output: str
    error: str
    conversationEnded: bool
    conversationEndReason: str


_target_lock = asyncio.Lock()


@contextmanager
def target_environment(values: dict[str, str]) -> Iterator[None]:
    """Expose only configured target variables while target code is running."""
    previous = os.environ.copy()
    environment = {"PATH": previous["PATH"]} if "PATH" in previous else {}
    for key, value in values.items():
        if re.fullmatch(r"[A-Z_][A-Z0-9_]*", str(key)):
            environment[str(key)] = str(value)
    os.environ.clear()
    os.environ.update(environment)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


async def call_api(prompt: str, options: dict, context: dict) -> ProviderResponse:
    try:
        messages = json.loads(prompt)
        if not isinstance(messages, list):
            messages = [{"role": "user", "content": prompt}]
    except json.JSONDecodeError:
        messages = [{"role": "user", "content": prompt}]

    config = options.get("config", {})
    if not isinstance(config, dict):
        return {"output": "", "error": "Invalid provider configuration."}

    try:
        async with _target_lock:
            with target_environment(config):
                # TODO: import the real target here and construct it once per call.
                # Example: from target import Agent; agent = Agent()
                # Do not execute both forms below: use one interface for the target.
                raise NotImplementedError("Customize this provider for the target.")
                # response = agent.process_messages(messages)
                # if inspect.isawaitable(response):
                #     response = await response

        # TODO: adapt this mapping to the documented target response schema.
        # return {"output": response["reply"], "conversationEnded": False}
    except NotImplementedError:
        return {"output": "", "error": "Custom provider has not been implemented."}
    except Exception:
        return {"output": "", "error": "Target provider failed."}
