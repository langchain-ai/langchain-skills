---
name: memory-and-persistence
description: Add or modify application memory, durable state, conversation persistence, or filesystem-backed context. Use when an agent must remember within a thread, retain information across threads or restarts, or store working files; inspect the application's framework before choosing an implementation.
---

# Memory and persistence

Start with the behavior the application needs, then inspect its existing agent,
graph, storage, and deployment setup. Do not choose a framework from the user's
use of “LangChain” alone; LangChain agents, LangGraph workflows, and Deep Agents
can coexist in one application.

Distinguish these concerns before editing code:

- **Thread state** resumes one conversation or workflow using a checkpointer and
  a stable thread identity.
- **Durable memory** shares selected information across threads using a store.
- **Working files** give an agent virtual or real filesystem operations through
  a configured backend.
- **Startup instructions** such as `AGENTS.md` are loaded as standing context.
- **On-demand skills** are discovered and loaded when a task needs them; they
  are not a persistence layer.

Preserve the application's language, framework composition, storage system,
tenant boundaries, and deployment constraints. Use persistent production
storage when data must survive process restarts; in-memory implementations are
appropriate for examples and tests.

## References

- For a LangChain application, read
  [LangChain](references/langchain.md).
- For a LangGraph application, read
  [LangGraph](references/langgraph.md).
- For a Deep Agents application, read
  [Deep Agents](references/deep-agents.md).
