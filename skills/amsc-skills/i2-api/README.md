# i2-api

Agent skill for working with the AmSC i2 LLM API at `api.i2-core.american-science-cloud.org`.

## Overview

This skill provides scripted workflows for:

- API key validation and spend tracking
- Model discovery and selection
- Chat completions (including streaming)
- Embeddings
- Cost estimation
- Claude Code configuration with i2 as the backend
- LangChain integration

## Prerequisites

1. Go to `https://api.i2-core.american-science-cloud.org/`
2. Log in with your AmSC Google credentials
3. Click "API Key Manager" in the upper right corner
4. Generate a key
5. Export it as an environment variable:

```bash
export AMSC_I2_API_KEY=<your-key>
```

> **Never hardcode API keys in source code.** Always use environment variables.

## Quick Start

```bash
# Validate your key
python3 scripts/key_manager.py status

# List available models
python3 scripts/i2_api_call.py list-models

# Send a chat message
python3 scripts/i2_api_call.py chat --model claude-sonnet --message "Hello, world"
```

## Contents

| Path | Description |
|------|-------------|
| `SKILL.md` | Full skill instructions for AI agents |
| `scripts/key_manager.py` | API key validation and spend tracking |
| `scripts/i2_api_call.py` | Chat completions, embeddings, model discovery, cost estimation |
| `scripts/select_model.py` | Model selection by capability requirements |
| `references/claude-code-env.sh` | Environment variable template for Claude Code + i2 |

## Usage

See [`SKILL.md`](SKILL.md) for the complete reference, including:

- Key management and spend tracking
- Model discovery and selection (CLI filter, natural language, and interview modes)
- Chat completions with system prompts, streaming, and retry handling
- Embeddings
- Claude Code setup
- LangChain integration
- Network troubleshooting (SSL, timeouts, retries)

## Installation

Copy or symlink this directory into your agent skills folder, then reference `SKILL.md` in your agent configuration.
