---
name: langchain-memory-and-persistence
description: Add or modify application memory, durable state, conversation persistence, or filesystem-backed context. Use when an agent or workflow must resume within a thread, retain selected information across threads or restarts, or store working files; choose the persistence behavior before selecting its APIs.
---

# Memory and persistence

Start with the behavior the application needs, then inspect its existing agent,
graph, storage, and deployment setup. LangChain agents and Deep Agents use
LangGraph persistence primitives, while Deep Agents also provides virtual
filesystem backends. Configure these layers together rather than treating them
as separate persistence systems.

Distinguish these concerns before editing code:

- **Thread state** resumes one conversation or workflow using a checkpointer and
  a stable thread identity.
- **Durable memory** shares selected information across threads using a store.
- **Working files** give an agent virtual or real filesystem operations through
  a configured backend.
- **Startup memory files** are loaded as standing context only when the agent is
  configured to load their paths. `AGENTS.md` is a useful convention, not an
  automatically discovered persistence mechanism.
- **On-demand skills** are discovered and loaded when a task needs them; they
  are not a persistence layer.

Keep request-scoped identity and dependencies in runtime context rather than
checkpointed state. Use trusted runtime identity to choose tenant and user
namespaces; runtime context is supplied for a run and is not durable memory.

Preserve the application's language, framework composition, storage system,
tenant boundaries, and deployment constraints. Use persistent production
storage when data must survive process restarts; in-memory implementations are
appropriate for examples and tests.

## References

- To resume a conversation or workflow within one thread, read
  [Thread state](references/thread-state.md).
- To retain selected information across threads, read
  [Cross-thread memory](references/cross-thread-memory.md).
- To configure virtual files, real files, startup context, or skills, read
  [Filesystem and context](references/filesystem-and-context.md).
- For restart survival, tenant isolation, retention, and deployment concerns,
  read [Production storage](references/production-storage.md).
