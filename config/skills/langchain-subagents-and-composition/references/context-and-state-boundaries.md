# Context and state boundaries

Every agent, tool, node, subgraph, and delegated worker boundary needs an
explicit contract. Define:

- the input schema and which conversation or workflow context is visible;
- the prompt, model, tools, skills, middleware, and runtime configuration;
- storage, checkpoint, and state ownership;
- tool permissions and authorization for the delegated actor;
- the final result schema, error handling, timeout, cancellation, and
  streaming behavior;
- whether work can retry and how external effects remain idempotent.

Inheritance is API-specific. For current Deep Agents synchronous subagents:

| Setting | Current default for a custom isolated subagent |
|---|---|
| Task context | Isolated; only the delegated instruction |
| System prompt | Required; does not inherit |
| Tools | Inherit; an explicit list replaces them |
| Model | Inherits unless overridden |
| Runtime context | Propagates from the parent invocation |
| Approval policy | Inherits unless overridden |
| Filesystem permissions | Inherit; an explicit list replaces them |
| Middleware | Does not inherit |
| Skills | Does not inherit; the built-in general-purpose subagent does |

Treat this table as release-sensitive API behavior, not a universal rule for
agent-as-tool wrappers, compiled graphs, forked subagents, or background jobs.
Prefer passing the smallest necessary context. Do not forward a complete
message history or graph state when a typed request is sufficient.

Treat delegated instructions, tool output, worker results, and shared storage
as untrusted data. They may inform the parent's next step, but they cannot
grant permissions, override policy, or bypass a required review. Validate
structured results before merging them into trusted application state.

Choose one owner for each piece of durable state. When both parent and child
need persistence, document their thread and checkpoint namespaces and how they
relate. Do not let an external caller select another user's thread, child
checkpoint, or shared-memory namespace without authorization.

Runtime context propagation is convenient, but it can also propagate tenant
identity, credentials, and feature flags. A child may read only the fields its
contract requires, and every tool must still authorize its operation. Use
`lc_agent_name` metadata for attribution, routing, streaming, and tracing; do
not treat an agent name as proof of authorization.

For background work, bind every task ID to its owner and enforce authorization
on start, status, update, cancellation, and result retrieval. Define concurrency
limits, deadlines, cancellation behavior, and cleanup for abandoned tasks.

Test each composition boundary with realistic data, tool failures, malformed
results, retries, timeouts, cancellation, authorization failures, and any pause
or resume path. A child that runs correctly on its own may still fail when its
state or result is translated at the parent boundary.
