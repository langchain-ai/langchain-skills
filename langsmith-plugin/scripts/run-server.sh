#!/bin/bash
# Wrapper to launch the MCP server with the correct Python interpreter.
# Uses the plugin-local venv if available, otherwise tries system python3/python.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_PATH="$PLUGIN_ROOT/servers/langsmith_mcp.py"
VENV_PYTHON="$PLUGIN_ROOT/.venv/bin/python"

# Prefer the plugin venv (created by ensure-deps.sh)
if [ -f "$VENV_PYTHON" ]; then
  exec "$VENV_PYTHON" "$SERVER_PATH"
fi

# Fall back to system Python
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    exec "$cmd" "$SERVER_PATH"
  fi
done

echo "langsmith-plugin: no python interpreter found. Install Python 3.8+ to use this plugin." >&2
exit 1
