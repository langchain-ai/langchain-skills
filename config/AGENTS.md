# LangChain + Deep Agents Development Guide

This project uses skills for current ecosystem guidance and workflows. Retrieve
implementation details from official documentation and verify them against the
installed package versions.

## Invoke the relevant skill before writing code

- **langchain-build-agent** - Invoke when building or modifying applications with Deep Agents, LangGraph, or LangChain, including architecture selection, middleware, memory, human review, composition, and retrieval. Follow its documentation lookup and fallback guidance.
- **langchain-managed-deep-agents** - Invoke for Managed Deep Agents and the hosted runtime: tools, middleware, MCP connectors, schedules, sandboxes, and deployment with the `mda` CLI.
- **langchain-langgraph-cli** - Invoke for LangGraph CLI commands: new, dev, build, up, deploy, and langgraph.json configuration.
- **langchain-eval-engineering** - Invoke to design or audit Harbor evaluation tasks.
- **langchain-swarm** - Invoke when asked to dispatch independent work items in parallel and aggregate results.

## Environment Setup

Required environment variables:

```bash
OPENAI_API_KEY=<your-key>  # For OpenAI models
ANTHROPIC_API_KEY=<your-key>  # For Anthropic models
```
