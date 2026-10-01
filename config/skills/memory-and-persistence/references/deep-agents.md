# Deep Agents memory and persistence

Read the application's Deep Agents language reference as well as this file.
Verify current constructor names and backend signatures against the installed
package and current documentation before editing code.

## Choose the correct mechanism

| Need | Deep Agents mechanism |
|---|---|
| Resume one thread | Checkpointer plus a stable `thread_id` |
| Persist virtual files within thread state | `StateBackend` |
| Share virtual files across threads | `StoreBackend` plus a store |
| Route paths to different storage | `CompositeBackend` |
| Access a local working directory | `FilesystemBackend` with an explicit root and path restrictions |
| Load standing project context | `AGENTS.md` or the configured memory source |
| Load reusable instructions on demand | Skills configuration |

`StateBackend` files are tied to checkpointed thread state. They are not
cross-thread memory. `StoreBackend` requires a store and persists only the paths
routed to it. A store's own durability still determines whether data survives
process restarts.

## Python: route persistent files

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()  # Replace with a durable store in production.

agent = create_deep_agent(
    store=store,
    backend=lambda runtime: CompositeBackend(
        default=StateBackend(runtime),
        routes={"/memories/": StoreBackend(runtime)},
    ),
)
```

Files under `/memories/` use the store; unmatched paths remain thread-scoped.
Use the same thread identifier to resume `StateBackend` contents.

## TypeScript: route persistent files

```typescript
import {
  CompositeBackend,
  createDeepAgent,
  StateBackend,
  StoreBackend,
} from "deepagents";
import { InMemoryStore } from "@langchain/langgraph";

const store = new InMemoryStore(); // Replace with durable storage in production.

const agent = await createDeepAgent({
  store,
  backend: (runtime) =>
    new CompositeBackend(
      new StateBackend(runtime),
      { "/memories/": new StoreBackend(runtime) },
    ),
});
```

Confirm the `CompositeBackend` constructor shape for the installed TypeScript
release; this API has changed across versions.

## Filesystem boundaries

Use `FilesystemBackend` only when the application is meant to expose a real
directory. Set an explicit root and enable the release's virtual path or
sandbox restriction. For web or multi-tenant applications, prefer isolated
state, store, or sandbox backends rather than exposing the host filesystem.

Test the properties the application depends on: same-thread resumption,
cross-thread visibility, process-restart durability, route-prefix behavior,
and tenant isolation.
