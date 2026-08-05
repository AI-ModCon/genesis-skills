#!/usr/bin/env python3
"""Promptfoo provider template for an authorized CLI target.

Set MODEL_COMMAND in AGENTIC_SCAN_PROVIDER_ENV. The command must contain the
literal {PROMPT} placeholder. Promptfoo supplies either a plain prompt string
or a JSON-encoded OpenAI-style message array; the latter is passed intact as
the single substituted argument. Review target input and response parsing before
running a scan.
"""

import asyncio
from contextlib import contextmanager
import json
import os
import shlex
import subprocess
from typing import Iterator, TypedDict


class ProviderResponse(TypedDict, total=False):
    output: str
    error: str
    conversationEnded: bool


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


def prompt_text(prompt: str) -> str:
    try:
        messages = json.loads(prompt)
    except json.JSONDecodeError:
        return prompt
    return json.dumps(messages) if isinstance(messages, list) else prompt


async def call_api(prompt: str, options: dict, context: dict) -> ProviderResponse:
    config = options.get("config", {})
    if not isinstance(config, dict):
        return {"output": "", "error": "Invalid provider configuration."}
    command_template = config.get("MODEL_COMMAND")
    if not isinstance(command_template, str) or "{PROMPT}" not in command_template:
        return {"output": "", "error": "MODEL_COMMAND is not configured."}

    try:
        command = shlex.split(command_template.format(PROMPT=prompt_text(prompt)))
        if not command:
            raise ValueError("empty command")
        target_dir = config.get("AGENTIC_SCAN_TARGET_DIR", ".")
        with temporary_environment({str(key): str(value) for key, value in config.items()}):
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=300,
                env=os.environ.copy(),
            )
        if result.returncode:
            return {"output": "", "error": "Target command failed.", "conversationEnded": True}

        # Replace this plain-text behavior only when the target has a documented
        # structured response format. Do not return raw stderr or exception text.
        return {"output": result.stdout.strip(), "conversationEnded": False}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"output": "", "error": "Target command could not be executed.", "conversationEnded": True}
