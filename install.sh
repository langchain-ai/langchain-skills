#!/bin/bash

# Install LangGraph + LangSmith skills as a DeepAgents CLI agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_DEEPAGENTS_DIR="$HOME/.deepagents"
DEFAULT_AGENT_NAME="langchain_agent"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DeepAgents CLI - LangChain Agent Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will install LangGraph + LangSmith skills as a custom agent"
echo "in your DeepAgents CLI configuration."
echo ""

# Prompt for agent name
read -p "Agent name [default: $DEFAULT_AGENT_NAME]: " AGENT_NAME
AGENT_NAME="${AGENT_NAME:-$DEFAULT_AGENT_NAME}"

# Prompt for installation directory
read -p "Installation directory [default: $DEFAULT_DEEPAGENTS_DIR]: " DEEPAGENTS_DIR
DEEPAGENTS_DIR="${DEEPAGENTS_DIR:-$DEFAULT_DEEPAGENTS_DIR}"

# Expand tilde
DEEPAGENTS_DIR="${DEEPAGENTS_DIR/#\~/$HOME}"

AGENT_DIR="$DEEPAGENTS_DIR/$AGENT_NAME"

echo ""
echo "Agent will be installed to: $AGENT_DIR"
echo ""

# Check if agent already exists
if [ -d "$AGENT_DIR" ]; then
    echo "❌ ERROR: Agent '$AGENT_NAME' already exists at $AGENT_DIR"
    echo ""
    echo "To reinstall, first remove the existing agent:"
    echo "  rm -rf $AGENT_DIR"
    echo ""
    exit 1
fi

# Ask for confirmation
read -p "Proceed with installation? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo "Installing..."

# Create agent directory structure
mkdir -p "$AGENT_DIR"

# Copy AGENTS.md
if [ -f "$SCRIPT_DIR/config/AGENTS.md" ]; then
    cp "$SCRIPT_DIR/config/AGENTS.md" "$AGENT_DIR/AGENTS.md"
    echo "✓ Copied AGENTS.md"
else
    echo "❌ ERROR: config/AGENTS.md not found"
    rm -rf "$AGENT_DIR"
    exit 1
fi

# Copy skills directory
if [ -d "$SCRIPT_DIR/config/skills" ]; then
    cp -r "$SCRIPT_DIR/config/skills" "$AGENT_DIR/skills"
    echo "✓ Copied skills directory"
else
    echo "❌ ERROR: config/skills directory not found"
    rm -rf "$AGENT_DIR"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Agent '$AGENT_NAME' is now available in DeepAgents CLI."
echo ""
echo "To use this agent, run:"
echo "  deepagents --agent $AGENT_NAME"
echo ""
echo "Available skills:"
echo "  - langgraph-code: Building agents with LangGraph"
echo "  - langsmith-trace: Query and inspect traces"
echo "  - langsmith-dataset: Generate evaluation datasets"
echo "  - langsmith-evaluator: Create custom metrics"
echo ""
echo "Set your LangSmith API key before using:"
echo "  export LANGSMITH_API_KEY=<your-key>"
echo ""
