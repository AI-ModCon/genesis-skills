#!/usr/bin/env bash
# Install amsc-client and dependencies
# Supports: uv (preferred), pip+venv, pip (fallback)
set -euo pipefail

EXTRA_INDEXES=(
  "--extra-index-url" "https://gitlab.com/api/v4/projects/77567162/packages/pypi/simple"
  "--extra-index-url" "https://gitlab.com/api/v4/projects/76368190/packages/pypi/simple"
  "--extra-index-url" "https://gitlab.com/api/v4/projects/80654726/packages/pypi/simple"
)

PACKAGES=("amsc-client[globus]" "globus-sdk")

# Accept optional venv path as $1 (default: .venv)
VENV_DIR="${1:-.venv}"

if command -v uv &>/dev/null; then
  echo "Using uv to create venv and install..."
  uv venv "$VENV_DIR" 2>/dev/null || true
  uv pip install --python "$VENV_DIR/bin/python3" "${EXTRA_INDEXES[@]}" "${PACKAGES[@]}"
  echo ""
  echo "amsc-client installed in $VENV_DIR (activate: source $VENV_DIR/bin/activate)"
elif python3 -c "import venv" 2>/dev/null; then
  echo "Using python3 venv + pip..."
  python3 -m venv "$VENV_DIR" 2>/dev/null || true
  "$VENV_DIR/bin/pip" install "${EXTRA_INDEXES[@]}" "${PACKAGES[@]}"
  echo ""
  echo "amsc-client installed in $VENV_DIR (activate: source $VENV_DIR/bin/activate)"
else
  echo "Installing with pip (system)..."
  pip install "${EXTRA_INDEXES[@]}" "${PACKAGES[@]}"
  echo ""
  echo "amsc-client installed system-wide."
fi

echo "Run 'python3 .claude/skills/amsc-python-client/scripts/verify_setup.py' to verify."
