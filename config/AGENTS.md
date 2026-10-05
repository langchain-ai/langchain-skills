# LangChain + Deep Agents Development Guide

This project uses skills that contain up-to-date patterns and working reference scripts.

## CRITICAL: Invoke Skills BEFORE Writing Code

**ALWAYS** invoke the relevant skill first - skills have the correct imports, patterns, and scripts that prevent common mistakes.

### Getting Started
- **langchain-build-agent** - Invoke for new agent applications or broad “LangChain” requests that need architecture selection across the ecosystem

### Framework entrypoints
Invoke when building or modifying an application. Each skill routes to Python or TypeScript guidance:
- **langchain-framework** (LangChain framework components or the base create_agent/createAgent API)
- **langchain-langgraph** (StateGraph construction and explicit workflow control)
- **langchain-deep-agents** (routed Python and TypeScript quickstarts for new applications)

### LangChain Skills
- **langchain-framework** - Invoke for explicit LangChain framework APIs: models, tools, base create_agent/createAgent, structured output, and invocation

### LangGraph Skills
- **langchain-langgraph-cli** - Invoke for langgraph CLI commands: new, dev, build, up, deploy, and langgraph.json configuration
- **langchain-langgraph** - Invoke for StateGraph, state schemas, nodes, edges, Command, Send, invocation, streaming, and error handling

### Deep Agents Skills
- **langchain-deep-agents** - Invoke when building or modifying an application with the open-source Deep Agents harness
- **langchain-managed-deep-agents** - Invoke for Managed Deep Agents: build a code-first agent, add tools, middleware, MCP connectors, schedules, and sandboxes, and deploy with the `mda` CLI

### Shared Capability Skills
- **langchain-memory-and-persistence** - Invoke for thread state, durable memory, stores, checkpointers, and filesystem-backed context
- **langchain-human-in-the-loop** - Invoke for interrupts, review, approvals, edits, rejection, and resumption
- **langchain-subagents-and-composition** - Invoke for subagents, delegation, agent-as-tool patterns, and agent/graph composition
- **langchain-middleware** - Invoke for agent middleware, including task planning, prompts, tool wrapping, and summarization
- **langchain-retrieval-and-rag** - Invoke for ingestion, indexing, embeddings, vector stores, retrieval, citations, and retrieval tools

## Environment Setup

Required environment variables:

```bash
OPENAI_API_KEY=<your-key>  # For OpenAI models
ANTHROPIC_API_KEY=<your-key>  # For Anthropic models
```
