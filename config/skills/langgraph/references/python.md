# LangGraph Python

Use this reference for Python applications. Inspect installed versions and
current imports before editing an existing project. Current documentation:
<https://docs.langchain.com/oss/python/langgraph/overview>.

## Minimal graph

```python
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    input: str
    output: str


def process(state: State) -> dict:
    return {"output": state["input"].upper()}


graph = (
    StateGraph(State)
    .add_node("process", process)
    .add_edge(START, "process")
    .add_edge("process", END)
    .compile()
)

result = graph.invoke({"input": "hello"})
```

For a new application, create it where the user requested and preserve their
provider and package choices. For an existing application, extend its state and
graph rather than creating an unrelated demo.

## State and reducers

```python
import operator
from typing import Annotated
from typing_extensions import TypedDict


class State(TypedDict):
    latest: str                         # overwrites
    results: Annotated[list[str], operator.add]  # accumulates
```

Return only updates such as `{"latest": "done"}`. Do not mutate and return the
incoming state. Reducer update values must match the reducer's expected type.

## Routing with Command

```python
from typing import Literal
from langgraph.types import Command


def route(state: State) -> Command[Literal["review", "finish"]]:
    destination = "review" if state["needs_review"] else "finish"
    return Command(update={"routed": True}, goto=destination)
```

Do not add an unintended static edge from `route`; a `Command` route and a
static edge both execute. `START` is entry-only, so route loops through a named
node.

## Parallel fan-out with Send

```python
from langgraph.types import Send


def dispatch(state: State):
    return [Send("worker", {"task": task}) for task in state["tasks"]]
```

The receiving result field needs a reducer. For broader worker and subgraph
design, use the `subagents-and-composition` LangGraph reference.

## Invoke, stream, and errors

```python
result = graph.invoke({"input": "hello"})

for update in graph.stream({"input": "hello"}, stream_mode="updates"):
    print(update)
```

Choose `values` for complete state, `updates` for deltas, `messages` for model
tokens and metadata, and `custom` for application progress. Add a `RetryPolicy`
to nodes that perform transient network operations. Compile before invoking and
ensure every conditional router returns a registered node or `END`.

Use the shared persistence and HITL references when invocation requires a
thread identifier, checkpointer, store, or interrupt.
