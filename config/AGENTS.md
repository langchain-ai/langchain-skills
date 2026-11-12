# LangChain Ecosystem Development Guide

This project uses skills for current ecosystem guidance and workflows. Retrieve
implementation details from official documentation and verify them against the
installed package versions.

## Invoke the relevant skill before writing code

- **langchain-build-agent** - Invoke when building or modifying applications with Deep Agents, LangGraph, or LangChain, including architecture selection, middleware, memory, human review, composition, and retrieval. Follow its documentation lookup and fallback guidance.
- **langchain-eval-engineering** - Invoke to design or audit Harbor evaluation tasks.
- **langchain-agent-monitoring** - Invoke when monitoring an agent in production: choosing quality signals, designing or improving LangSmith online evaluations for runs or threads, and acting on the feedback.
- **langchain-agent-tracing** - Invoke when adding, fixing, or reviewing LangSmith tracing: instrumentation, agent environment or project destination, threads and metadata, sampling, redaction, distributed tracing, and finding traces after they land.

For LangSmith workspace operations, use an authenticated CLI profile when
the CLI supports the task; use the SDK for application tracing and evaluation
runs. Retrieve current instructions through the documentation MCP. For Custom
Apps, follow the CLI scaffold’s generated `AGENTS.md`. For offline evaluation
and experiment diagnosis, use current documentation and available tools.

## Environment setup

The skills and public documentation do not require model-provider credentials.
When running an application, configure credentials for the provider that
application uses.
