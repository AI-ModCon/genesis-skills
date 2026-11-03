# claude-amsc: run Claude Code against the AmSC Model Access Gateway (MAG).
# Source from ~/.zshrc or ~/.bashrc. Variables apply only to this invocation,
# so plain `claude` keeps using its normal backend.
#
# Requires AMSC_TOKEN (PAT from https://my.amsc.energy.gov/dashboard).
# Do NOT set ANTHROPIC_MODEL, ANTHROPIC_DEFAULT_*_MODEL or CLAUDE_CODE_SUBAGENT_MODEL;
# choose models with /model inside Claude Code.
# Haiku: run CLAUDE_CODE_AUTO_COMPACT_WINDOW=100000 claude-amsc
# Optional: MAG_PROVIDER=amazon claude-amsc pins requests to one provider bucket.

claude-amsc() {
  if [ -z "${AMSC_TOKEN:-}" ]; then
    echo "claude-amsc: AMSC_TOKEN is not set" >&2
    return 1
  fi
  ANTHROPIC_AUTH_TOKEN=$AMSC_TOKEN \
  ANTHROPIC_BASE_URL=https://mag.genesis.americansciencecloud.org \
  CLAUDE_CODE_AUTO_COMPACT_WINDOW=${CLAUDE_CODE_AUTO_COMPACT_WINDOW:-200000} \
  CLAUDE_CODE_MAX_OUTPUT_TOKENS=16384 \
  DISABLE_NON_ESSENTIAL_MODEL_CALLS=1 DISABLE_TELEMETRY=1 \
  CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 \
  ANTHROPIC_CUSTOM_HEADERS=${MAG_PROVIDER:+"X-AmSC-MAG-Provider: $MAG_PROVIDER"} \
  claude "$@"
}
