# LangChain Ecosystem Development Guide

This project uses skills for current ecosystem guidance and workflows. Retrieve
implementation details from official documentation and verify them against the
installed package versions.

## Invoke the relevant skill before writing code

- **langchain-build-agent** - Invoke when building or modifying applications with Deep Agents, LangGraph, or LangChain, including architecture selection, middleware, memory, human review, composition, and retrieval. Follow its documentation lookup and fallback guidance.
- **langchain-eval-engineering** - Invoke to design or audit Harbor evaluation tasks.
- **langchain-langsmith** - Invoke for LangSmith trace inspection, workspace operations, dataset experiments, result diagnosis, or online feedback.

For LangSmith workspace operations, use an authenticated CLI profile when
the CLI supports the task; use the SDK for application tracing and evaluation
runs. Retrieve current instructions through the documentation MCP. For Custom
Apps, follow the CLI scaffold’s generated `AGENTS.md`. For evaluation
work, read the skill’s linked evaluation reference.

## Environment setup

The skills and public documentation do not require model-provider credentials.
When running an application, configure credentials for the provider that
application uses.
