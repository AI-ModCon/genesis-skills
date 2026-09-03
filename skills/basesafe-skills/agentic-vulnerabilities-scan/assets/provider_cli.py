#!/usr/bin/env python3
"""Promptfoo provider template for an authorized CLI target.

Set MODEL_COMMAND in AGENTIC_SCAN_PROVIDER_ENV. The command must contain the
literal {PROMPT} placeholder. Promptfoo supplies either a plain prompt string
or a JSON-encoded OpenAI-style message array; the latter is passed intact as
the single substituted argument. Review target input and response parsing before
running a scan.
"""

import asyncio
import json
import os
import re
import shlex
import subprocess
from typing import TypedDict


class ProviderResponse(TypedDict, total=False):
    output: str
    error: str
    conversationEnded: bool


def target_environment(config: dict) -> dict[str, str]:
    """Build the target environment from provider config, not ambient secrets."""
    environment = {"PATH": os.environ["PATH"]} if "PATH" in os.environ else {}
    for key, value in config.items():
        if re.fullmatch(r"[A-Z_][A-Z0-9_]*", str(key)):
            environment[str(key)] = str(value)
    return environment


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
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=300,
            env=target_environment(config),
        )
        if result.returncode:
            return {"output": "", "error": "Target command failed.", "conversationEnded": True}

        # Replace this plain-text behavior only when the target has a documented
        # structured response format. Do not return raw stderr or exception text.
        return {"output": result.stdout.strip(), "conversationEnded": False}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"output": "", "error": "Target command could not be executed.", "conversationEnded": True}
