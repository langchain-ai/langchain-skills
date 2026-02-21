# LangChain Skills

> **⚠️ ALPHA** — This project is in early development. APIs and skill content may change.

Agent skills for building, observing, and evaluating agents with LangChain, LangGraph, LangSmith, and Deep Agents.

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

### Quick Install (Global)

Install globally with a single command:

**Claude Code:**
```bash
curl -fsSL https://github.com/langchain-ai/langchain-skills/archive/main.tar.gz | tar -xz -C /tmp && /tmp/langchain-skills-main/install.sh --global -y && rm -rf /tmp/langchain-skills-main
```

**DeepAgents CLI:**
```bash
curl -fsSL https://github.com/langchain-ai/langchain-skills/archive/main.tar.gz | tar -xz -C /tmp && /tmp/langchain-skills-main/install.sh --deepagents --global -y && rm -rf /tmp/langchain-skills-main
```

### Manual Install

Clone the repo and run the install script for more options:

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

After installation, set your API keys:

```bash
export LANGSMITH_API_KEY=<your-key>
export OPENAI_API_KEY=<your-key>      # For OpenAI models
export ANTHROPIC_API_KEY=<your-key>   # For Anthropic models
```

Then run your coding agent from the directory where you installed (for local installs) or from anywhere (for global installs).

## Available Skills (16)

### Getting Started
- **langchain-agent-starter-kit** - **Always start here** — framework selection + dependency setup combined into a single starting reference
- **framework-selection** - Framework comparison reference (LangChain vs LangGraph vs Deep Agents)
- **langchain-dependencies** - Full package version and dependency management reference (Python + TypeScript)

### Deep Agents
- **deep-agents-core** - Agent architecture, harness setup, and SKILL.md format
- **deep-agents-memory** - Memory, persistence, filesystem middleware
- **deep-agents-orchestration** - Subagents, task planning, human-in-the-loop

### LangChain
- **langchain-agents** - Agents and tools with create_react_agent, @tool decorator
- **langchain-fundamentals** - Chat models, provider setup, streaming
- **langchain-output** - Structured output with Pydantic, HITL middleware
- **langchain-rag** - RAG pipeline (document loaders, embeddings, vector stores)

### LangGraph
- **langgraph-fundamentals** - StateGraph, nodes, edges, state reducers
- **langgraph-persistence** - Checkpointers, thread_id, cross-thread memory
- **langgraph-execution** - Workflows, interrupts, streaming modes

### LangSmith
- **langsmith-trace** - Query and export traces (includes helper scripts)
- **langsmith-dataset** - Generate evaluation datasets from traces (includes helper scripts)
- **langsmith-evaluator** - Create custom evaluators (includes helper scripts)

**Note:** LangSmith skills include Python and TypeScript helper scripts for common operations.

## Development

Agent configuration lives in `config/`. To update an existing installation:

```bash
./install.sh --force
```
