---
name: langchain-middleware
description: >-
  Add, remove, order, or debug agent middleware, including task lists and
  planning middleware, dynamic prompt adaptation, conversation or context
  summarization, model and tool wrappers, guardrails, and agent-loop hooks. Use
  when cross-cutting behavior should wrap the agent loop rather than become
  workflow control flow. Do not use for durable memory or explicit LangGraph
  nodes and edges.
---

# Middleware

Inspect how the application constructs its agent and which middleware is
already active. Deep Agents is built from LangChain middleware and can also run
inside LangGraph, so identify which layer owns the behavior before changing it.

Current Deep Agents include filesystem tools, summarization, synchronous
subagents, and prompt caching as core behavior. Task planning is opt-in. Check
the installed release because defaults and insertion details can change.

## Common triggers

- add an explicit task list or planning cycle around agent work;
- adapt the prompt, available tools, or model from request or state;
- summarize the active conversation or context before a model call; or
- wrap model or tool calls with guardrails, retries, telemetry, or policy checks.

Persisted information across threads belongs to memory and persistence. Use
graph nodes and edges for explicit business workflow or deterministic control
flow.

For each middleware component:

- state the behavior it owns and when it runs;
- verify its required state schema and tools;
- check ordering and interaction with existing middleware;
- avoid duplicating behavior already supplied by the harness;
- test an observable path that triggers it.

Treat tool filtering and prompt instructions as model guidance, not an
authorization boundary. Enforce permissions in the tool or service that owns
the protected operation.

## References

- To select an existing component or understand behavior already supplied by a
  Deep Agent, read [Built-in middleware](references/built-in-middleware.md).
- To implement agent-loop hooks or tool wrappers, read
  [Custom middleware](references/custom-middleware.md).
- To add an explicit task list for longer work, read
  [Task planning](references/task-planning.md).
- To combine components or extend agent state safely, read
  [Ordering and state](references/ordering-and-state.md).

LangGraph graph control flow is not agent middleware. A graph may contain an
agent whose loop uses middleware, but graph nodes and edges should keep
workflow control explicit.
