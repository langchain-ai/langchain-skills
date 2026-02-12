# LangGraph + LangSmith Skills for DeepAgents CLI

> **⚠️ ALPHA** — This project is in early development. APIs and skill content may change.

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
- More comprehensive LangGraph guidance
- More comprehensive DeepAgents guidance
- Additional LangSmith features
