# LangGraph + LangSmith Skills for DeepAgents CLI

**Alpha** — Agent skills for building, observing, and evaluating LangGraph agents with LangSmith.

> **This repository contains installable skills for [deepagents-cli](https://github.com/anthropics/deepagents-cli).** Skills extend the CLI's capabilities by providing specialized knowledge and tools for specific domains.

### Current Limitations

These skills are currently focused on **ReAct-style agents** that call tools in a loop. Support for other agent architectures is coming soon.

## Prerequisites

- [deepagents-cli](https://github.com/anthropics/deepagents-cli) installed
- A LangSmith API key (for tracing and evaluation features)

## Installation

```bash
./install.sh
```

Prompts for agent name (default: `langchain_agent`) and installation directory (default: `~/.deepagents`), then installs the agent with AGENTS.md and skills.

## Usage

```bash
deepagents --agent langchain_agent
export LANGSMITH_API_KEY=<your-key>
```

## Available Skills

- **langchain-agents** - Build agents with LangChain ecosystem (primitives, context management, multi-agent patterns)
- **langsmith-trace** - Query and export traces from LangSmith
- **langsmith-dataset** - Generate test/evaluation datasets from exported traces (final_response, single_step, trajectory, RAG types) and upload to LangSmith
- **langsmith-evaluator** - Create custom evaluation metrics and link to datasets

## Development

Agent configuration lives in `config/`. To update:

```bash
rm -rf ~/.deepagents/langchain_agent
./install.sh
```

## Coming Soon

- JavaScript/TypeScript support
- Tracing support for wider agent architectures
- Dataset generation for non-ReAct agents
- Evaluator patterns for diverse agent types
