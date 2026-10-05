# Production storage

Choose storage from the required durability and isolation properties, not from
the framework wrapper that consumes it.

Use a database-backed checkpointer when threads must survive process restart,
deployment, or worker failover. Use a durable store when cross-thread memory
must survive those events. Initialize database schemas during deployment or an
explicit migration step rather than on every application request.

LangGraph persistence implementations ship in provider packages. Select a
supported checkpointer and store for the application's database, use their async
variants in async applications, and run required `setup` or migration methods
once as part of deployment. Do not infer production durability from an
in-memory implementation or a long-lived development process.

When using LangSmith Agent Server, let the platform-provisioned persistence
infrastructure own checkpointers and stores. Do not add a second application
checkpointer unless the design intentionally requires a separate persistence
domain.

Define and test:

- ownership and authorization for threads, checkpoints, history, and stores;
- tenant and user namespace isolation;
- encryption, backup, retention, deletion, and regional requirements;
- serialization compatibility across application versions;
- behavior when a checkpoint or memory write partially fails;
- cleanup for abandoned threads, sandboxes, and stored files.

Persist only serializable state supported by the configured backend. Do not put
open connections, functions, raw credentials, or non-portable runtime objects
into checkpoints, interrupt payloads, or stores.

Keep request-scoped dependencies and authenticated tenant or user identity in
runtime context. Runtime context is supplied for each run and is not restored
from a checkpoint. Use it to derive authorized store namespaces and filesystem
routes rather than trusting model-generated identifiers.

Use the checkpointer's supported serializer deliberately. If persisted state
contains sensitive data, configure encryption through the backend or an
encrypted serializer and manage encryption keys outside checkpointed state.
Plan serializer and schema compatibility before rolling application versions
back or forward.

Retention is not automatic across every backend. Define separate policies for
thread checkpoints, cross-thread store items, uploaded files, and sandbox data.
Use backend or platform TTL features where supported; otherwise schedule
authorized deletion. Verify that user deletion removes every applicable layer
and any derived semantic index entries.

Nested graphs and agents need an explicit persistence owner. Avoid configuring
independent parent and child storage for the same logical state unless that
separation is intentional. A subgraph normally inherits the parent
checkpointer for per-invocation persistence. Compile it with `checkpointer=True`
only when it needs state across calls in the same thread, or `False` when it must
be stateless. Do not call the same per-thread stateful subgraph more than once
concurrently inside one node because those calls share a checkpoint namespace.

Test same-thread resumption, cross-thread memory, process restart, worker
failover, unauthorized access, deletion, and schema migration as separate
properties. Also test async startup and shutdown, retention jobs, encryption
key availability, and rollback across serializer or schema changes. A passing
in-memory test demonstrates API wiring, not production durability.
