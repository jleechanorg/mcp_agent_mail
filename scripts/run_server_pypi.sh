#!/usr/bin/env bash
set -euo pipefail

# This script runs the MCP Agent Mail server using the PyPI package
# instead of local development code

echo "🔄 Installing mcp-agent-mail from PyPI..."

# Create a temporary directory for the isolated installation
TEMP_ENV=$(mktemp -d -t mcp-agent-mail-XXXXXX)
trap "rm -rf $TEMP_ENV" EXIT

# Find Python 3.11+
PYTHON_BIN=""
for py in python3.13 python3.12 python3.11; do
  if command -v "$py" >/dev/null 2>&1; then
    PYTHON_BIN=$(command -v "$py")
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "❌ Error: Python 3.11 or higher is required"
  exit 1
fi

echo "Using Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# Install the package from PyPI using uv
cd "$TEMP_ENV"
uv venv --python "$PYTHON_BIN"
source .venv/bin/activate

uv pip install mcp-agent-mail

echo "✅ Installed mcp-agent-mail from PyPI"

# Load token from environment or .env file
if [[ -z "${HTTP_BEARER_TOKEN:-}" ]]; then
  if [[ -f ~/.config/mcp-agent-mail/.env ]]; then
    HTTP_BEARER_TOKEN=$(grep -E '^HTTP_BEARER_TOKEN=' ~/.config/mcp-agent-mail/.env | sed -E 's/^HTTP_BEARER_TOKEN=//') || true
  elif [[ -f /Users/jleechan/mcp_agent_mail/.env ]]; then
    HTTP_BEARER_TOKEN=$(grep -E '^HTTP_BEARER_TOKEN=' /Users/jleechan/mcp_agent_mail/.env | sed -E 's/^HTTP_BEARER_TOKEN=//') || true
  fi
fi

if [[ -z "${HTTP_BEARER_TOKEN:-}" ]]; then
  # Generate a token if none exists
  HTTP_BEARER_TOKEN=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
fi

export HTTP_BEARER_TOKEN

echo "🚀 Starting MCP Agent Mail server from PyPI package..."
python -m mcp_agent_mail.cli serve-http "$@"
