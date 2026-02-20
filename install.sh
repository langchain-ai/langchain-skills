#!/bin/bash

# Install LangGraph + LangSmith skills for Claude Code or DeepAgents CLI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
TARGET="claude"  # claude or deepagents
GLOBAL=false
FORCE=false
YES=false

# Usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Install LangGraph + LangSmith skills for Claude Code or DeepAgents CLI."
    echo ""
    echo "Options:"
    echo "  --claude        Install for Claude Code (default)"
    echo "  --deepagents    Install for DeepAgents CLI"
    echo "  --global, -g    Install globally (~/.claude or ~/.deepagents/langchain_agent)"
    echo "                  Default: install in current directory"
    echo "  --force, -f     Overwrite skills with same names as this package"
    echo "  --yes, -y       Skip confirmation prompts"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Install for Claude Code in current directory"
    echo "  $0 --global             # Install for Claude Code globally"
    echo "  $0 --deepagents -g      # Install for DeepAgents globally (with agent persona)"
    echo "  $0 -f -y                # Force reinstall without prompts"
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --claude)
            TARGET="claude"
            shift
            ;;
        --deepagents)
            TARGET="deepagents"
            shift
            ;;
        --global|-g)
            GLOBAL=true
            shift
            ;;
        --force|-f)
            FORCE=true
            shift
            ;;
        --yes|-y)
            YES=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Determine installation directory and whether to include AGENTS.md
INCLUDE_AGENTS_MD=false

if [ "$TARGET" = "claude" ]; then
    if [ "$GLOBAL" = true ]; then
        INSTALL_DIR="$HOME/.claude"
    else
        INSTALL_DIR="$(pwd)/.claude"
    fi
    TOOL_NAME="Claude Code"
else
    # DeepAgents
    if [ "$GLOBAL" = true ]; then
        # Global: install as agent with persona
        INSTALL_DIR="$HOME/.deepagents/langchain_agent"
        INCLUDE_AGENTS_MD=true
    else
        # Local: just skills, no agent persona
        INSTALL_DIR="$(pwd)/.deepagents"
    fi
    TOOL_NAME="DeepAgents CLI"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "LangChain Skills Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Target:    $TOOL_NAME"
echo "Location:  $INSTALL_DIR"
if [ "$GLOBAL" = true ]; then
    echo "Scope:     Global (all projects)"
else
    echo "Scope:     Local (current directory)"
fi
echo ""

# For DeepAgents global, check if agent already exists
if [ "$TARGET" = "deepagents" ] && [ "$GLOBAL" = true ] && [ -d "$INSTALL_DIR" ]; then
    if [ "$FORCE" = true ]; then
        echo "⚠️  Existing agent found. Will overwrite (--force)."
    else
        echo "❌ ERROR: Agent 'langchain_agent' already exists at $INSTALL_DIR"
        echo ""
        echo "To reinstall, use --force flag:"
        echo "  $0 --deepagents --global --force"
        echo ""
        echo "Or manually remove:"
        echo "  rm -rf $INSTALL_DIR"
        exit 1
    fi
fi

# Confirm installation
if [ "$YES" != true ]; then
    read -p "Proceed with installation? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

echo ""
echo "Installing..."

# For DeepAgents global with --force, remove existing agent
if [ "$TARGET" = "deepagents" ] && [ "$GLOBAL" = true ] && [ "$FORCE" = true ] && [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
fi

# Create directory structure
mkdir -p "$INSTALL_DIR"

# Copy AGENTS.md only for global DeepAgents install
if [ "$INCLUDE_AGENTS_MD" = true ]; then
    if [ -f "$SCRIPT_DIR/config/AGENTS.md" ]; then
        cp "$SCRIPT_DIR/config/AGENTS.md" "$INSTALL_DIR/AGENTS.md"
        echo "✓ Copied AGENTS.md (agent persona)"
    else
        echo "❌ ERROR: config/AGENTS.md not found"
        exit 1
    fi
fi

# Copy skills
if [ -d "$SCRIPT_DIR/config/skills" ]; then
    mkdir -p "$INSTALL_DIR/skills"
    for skill in "$SCRIPT_DIR/config/skills"/*; do
        skill_name=$(basename "$skill")
        if [ -d "$INSTALL_DIR/skills/$skill_name" ]; then
            if [ "$FORCE" = true ]; then
                rm -rf "$INSTALL_DIR/skills/$skill_name"
            else
                echo "⚠️  Skipping $skill_name (already exists, use --force to overwrite)"
                continue
            fi
        fi
        cp -r "$skill" "$INSTALL_DIR/skills/$skill_name"
        echo "✓ Installed $skill_name"
    done
else
    echo "❌ ERROR: config/skills directory not found"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$TARGET" = "claude" ]; then
    echo "Skills installed for Claude Code."
    echo ""
    if [ "$GLOBAL" = true ]; then
        echo "The skills are now available globally in all projects."
    else
        echo "The skills are available in this directory."
        echo "Run Claude Code from here to use them."
    fi
else
    if [ "$GLOBAL" = true ]; then
        echo "Agent 'langchain_agent' is now available in DeepAgents CLI."
        echo ""
        echo "To use this agent, run:"
        echo "  deepagents --agent langchain_agent"
    else
        echo "Skills installed for DeepAgents CLI."
        echo ""
        echo "The skills are available in this directory."
    fi
fi

echo ""
echo "Available skills (15 total):"
echo ""
echo "  Getting Started:"
echo "    - framework-selection: Choose between LangChain, LangGraph, and Deep Agents"
echo "    - langchain-dependencies: Package versions and dependency management (Python + TypeScript)"
echo ""
echo "  Deep Agents:"
echo "    - deep-agents-core: Agent architecture and SKILL.md format"
echo "    - deep-agents-memory: Memory, persistence, and filesystem"
echo "    - deep-agents-orchestration: Subagents, task planning, HITL"
echo ""
echo "  LangChain:"
echo "    - langchain-agents: Agents and tools"
echo "    - langchain-models: Chat models and streaming"
echo "    - langchain-output: Structured output and HITL"
echo "    - langchain-rag: RAG pipeline (loaders, embeddings, vector stores)"
echo ""
echo "  LangGraph:"
echo "    - langgraph-fundamentals: StateGraph, nodes, edges, reducers"
echo "    - langgraph-persistence: Checkpointers and memory"
echo "    - langgraph-execution: Workflows, interrupts, streaming"
echo ""
echo "  LangSmith:"
echo "    - langsmith-trace: Query and export traces"
echo "    - langsmith-dataset: Generate evaluation datasets"
echo "    - langsmith-evaluator: Create custom evaluators"
echo ""
echo "Set your API keys before using:"
echo "  export LANGSMITH_API_KEY=<your-key>"
echo "  export OPENAI_API_KEY=<your-key>      # For OpenAI models"
echo "  export ANTHROPIC_API_KEY=<your-key>   # For Anthropic models"
echo ""
