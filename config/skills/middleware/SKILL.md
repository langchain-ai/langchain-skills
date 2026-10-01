---
name: middleware
description: Add, remove, order, or debug agent middleware that changes prompts, tools, model calls, state, planning, summarization, guardrails, or execution behavior. Use when cross-cutting agent behavior should wrap the agent loop rather than become application control flow.
---

# Middleware

Inspect how the application constructs its agent and which middleware is
already active. Deep Agents is built from LangChain middleware and can also run
inside LangGraph, so identify which layer owns the behavior before changing it.

Use middleware for behavior that consistently wraps the agent loop, such as
dynamic prompts, tool filtering, model selection, summarization, task planning,
or policy checks. Use graph nodes and edges when the application needs explicit
business workflow or deterministic control flow.

For each middleware component:

- state the behavior it owns and when it runs;
- verify its required state schema and tools;
- check ordering and interaction with existing middleware;
- avoid duplicating behavior already supplied by the harness;
- test an observable path that triggers it.

Do not assume a middleware component is enabled by default. Verify defaults and
constructor APIs against the installed package version and current docs.

## References

- For LangChain agent middleware, read
  [LangChain](references/langchain.md).
- For Deep Agents middleware and task planning, read
  [Deep Agents](references/deep-agents.md).

LangGraph graph control flow is not agent middleware. Add a LangGraph reference
only if a future restructuring identifies framework-specific middleware there.
