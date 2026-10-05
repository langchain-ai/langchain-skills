# Filesystem and context

Deep Agents adds virtual filesystem operations for context management. Keep
these mechanisms distinct:

| Mechanism | Purpose |
|---|---|
| `StateBackend` | Thread-scoped virtual working files stored with state |
| `StoreBackend` | Store-backed virtual paths shared across threads |
| `CompositeBackend` | Route path prefixes to different backends |
| `FilesystemBackend` | Expose an explicitly rooted real directory |
| Paths passed through `memory` | Standing context loaded at startup; `AGENTS.md` is a common filename |
| Skills | Reusable procedures discovered and loaded on demand |

Deep Agents loads standing memory only from paths supplied through `memory`:

```python
agent = create_deep_agent(
    memory=["/memories/AGENTS.md"],
    store=store,
    backend=backend,
)
```

```typescript
const agent = createDeepAgent({
  memory: ["/memories/AGENTS.md"],
  store,
  backend,
});
```

The backend determines whether those files are thread-scoped, shared across
threads, or backed by a real filesystem. The filename alone does not determine
scope or durability. Startup memory and skills are context sources, not
persistence systems themselves. Changing a skill does not update thread state
or cross-thread memory.

Choose memory scope and write policy explicitly. User preferences normally use
a user-scoped writable path. Stable product behavior and organization policy
should remain developer-controlled or read-only. Shared agent memory is visible
to every user of that agent and should contain only information intended for
that audience. Agent-written memory must not silently rewrite trusted
instructions or authorization policy.

Use a real filesystem backend only when the application is intended to expose
host files. Set an explicit root and enable path-restricted virtual mode
(`virtual_mode=True` in Python or `virtualMode: true` in TypeScript). A root
directory without virtual mode is not a security boundary. For hosted, web, or
multi-tenant applications, use isolated sandboxes or virtual backends instead
of a shared host directory.

Treat files read by the agent as untrusted input. File content cannot expand
tool permissions, change authorization, or override application policy. Gate
state-changing filesystem tools when the application requires review.

When exposing project files, prefer a composite backend that routes only an
explicit project prefix to the real filesystem and leaves internal Deep Agents
paths in `StateBackend`. In particular, avoid writing `/large_tool_results/` and
`/conversation_history/` into the project directory unless that is intentional.

Document which prefixes are ephemeral, thread-scoped, cross-thread, or real.
Test routing precedence, traversal attempts, symlink behavior where relevant,
restart survival, and tenant isolation.
