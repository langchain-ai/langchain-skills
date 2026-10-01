# LangGraph human in the loop

`interrupt(value)` pauses graph execution and surfaces a serializable value to
the caller. `Command(resume=value)` continues the same checkpointed thread and
returns the resume value from the `interrupt` call.

A resumable graph requires a checkpointer, a stable thread identity, and an
authorized application path that displays the interrupt and resumes it.

## Python

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


def review(state: State) -> dict:
    decision = interrupt({"question": "Approve this draft?", "draft": state["draft"]})
    return {"approved": bool(decision["approved"])}


graph = (
    StateGraph(State)
    .add_node("review", review)
    .add_edge(START, "review")
    .add_edge("review", END)
    .compile(checkpointer=InMemorySaver())
)

config = {"configurable": {"thread_id": "review-123"}}
paused = graph.invoke({"draft": "..."}, config=config)
result = graph.invoke(Command(resume={"approved": True}), config=config)
```

## TypeScript

```typescript
import {
  Command,
  END,
  interrupt,
  MemorySaver,
  START,
  StateGraph,
} from "@langchain/langgraph";

const review = async (state: typeof State.State) => {
  const decision = interrupt({
    question: "Approve this draft?",
    draft: state.draft,
  }) as { approved: boolean };
  return { approved: decision.approved };
};

const graph = new StateGraph(State)
  .addNode("review", review)
  .addEdge(START, "review")
  .addEdge("review", END)
  .compile({ checkpointer: new MemorySaver() });

const config = { configurable: { thread_id: "review-123" } };
const paused = await graph.invoke({ draft: "..." }, config);
const result = await graph.invoke(
  new Command({ resume: { approved: true } }),
  config,
);
```

## Re-execution and side effects

When execution resumes, the interrupted node restarts from the beginning. Code
before `interrupt` runs again. Make preceding side effects idempotent, move them
after the interrupt when possible, or isolate them in another node. When a
subgraph interrupts, the parent node that invoked it may also re-execute.

Interrupt values and resume values must be serializable by the configured
checkpointer. Do not pass open connections, functions, or arbitrary runtime
objects.

For parallel interrupts, inspect the returned interrupt IDs and use the current
release's mapping form to resume the intended interrupts. Do not depend on list
order. Verify exact multiple-resume semantics against installed packages.

Authorize every resume using the owner of the thread and pending checkpoint.
Use a durable checkpointer outside development and test pause, process restart,
resume, rejection, repeated requests, and unauthorized access.
