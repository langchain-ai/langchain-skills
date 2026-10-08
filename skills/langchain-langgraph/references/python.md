# LangGraph Python

Use this reference for Python applications. Inspect installed versions and
current imports before editing an existing project. Current documentation:
<https://docs.langchain.com/oss/python/langgraph/overview>.

## Packages and versions

Inspect the dependency manifest and lockfile first. Preserve the existing
package manager and compatible versions, and add only packages required by the
graph and the components its nodes actually use. Verify current LangGraph,
LangChain integration, runtime, and checkpointer package requirements in
official documentation and installed metadata. Do not apply a repository-wide
version matrix. Verify imports and exercise the changed graph path afterward.

## Minimal graph

```python
from typing_extensions import NotRequired, TypedDict
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    input: str
    output: NotRequired[str]


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

## Functional API

Use `entrypoint` and `task` when ordinary Python control flow is clearer than an
explicit graph. Tasks return future-like values and their completed results can
be restored from a checkpoint during replay.

```python
from langgraph.func import entrypoint, task


@task
def normalize(value: str) -> str:
    return value.strip().upper()


@entrypoint()
def workflow(value: str) -> str:
    return normalize(value).result()


result = workflow.invoke(" hello ")
```

Entrypoint inputs, outputs, and task results must be serializable when the
workflow uses checkpointing. Put non-deterministic work and external effects in
tasks, and make effects idempotent because a task that started but did not
finish can run again.

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

Returning an empty list does not clear a field with an accumulating reducer.
Use `Overwrite` from `langgraph.types` when bypassing that reducer is
intentional.

For conversation state, use `MessagesState` or annotate a message field with
`add_messages`. This reducer appends new messages and replaces existing
messages by ID; plain list concatenation cannot safely support message edits.

## State and runtime boundaries

Use distinct input, output, and internal schemas when the graph's public
contract should expose only part of its working state. Nodes can also use
private channels for internal communication.

Private channels are omitted from the normal invocation output when an output
schema excludes them, but they are not redacted from full-state streaming.
Restrict stream `output_keys`, authorize stream access, and avoid putting
secrets in graph state.

Pass request-scoped dependencies through LangGraph runtime context. Define the
graph's context schema, receive `Runtime[Context]` in nodes, and supply context
at invocation. Do not checkpoint open connections, credentials, or caller
authorization as state.

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
design, use the shared `langchain-subagents-and-composition` skill.

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

For new integrations, prefer the typed event-streaming API, which exposes
separate projections for messages, values, subgraphs, and output. Preserve
`stream`/`astream` and their existing event contract when modifying a stream-mode
consumer.

When a checkpointed run resumes, an affected node starts again from the
beginning. Keep side effects idempotent, use stable operation keys, and split
completed effects into separate nodes or tasks when that improves replay safety.

Use the shared persistence and HITL references when invocation requires a
thread identifier, checkpointer, store, or interrupt.
