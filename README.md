# LangChain Skills

> **⚠️** — This project is in early development. APIs and skill content may change.

Agent skills for building agents with LangChain, LangGraph, and Deep Agents.

## Supported Coding Agents

These skills can be installed for the following AI coding agents:

| Agent | Local Install | Global Install |
|-------|---------------|----------------|
| **Claude Code** | `.claude/skills/` | `~/.claude/skills/` |
| **Deep Agents CLI** | `.deepagents/skills/` | `~/.deepagents/langchain_agent/skills/` |

**Note:** The `config/AGENTS.md` file is primarily for reference and is **not copied** during installation (except for Deep Agents global installs where it defines the agent persona). It may be a helpful example to incorporate into your existing `CLAUDE.md` or `AGENTS.md` configuration.

## Prerequisites

- [Claude Code](https://claude.ai/claude-code) or [Deep Agents CLI](https://docs.langchain.com/oss/python/deepagents/cli/overview) installed

## Installation

### Quick Install

Using [`npx skills`](https://github.com/vercel-labs/skills):

**Local** (current project):
```bash
npx skills add langchain-ai/langchain-skills --skill '*' --yes
```

**Global** (all projects):
```bash
npx skills add langchain-ai/langchain-skills --skill '*' --yes --global
```

To link skills to a specific agent (e.g. Claude Code):
```bash
npx skills add langchain-ai/langchain-skills --agent claude-code --skill '*' --yes --global
```

### Install Script

Alternatively, clone the repo and use the install script:

```bash
# Install for Claude Code in current directory (default)
./install.sh

# Install for Claude Code globally
./install.sh --global

# Install for Deep Agents CLI in current directory
./install.sh --deepagents

# Install for Deep Agents CLI globally (includes agent persona)
./install.sh --deepagents --global
```

| Flag | Description |
|------|-------------|
| `--claude` | Install for Claude Code (default) |
| `--deepagents` | Install for Deep Agents CLI |
| `--global`, `-g` | Install globally instead of current directory |
| `--force`, `-f` | Overwrite skills with same names as this package |
| `--yes`, `-y` | Skip confirmation prompts |

## Usage

After installation, set your API keys:

```bash
export OPENAI_API_KEY=<your-key>      # For OpenAI models
export ANTHROPIC_API_KEY=<your-key>   # For Anthropic models
```

Then run your coding agent from the directory where you installed (for local installs) or from anywhere (for global installs).

## Available Skills (11)

### Getting Started
- **framework-selection** - Framework comparison reference (LangChain vs LangGraph vs Deep Agents)
- **langchain-dependencies** - Full package version and dependency management reference (Python + TypeScript)

### Deep Agents
- **deep-agents-core** - Agent architecture, harness setup, and SKILL.md format
- **deep-agents-memory** - Memory, persistence, filesystem middleware
- **deep-agents-orchestration** - Subagents, task planning, human-in-the-loop

### LangChain
- **langchain-fundamentals** - Agents with create_agent, tools, structured output, middleware basics
- **langchain-middleware** - Human-in-the-loop approval, custom middleware, Command resume patterns
- **langchain-rag** - RAG pipeline (document loaders, embeddings, vector stores)

### LangGraph
- **langgraph-fundamentals** - StateGraph, nodes, edges, state reducers
- **langgraph-persistence** - Checkpointers, thread_id, cross-thread memory
- **langgraph-human-in-the-loop** - Interrupts, human review, approval workflows

## Development

Agent configuration lives in `config/`. To update an existing installation:

```bash
./install.sh --force
```
