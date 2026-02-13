# LangGraph + LangSmith Skills

> **⚠️ ALPHA** — This project is in early development. APIs and skill content may change.

Agent skills for building, observing, and evaluating LangGraph agents with LangSmith.

## Supported Coding Agents

These skills can be installed for the following AI coding agents:

| Agent | Local Install | Global Install |
|-------|---------------|----------------|
| **Claude Code** | `.claude/skills/` | `~/.claude/skills/` |
| **DeepAgents CLI** | `.deepagents/skills/` | `~/.deepagents/langchain_agent/skills/` |

**Note:** The `config/AGENTS.md` file is primarily for reference and is **not copied** during installation (except for DeepAgents global installs where it defines the agent persona). It may be a helpful example to incorporate into your existing `CLAUDE.md` or `AGENTS.md` configuration.

## Prerequisites

- [Claude Code](https://claude.ai/claude-code) or [DeepAgents CLI](https://github.com/anthropics/deepagents-cli) installed
- A LangSmith API key (for tracing and evaluation features)

## Installation

```bash
# Install for Claude Code in current directory (default)
./install.sh

# Install for Claude Code globally
./install.sh --global

# Install for DeepAgents CLI in current directory
./install.sh --deepagents

# Install for DeepAgents CLI globally (includes agent persona)
./install.sh --deepagents --global
```

### Options

| Flag | Description |
|------|-------------|
| `--claude` | Install for Claude Code (default) |
| `--deepagents` | Install for DeepAgents CLI |
| `--global`, `-g` | Install globally instead of current directory |
| `--force`, `-f` | Overwrite skills with same names as this package |
| `--yes`, `-y` | Skip confirmation prompts |

## Usage

After installation, set your LangSmith API key:

```bash
export LANGSMITH_API_KEY=<your-key>
```

Then run your coding agent from the directory where you installed (for local installs) or from anywhere (for global installs).

## Available Skills

- **langchain-agents** - Build agents with LangChain ecosystem (primitives, context management, multi-agent patterns)
- **langsmith-trace** - Query and export traces from LangSmith
- **langsmith-dataset** - Generate test/evaluation datasets from exported traces (final_response, single_step, trajectory, RAG types) and upload to LangSmith
- **langsmith-evaluator** - Create custom evaluation metrics and link to datasets

## Development

Agent configuration lives in `config/`. To update an existing installation:

```bash
./install.sh --force
```

## Coming Soon

- JavaScript/TypeScript support
- More comprehensive LangGraph guidance
- More comprehensive DeepAgents guidance
- Additional LangSmith features
