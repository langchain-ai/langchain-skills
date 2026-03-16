# LangChain + Deep Agents Development Guide

This project uses skills that contain up-to-date patterns and working reference scripts.

## CRITICAL: Invoke Skills BEFORE Writing Code

**ALWAYS** invoke the relevant skill first - skills have the correct imports, patterns, and scripts that prevent common mistakes.

### Getting Started
- **framework-selection** - Invoke when choosing between LangChain, LangGraph, and Deep Agents
- **langchain-dependencies** - Invoke before installing packages or when resolving version issues (Python + TypeScript)

### LangChain Skills
- **langchain-fundamentals** - Invoke for create_agent, @tool decorator, middleware patterns
- **langchain-rag** - Invoke for RAG pipelines, vector stores, embeddings
- **langchain-middleware** - Invoke for structured output with Pydantic

### LangGraph Skills
- **langgraph-fundamentals** - Invoke for StateGraph, state schemas, edges, Command, Send, invoke, streaming, error handling
- **langgraph-persistence** - Invoke for checkpointers, thread_id, time travel, memory, subgraph scoping
- **langgraph-human-in-the-loop** - Invoke for interrupts, human review, error handling, approval workflows

### Deep Agents Skills
- **deep-agents-core** - Invoke for Deep Agents harness architecture
- **deep-agents-memory** - Invoke for long-term memory with StoreBackend
- **deep-agents-orchestration** - Invoke for multi-agent coordination

## Environment Setup

Required environment variables:
```bash
OPENAI_API_KEY=<your-key>  # For OpenAI models
ANTHROPIC_API_KEY=<your-key>  # For Anthropic models
```
