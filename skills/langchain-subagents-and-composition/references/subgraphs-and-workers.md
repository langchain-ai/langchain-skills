# Subgraphs and workers

Use a subgraph when delegated work needs its own state and explicit control
flow. Use a node that invokes an agent when one graph step needs an agent loop.
Use dynamic workers when the number of parallel tasks depends on runtime state.

## Subgraph as a node

When parent and child use compatible state keys, a compiled subgraph can be a
node. When their schemas differ, translate the input and result explicitly.

```python
child = child_builder.compile()


def run_child(state: ParentState) -> dict:
    result = child.invoke({"query": state["request"]})
    return {"answer": result["response"]}


parent_builder.add_node("specialist", run_child)
```

```typescript
const child = childBuilder.compile();

const runChild = async (state: typeof ParentState.State) => {
  const result = await child.invoke({ query: state.request });
  return { answer: result.response };
};

parentBuilder.addNode("specialist", runChild);
```

A node may invoke a base LangChain agent or Deep Agent and translate its final
result into graph state. Configure that contained agent explicitly; graph state
does not supply its tools, middleware, store, or permissions.

Subgraph checkpointing controls state lifetime:

| Compile setting | Behavior |
|---|---|
| Omitted / `None` | Per-invocation persistence inherited from the parent |
| `True` | Per-thread state retained across calls |
| `False` | Stateless; no interrupts or checkpointed subgraph state |

Do not invoke the same per-thread stateful subgraph more than once concurrently
inside one node. Those calls share a checkpoint namespace. Use per-invocation
persistence or separate stateful graph instances when calls must run in
parallel.

## Dynamic workers

Use LangGraph `Send` to return one worker invocation per runtime work item.
Each worker receives only the payload supplied to that `Send`. Add a reducer
for every graph-state field written by parallel workers, and make external
effects safe under retry. Use fixed parallel edges when branches are known
while building the graph.

```python
from langgraph.types import Send


def assign_workers(state: State):
    return [Send("worker", {"item": item}) for item in state["items"]]
```

```typescript
import { Send } from "@langchain/langgraph";

const assignWorkers = (state: typeof State.State) =>
  state.items.map((item) => new Send("worker", { item }));
```

Return `Send` objects from a conditional edge. Define an associative reducer for
every parent-state field that collects parallel results; without one, concurrent
writes can conflict. Bound the number of work items and concurrent workers,
define per-worker timeouts, and decide whether one failure cancels the batch,
is recorded beside successful results, or is retried. Preserve stable item IDs
so retries and result aggregation cannot duplicate external effects.

Define which layer owns checkpointing. Avoid independent parent and child
persistence for the same logical state unless the separation is intentional.
If a child interrupts, account for the parent node re-executing during resume.
Stream subgraph or worker events with namespace information when the UI or
operator needs progress, but keep worker internals out of the parent prompt
unless they are part of the result contract.
