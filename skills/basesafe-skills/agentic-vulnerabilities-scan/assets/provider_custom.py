"""Promptfoo provider template for a custom Python target.

Edit the marked section to import and call the real target. This code executes
the target in the already-authorized sandbox; never replace it with a simulator.
"""

import asyncio
from contextlib import contextmanager
import inspect
import json
import os
from typing import Iterator, TypedDict


class ProviderResponse(TypedDict, total=False):
    output: str
    error: str
    conversationEnded: bool
    conversationEndReason: str


@contextmanager
def temporary_environment(values: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


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
        with temporary_environment({str(key): str(value) for key, value in config.items()}):
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
