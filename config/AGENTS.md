# LangChain + Deep Agents Development Guide

This project uses skills that contain up-to-date patterns and working reference scripts.

## CRITICAL: Invoke Skills BEFORE Writing Code

**ALWAYS** invoke the relevant skill first - skills have the correct imports, patterns, and scripts that prevent common mistakes.

### Getting Started
- **build-agent** - Invoke for new or ambiguous agent applications that need architecture selection across LangChain, LangGraph, Deep Agents, or Managed Deep Agents
- **langchain-dependencies** - Invoke before installing packages or when resolving version issues (Python + TypeScript)

### Framework entrypoints
Invoke when building or modifying an application. Each skill routes to Python or TypeScript guidance:
- **langchain** (routes to Python or TypeScript guidance for new and existing applications)
- **langgraph** (StateGraph construction and explicit workflow control)
- **deep-agents** (routed Python and TypeScript quickstarts for new applications)

### LangChain Skills
- **langchain** - Invoke for LangChain models, create_agent/createAgent, tools, structured output, and agent invocation
- **langchain-rag** - Invoke for RAG pipelines, vector stores, embeddings

### LangGraph Skills
- **langgraph-cli** - Invoke for langgraph CLI commands: new, dev, build, up, deploy, and langgraph.json configuration
- **langgraph** - Invoke for StateGraph, state schemas, nodes, edges, Command, Send, invocation, streaming, and error handling

### Deep Agents Skills
- **deep-agents** - Invoke when building or modifying an application with the open-source Deep Agents harness
- **managed-deep-agents** - Invoke for Managed Deep Agents: build a code-first agent, add tools, middleware, MCP connectors, schedules, and sandboxes, and deploy with the `mda` CLI

### Shared Capability Skills
- **memory-and-persistence** - Invoke for thread state, durable memory, stores, checkpointers, and filesystem-backed context
- **human-in-the-loop** - Invoke for interrupts, review, approvals, edits, rejection, and resumption
- **subagents-and-composition** - Invoke for subagents, delegation, agent-as-tool patterns, and agent/graph composition
- **middleware** - Invoke for agent middleware, including task planning, prompts, tool wrapping, and summarization

## Environment Setup

Required environment variables:

```bash
OPENAI_API_KEY=<your-key>  # For OpenAI models
ANTHROPIC_API_KEY=<your-key>  # For Anthropic models
```
