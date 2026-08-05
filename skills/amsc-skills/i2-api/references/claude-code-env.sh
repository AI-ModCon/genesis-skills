#!/usr/bin/env bash
# Claude Code environment configuration for AmSC i2 API
#
# Usage:
#   source references/claude-code-env.sh
#
# Or add these exports to your shell profile (~/.zshrc or ~/.bashrc) for
# persistent configuration.
#
# Prerequisites:
#   1. Go to https://api.i2-core.american-science-cloud.org/
#   2. Log in with your AmSC Google credentials
#   3. Click "API Key Manager" and generate a key
#   4. Set AMSC_I2_API_KEY in your environment before sourcing this file

# Authenticate Claude Code against the i2 API instead of Anthropic directly.
# ANTHROPIC_AUTH_TOKEN is read from AMSC_I2_API_KEY -- fail loudly if not set.
export ANTHROPIC_AUTH_TOKEN="${AMSC_I2_API_KEY:?AMSC_I2_API_KEY must be set before sourcing this file}"
export ANTHROPIC_BASE_URL="https://api.i2-core.american-science-cloud.org"

# Model aliases -- these point to the latest version of each tier.
# Use pinned names (e.g. claude-sonnet-4-6) if you need version stability.
export ANTHROPIC_DEFAULT_HAIKU_MODEL="claude-haiku"
export ANTHROPIC_DEFAULT_SONNET_MODEL="claude-sonnet"
export ANTHROPIC_DEFAULT_OPUS_MODEL="claude-opus"

# Default model for interactive conversation turns.
# claude-sonnet offers a good balance of quality and cost.
# Switch to claude-haiku for faster/cheaper sessions or claude-opus for
# the most capable responses.
export ANTHROPIC_MODEL="claude-sonnet"

# Model used for background subagent tasks (file reads, tool calls, etc.).
# claude-haiku is cheaper and fast enough for these routine operations.
export CLAUDE_CODE_SUBAGENT_MODEL="claude-haiku"

# Suppress optional model calls that are not essential to the task
# (e.g. auto-generated commit message suggestions). Reduces spend.
export DISABLE_NON_ESSENTIAL_MODEL_CALLS=1

# Opt out of usage telemetry sent to Anthropic.
export DISABLE_TELEMETRY=1

# Disable experimental beta features that may not be supported by the i2 proxy.
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1

# Cap output tokens per response. Higher values are possible but may trigger
# "too many tokens" rejections from the proxy. 8192 is a safe default.
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=8192
