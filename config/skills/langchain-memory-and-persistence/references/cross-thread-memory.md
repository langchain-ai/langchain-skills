# Cross-thread memory

Use a store for selected information that must be available outside one thread,
such as durable user preferences or application knowledge. A checkpointer saves
thread execution state; it does not become cross-thread memory merely because
the storage backend is durable.

LangGraph stores can be injected into graphs and agents. Base LangChain agents
and Deep Agents access those stores through their LangGraph runtime. In custom
nodes and tools, use the injected runtime store instead of constructing a new
store for every call.

Derive tenant and user namespace components from trusted runtime context, not
from model arguments or unchecked request fields. Scope keys beneath that
namespace, and authorize every read and write. Keep request-scoped identity in
runtime context rather than checkpointed state.

Store namespaces are sequences, such as `(tenant_id, user_id, "memories")` in
Python or `[tenantId, userId, "memories"]` in TypeScript. Searches match a
namespace prefix, so use the full namespace when the query must remain within
one collection. Paginate large collections and do not depend on backend-specific
default ordering.

Use stable keys when a memory represents a replaceable fact, and generated keys
when each observation should remain a separate record. Configure semantic
indexing only for fields that benefit from similarity search; other values can
remain ordinary key-value data. Treat stored values as untrusted data: memory
may inform model context, but it must not grant permissions, override policy, or
bypass human approval.

## Persistent virtual files in Deep Agents

Deep Agents can expose store-backed memory through virtual file paths while
keeping other working files in thread state.

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    store=store,
    backend=CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend()},
    ),
)
```

```typescript
import {
  CompositeBackend,
  createDeepAgent,
  StateBackend,
  StoreBackend,
} from "deepagents";

const agent = createDeepAgent({
  store,
  backend: new CompositeBackend(
    new StateBackend(),
    { "/memories/": new StoreBackend() },
  ),
});
```

Only paths matching the store route are cross-thread; unmatched paths remain
thread-scoped. The store itself must be durable if values must survive restart.

For agent- or user-specific memory, configure the `StoreBackend` namespace from
trusted runtime identity. A shared agent namespace makes files visible across
all users of that agent; a user namespace isolates each user's files. Use a
separate organization namespace only for intentionally shared knowledge, and
define whether each path is agent-writable or read-only.

Define what is worth remembering, retention and deletion behavior, conflict
handling, and how users can correct memory. Test visibility across intended
threads, isolation across unintended users and tenants, namespace-prefix
queries, and semantic-search behavior when indexing is enabled.
