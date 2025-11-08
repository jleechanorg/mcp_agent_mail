#!/usr/bin/env bash
set -euo pipefail

# This script runs the MCP Agent Mail server using a locally built wheel
# from the dist/ directory instead of PyPI

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"

echo "🔍 Looking for local wheel in $DIST_DIR..."

# Find the most recent wheel file
WHEEL_FILE=$(ls -t "$DIST_DIR"/*.whl 2>/dev/null | head -1)

if [[ -z "$WHEEL_FILE" ]]; then
  echo "❌ Error: No wheel file found in $DIST_DIR"
  echo "Run 'uv build' first to create the wheel"
  exit 1
fi

echo "📦 Found wheel: $(basename "$WHEEL_FILE")"

# Create a temporary directory for the isolated installation
TEMP_ENV=$(mktemp -d -t mcp_mail-XXXXXX)
trap 'rm -rf "$TEMP_ENV"' EXIT

# Find Python 3.11+ (prefer stable versions, avoid Python 3.14 RC due to Pydantic issues)
PYTHON_BIN=""
MIN_VERSION=311  # e.g. 3.11 -> 311, 3.12 -> 312
MAX_VERSION=313  # Avoid Python 3.14 RC

# Try specific stable versions first
for py in python3.13 python3.12 python3.11; do
  if command -v "$py" >/dev/null 2>&1; then
    PYTHON_BIN=$(command -v "$py")
    break
  fi
done

# Fallback to default python3 if it's in the acceptable range
if [[ -z "$PYTHON_BIN" ]] && command -v python3 >/dev/null 2>&1; then
  PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor:02d}")')
  if [[ "$PY_VER" -ge "$MIN_VERSION" ]] && [[ "$PY_VER" -le "$MAX_VERSION" ]]; then
    PYTHON_BIN=$(command -v python3)
  fi
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "❌ Error: Python 3.11 or higher is required"
  exit 1
fi

echo "Using Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# Check if uv is available
if ! command -v uv >/dev/null 2>&1; then
  echo "❌ Error: uv is required but not installed"
  echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

# Create venv and install the local wheel
echo "🔄 Installing local wheel..."
uv venv "$TEMP_ENV/.venv" --python "$PYTHON_BIN"
source "$TEMP_ENV/.venv/bin/activate"

uv pip install "$WHEEL_FILE"

echo "✅ Installed mcp_mail from local build"

# Load token from environment or .env file
if [[ -z "${HTTP_BEARER_TOKEN:-}" ]]; then
  if [[ -f ~/.config/mcp-agent-mail/.env ]]; then
    HTTP_BEARER_TOKEN=$(grep -E '^HTTP_BEARER_TOKEN=' ~/.config/mcp-agent-mail/.env | sed -E 's/^HTTP_BEARER_TOKEN=//') || true
  elif [[ -f ~/mcp_agent_mail/.env ]]; then
    HTTP_BEARER_TOKEN=$(grep -E '^HTTP_BEARER_TOKEN=' ~/mcp_agent_mail/.env | sed -E 's/^HTTP_BEARER_TOKEN=//') || true
  fi
fi

if [[ -z "${HTTP_BEARER_TOKEN:-}" ]]; then
  # Generate a token if none exists
  HTTP_BEARER_TOKEN=$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_hex(32))')
fi

export HTTP_BEARER_TOKEN

echo "🚀 Starting MCP Mail server from local build..."
python -m mcp_agent_mail.cli serve-http "$@"
