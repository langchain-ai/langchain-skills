# LangGraph subagents and composition

Use a subgraph when delegated work needs its own state and explicit control
flow. Use a node that invokes an agent when one graph step needs an agent loop.
Expose a compiled graph through a narrow tool when a parent agent only needs a
single input and result.

## Subgraph as a node

When parent and child use compatible state keys, add the compiled subgraph as a
node. When their schemas differ, use a wrapper node to translate input and
output explicitly.

### Python

```python
child = child_builder.compile()


def run_child(state: ParentState) -> dict:
    result = child.invoke({"query": state["request"]})
    return {"answer": result["response"]}


parent_builder.add_node("specialist", run_child)
```

### TypeScript

```typescript
const child = childBuilder.compile();

const runChild = async (state: typeof ParentState.State) => {
  const result = await child.invoke({ query: state.request });
  return { answer: result.response };
};

parentBuilder.addNode("specialist", runChild);
```

Define which layer owns checkpointing. Avoid accidentally compiling both parent
and child with independent persistence for the same logical state. If the child
interrupts, account for parent-node re-execution during resume.

## Agents in graph nodes

A node may invoke a LangChain agent or Deep Agent and translate its result into
graph state. Pass only the context it needs. Configure the contained agent's
tools, middleware, store, and permissions explicitly; graph state does not make
those dependencies implicit.

## Dynamic workers with Send

Return one `Send` per work item from a conditional edge. Each worker receives
the payload supplied to that `Send`, and its results merge into graph state. Add
a reducer for every field written by parallel workers, and make worker side
effects safe under retry.

Use `Send` for runtime fan-out when the number of workers depends on state. Use
fixed parallel edges when the branches are known while building the graph.

At every boundary, define state conversion, result shape, error propagation,
streaming behavior, persistence ownership, and authorization. Test composition
with realistic state rather than only compiling each component separately.
