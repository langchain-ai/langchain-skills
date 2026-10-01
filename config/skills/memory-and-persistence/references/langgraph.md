# LangGraph memory and persistence

LangGraph checkpointers save graph state as checkpoints within a thread. A
stable thread identity resumes that state. Stores hold selected information
outside a single thread. Keep these mechanisms distinct.

## Development checkpointing

### Python

```python
from langgraph.checkpoint.memory import InMemorySaver

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "thread-123"}}
result = graph.invoke({"input": "hello"}, config=config)
```

### TypeScript

```typescript
import { MemorySaver } from "@langchain/langgraph";

const graph = builder.compile({ checkpointer: new MemorySaver() });
const config = { configurable: { thread_id: "thread-123" } };
const result = await graph.invoke({ input: "hello" }, config);
```

In-memory savers are for development and tests. Use the database-backed saver
supported by the application's deployment when state must survive restart.
Initialize its schema during deployment rather than on every request.

## State history and updates

Use `get_state`/`getState` for the current snapshot and
`get_state_history`/`getStateHistory` for checkpoints in one thread. A replay
uses a prior checkpoint configuration. `update_state`/`updateState` writes an
update through the graph's reducers; it does not necessarily replace an
accumulating field.

Authorize access to thread state, checkpoint history, replay, and state updates.
Never accept an arbitrary thread or checkpoint identifier without checking its
owner.

## Cross-thread memory

Compile with a store when nodes or agents must share selected memory across
threads. Access the injected store through the runtime API supported by the
installed release. Scope keys or namespaces by tenant and user. An in-memory
store still loses data on process restart.

## Subgraph persistence

Subgraphs inherit or configure checkpointing according to the installed
LangGraph version. Choose the mode from behavior:

- no checkpointing when the subgraph needs neither interrupts nor persistence;
- inherited/default checkpointing for invocation-local pause and resume;
- stateful checkpointing when the same logical subgraph must remember across
  invocations.

Stateful subgraphs need stable, isolated checkpoint namespaces. Verify current
rules before invoking the same stateful subgraph concurrently or multiple times
from one node. Put subgraph composition mechanics in the
`subagents-and-composition` skill.

Test same-thread resumption, thread isolation, process restart, history access,
and store namespace isolation as separate properties.
