# LangGraph + LangSmith Agent Development

## Overview

You have access to skills for building agents with LangGraph and observing/evaluating them with LangSmith.

## Skills Available

- **langgraph-code** - Patterns for building agents (primitives, context management, multi-agent)
- **langsmith-trace** - Query and inspect agent execution traces
- **langsmith-dataset** - Generate evaluation datasets from traces
- **langsmith-evaluator** - Create custom evaluation metrics

## When Building Agents

**Start simple.** Use `create_agent` or basic ReAct loops before adding complexity.

**Manage context early.** If your agent handles long conversations or large state, consult `langgraph-code` section 2:
- Subagent delegation (offload work, return summaries)
- Filesystem context (store paths not content)
- Message trimming (keep recent only)
- Compression (summarize old context)

**Track execution.** Ensure `LANGSMITH_API_KEY` is set. Traces appear automatically at https://smith.langchain.com

## When Debugging/Evaluating

**Investigate failures:** Use `langsmith-trace` to query recent runs, filter by error status, export to JSON

**Create test sets:** Use `langsmith-dataset` to generate datasets from production traces (final_response, trajectory, single_step, RAG types)

**Define metrics:** Use `langsmith-evaluator` for custom evaluation (LLM as Judge for subjective quality, custom code for objective checks)

## Common Patterns

**Research agent:** Subagent delegation + filesystem + LLM as Judge

**SQL agent:** Simple ReAct loop + exact match evaluation

**Multi-agent:** Supervisor pattern + compressed outputs + trajectory datasets

**Long-running:** Hierarchical state + checkpointing + message trimming
