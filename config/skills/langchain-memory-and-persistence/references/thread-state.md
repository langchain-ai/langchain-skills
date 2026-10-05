# Thread state

Thread state resumes one logical conversation or workflow. LangGraph provides
the checkpointer abstraction used by compiled graphs, base LangChain agents,
and Deep Agents. The wrappers differ, but the invariant is the same: configure
a checkpointer and reuse a stable thread identity.

## Python

```python
from deepagents import create_deep_agent
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
config = {"configurable": {"thread_id": "conversation-123"}}

graph = graph_builder.compile(checkpointer=checkpointer)
graph.invoke({"input": "hello"}, config=config)

# Base LangChain agents and Deep Agents accept the same persistence primitive:
base_agent = create_agent(model=model, tools=tools, checkpointer=checkpointer)
deep_agent = create_deep_agent(model=model, tools=tools, checkpointer=checkpointer)
```

## TypeScript

```typescript
import { createDeepAgent } from "deepagents";
import { createAgent } from "langchain";
import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();
const config = { configurable: { thread_id: "conversation-123" } };

const graph = graphBuilder.compile({ checkpointer });
await graph.invoke({ input: "hello" }, config);

const baseAgent = createAgent({ model, tools, checkpointer });
const deepAgent = createDeepAgent({ model, tools, checkpointer });
```

In-memory savers are suitable for development and tests. They do not prove that
state survives process restart.

Thread state is not cross-thread memory. Different thread identifiers should be
isolated. Authorize reads, history, updates, replay, and resume operations
against the thread owner rather than accepting an arbitrary identifier.

## Inspect, update, and replay

Use `get_state`/`getState` for the latest snapshot, or include both a
`thread_id` and `checkpoint_id` to inspect a particular checkpoint. Use
`get_state_history`/`getStateHistory` to enumerate history; current
implementations return the newest checkpoint first.

A checkpoint contains state values, the nodes scheduled next, its checkpoint
configuration and parent, execution metadata, and pending tasks or interrupts.
Treat `checkpoint_ns` as framework-managed routing for a graph or subgraph, not
as an application authorization boundary.

Use `update_state`/`updateState` to create a new checkpoint based on an existing
one. State updates pass through the graph's reducers, so an update to an
accumulating field may append rather than replace. Inspect the state schema and
specify the source node when the next edge cannot be inferred safely.

Invoking from an earlier `checkpoint_id` creates a new history branch. LangGraph
replays steps that precede that checkpoint and executes steps after it; it does
not mutate the original history. Nodes and tasks after the fork point can run
again, so their side effects must be idempotent.

## Subgraph persistence

Subgraphs use the parent graph's checkpointer, but their compile setting controls
the lifetime of their own state:

| Setting | Behavior |
|---|---|
| Default (`None` / omitted) | Per-invocation persistence; supports interrupts without retaining subgraph memory across separate calls |
| `True` | Per-thread persistence; retains subgraph state across calls in the same thread |
| `False` | Stateless; no subgraph checkpointing or interrupts |

Do not invoke the same per-thread stateful subgraph more than once concurrently
inside one node. Those calls share a checkpoint namespace and conflict. Use
per-invocation persistence for parallel calls, or give each stateful subgraph a
separate graph instance and namespace.

Test same-thread continuation, different-thread isolation, and the exact
application path that supplies configuration to nested graphs and agents. Also
test history inspection, replay, and any state update used by an operator or UI.
