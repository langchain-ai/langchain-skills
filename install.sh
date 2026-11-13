#!/usr/bin/env bash

# Install skills from a local checkout. Linked installs follow future git pulls.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="claude"
GLOBAL=false
COPY=false
FORCE=false
YES=false
TARGET_DIR=""

usage() {
    cat <<'EOF'
Usage: ./install.sh [OPTIONS] [DIRECTORY]

Install LangChain skills from this checkout. Skills are symlinked by default;
use --copy for a standalone installation. DIRECTORY defaults to the current
directory and is ignored with --global.

Options:
  --claude, --codex, --cursor, --dcode  Target agent (default: claude)
  --global, -g       Install for all projects
  --copy             Copy skills instead of linking to this checkout
  --force, -f        Replace existing skills with the same names
  --yes, -y          Skip confirmation
  --help, -h         Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --claude) TARGET="claude" ;;
        --codex) TARGET="codex" ;;
        --cursor) TARGET="cursor" ;;
        --dcode) TARGET="dcode" ;;
        --global|-g) GLOBAL=true ;;
        --copy) COPY=true ;;
        --force|-f) FORCE=true ;;
        --yes|-y) YES=true ;;
        --help|-h) usage; exit 0 ;;
        -*) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
        *)
            if [[ -n "$TARGET_DIR" ]]; then
                echo "Specify only one target directory." >&2
                exit 1
            fi
            TARGET_DIR="$1"
            ;;
    esac
    shift
done

if [[ ! -d "$SCRIPT_DIR/skills" ]]; then
    echo "Skills directory not found: $SCRIPT_DIR/skills" >&2
    exit 1
fi

TARGET_DIR="${TARGET_DIR:-$PWD}"
if [[ "$GLOBAL" == true ]]; then
    case "$TARGET" in
        claude) INSTALL_DIR="$HOME/.claude" ;;
        codex) INSTALL_DIR="$HOME/.codex" ;;
        cursor) INSTALL_DIR="$HOME/.cursor" ;;
        dcode) INSTALL_DIR="$HOME/.deepagents/agent" ;;
    esac
else
    case "$TARGET" in
        claude) INSTALL_DIR="$TARGET_DIR/.claude" ;;
        codex) INSTALL_DIR="$TARGET_DIR/.agents" ;;
        cursor) INSTALL_DIR="$TARGET_DIR/.cursor" ;;
        dcode) INSTALL_DIR="$TARGET_DIR/.deepagents" ;;
    esac
fi

MODE="linked"
if [[ "$COPY" == true ]]; then MODE="copied"; fi
echo "Install $TARGET skills to $INSTALL_DIR ($MODE)"
if [[ "$YES" != true ]]; then
    read -r -p "Proceed? [y/N] " REPLY
    if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then exit 0; fi
fi

mkdir -p "$INSTALL_DIR/skills"
for skill in "$SCRIPT_DIR"/skills/*; do
    [[ -f "$skill/SKILL.md" ]] || continue
    skill_name="${skill##*/}"
    destination="$INSTALL_DIR/skills/$skill_name"
    if [[ -e "$destination" || -L "$destination" ]]; then
        if [[ "$FORCE" != true ]]; then
            echo "Skipped $skill_name (exists; use --force to replace)"
            continue
        fi
        rm -rf -- "$destination"
    fi
    if [[ "$COPY" == true ]]; then
        cp -R -- "$skill" "$destination"
    else
        ln -s -- "$skill" "$destination"
    fi
    echo "Installed $skill_name"
done

echo "Done. Restart your agent session to load updated skills."
if [[ "$COPY" == true ]]; then
    echo "After a git pull, rerun this installer with --force to refresh copies."
else
    echo "After a git pull, existing links use updated skills. Rerun this installer to add new skills."
fi
