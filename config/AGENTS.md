# LangChain + LangSmith + DeepAgents Development Guide

This project uses skills that contain up-to-date patterns and working reference scripts.

## CRITICAL: Invoke Skills BEFORE Writing Code

**ALWAYS** invoke the relevant skill first - skills have the correct imports, patterns, and scripts that prevent common mistakes.

### Getting Started
- **framework-selection** - Invoke when choosing between LangChain, LangGraph, and Deep Agents
- **langchain-dependencies** - Invoke before installing packages or when resolving version issues (Python + TypeScript)

### LangSmith Skills
- **langsmith-trace** - Invoke for ANY trace querying or analysis
- **langsmith-dataset** - Invoke for ANY dataset creation from traces
- **langsmith-evaluator** - Invoke for ANY evaluator creation

### LangChain Skills
- **langchain-fundamentals** - Invoke for create_agent, @tool decorator, middleware patterns
- **langchain-rag** - Invoke for RAG pipelines, vector stores, embeddings
- **langchain-output** - Invoke for structured output with Pydantic

### LangGraph Skills
- **langgraph-fundamentals** - Invoke for StateGraph, state schemas, reducers
- **langgraph-persistence** - Invoke for checkpointers, thread_id, memory
- **langgraph-execution** - Invoke for workflows, interrupts, streaming

### DeepAgents Skills
- **deep-agents-core** - Invoke for DeepAgents harness architecture
- **deep-agents-memory** - Invoke for long-term memory with StoreBackend
- **deep-agents-orchestration** - Invoke for multi-agent coordination

## Debugging Flow: Build → Trace → Dataset → Evaluate

When stuck or debugging, use this powerful workflow:
1. **Build agent** using LangChain, DeepAgents, or LangGraph patterns
2. **Run agent** to generate traces in LangSmith
3. **Query traces** using `langsmith-trace` to find interesting examples
4. **Create dataset** using `langsmith-dataset` from those traces
5. **Build evaluator** using `langsmith-evaluator` to measure quality

Each skill includes reference scripts in `scripts/` - use these instead of writing from scratch.

## Environment Setup

Required environment variables:
```bash
LANGSMITH_API_KEY=<your-key>
LANGSMITH_PROJECT=<project-name>  # Optional, defaults to "default"
OPENAI_API_KEY=<your-key>  # For OpenAI models
ANTHROPIC_API_KEY=<your-key>  # For Anthropic models
```