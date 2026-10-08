# Ordering and state

Middleware order is part of agent behavior. Inspect the complete active stack,
including components supplied by the Deep Agents harness, before inserting or
reordering a component. Preserve existing order unless the requested behavior
requires a change and test the interaction, not only each component alone.

Order is exact:

- before hooks run from first middleware to last;
- after hooks run from last middleware to first;
- wrap hooks nest, with the first middleware as the outermost wrapper.

For example, place retry middleware later than an error-conversion wrapper when
the outer wrapper should see only the final failure after retries are exhausted.

For every component, document:

- which hook it implements and whether it runs before, after, or around the
  underlying operation;
- the state and runtime fields it reads or writes;
- tools it adds, removes, filters, or wraps;
- whether it can short-circuit, retry, or replace a result;
- errors it handles and errors it preserves;
- whether it performs or can repeat an external side effect.

When middleware extends agent state, use the installed release's supported
schema mechanism and reducers. Avoid field names that collide with the agent,
harness, or another component. Keep persisted values serializable and do not
store credentials, open connections, functions, or request-scoped objects in
checkpointed state.

Node-style hooks return ordinary state updates. Python model wrappers can
return an `ExtendedModelResponse` carrying a `Command`; tool wrappers and
TypeScript wrappers use `Command` for state updates and control flow. Reducers
still apply. For fields without reducers, the outer middleware's update wins
when wrappers conflict. Commands from discarded retry attempts are discarded
with those attempts.

Declare any supported jump destinations with `can_jump_to` in Python or
`canJumpTo` in TypeScript. Do not hide undeclared workflow transitions inside a
hook.

Do not assume a delegated worker inherits the parent's stack. Deep Agent
subagents, agent-as-tool wrappers, and agents invoked from graph nodes need
their own explicit middleware and state configuration.

Test the expected order with observable behavior, including bypass conditions,
errors, retry, streaming, persistence, and any tool approval. Treat model,
tool, and stored state content as untrusted; middleware may enforce policy but
content cannot rewrite that policy or grant new permissions.

Tool filtering is useful for context and model behavior, but it is not access
control. The tool or downstream service must verify authorization.
