#!/bin/bash
# Ensure MCP server dependencies are installed.
# Runs on SessionStart — checks first to avoid redundant installs.
# Creates a plugin-local venv to avoid PEP 668 / system Python issues.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PLUGIN_ROOT/.venv"

# Find a working Python interpreter (try python3 first, then python)
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON="$cmd"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo "langsmith-plugin: no python interpreter found. Install Python 3.8+ to use this plugin." >&2
  exit 0
fi

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "langsmith-plugin: creating virtual environment..." >&2
  "$PYTHON" -m venv "$VENV_DIR" 2>&1 >&2
  if [ $? -ne 0 ]; then
    echo "langsmith-plugin: failed to create venv. Falling back to system Python." >&2
    VENV_DIR=""
  fi
fi

# Use venv Python/pip if available, otherwise fall back to system
if [ -n "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python" ]; then
  VENV_PYTHON="$VENV_DIR/bin/python"
  VENV_PIP="$VENV_DIR/bin/pip"
else
  VENV_PYTHON="$PYTHON"
  # Find a working pip (try pip3 first, then pip, then python -m pip)
  VENV_PIP=""
  for cmd in pip3 pip; do
    if command -v "$cmd" &>/dev/null; then
      VENV_PIP="$cmd"
      break
    fi
  done
  if [ -z "$VENV_PIP" ]; then
    if "$PYTHON" -m pip --version &>/dev/null; then
      VENV_PIP="$PYTHON -m pip"
    else
      echo "langsmith-plugin: no pip found. Install pip to use this plugin." >&2
      exit 0
    fi
  fi
fi

REQUIRED_PACKAGES=("mcp" "langsmith" "python-dotenv")
MISSING=()

for pkg in "${REQUIRED_PACKAGES[@]}"; do
  # python-dotenv imports as "dotenv", handle the name mapping
  import_name="${pkg//-/_}"
  if [ "$pkg" = "python-dotenv" ]; then
    import_name="dotenv"
  fi
  "$VENV_PYTHON" -c "import $import_name" 2>/dev/null || MISSING+=("$pkg")
done

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "langsmith-plugin: installing missing dependencies: ${MISSING[*]}" >&2
  $VENV_PIP install -q "${MISSING[@]}" 2>&1 | tail -1 >&2
fi

exit 0
