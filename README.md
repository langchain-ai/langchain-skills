# LangGraph + LangSmith Skills for DeepAgents CLI

Agent skills for building, observing, and evaluating LangGraph agents with LangSmith.

> **This repository contains installable skills for [deepagents-cli](https://github.com/anthropics/deepagents-cli).** Skills extend the CLI's capabilities by providing specialized knowledge and tools for specific domains.

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
- **langsmith-trace** - Query and inspect traces
- **langsmith-dataset** - Generate evaluation datasets from traces
- **langsmith-evaluator** - Create custom evaluation metrics

## Development

Agent configuration lives in `config/`. To update:

```bash
rm -rf ~/.deepagents/langchain_agent
./install.sh
```
