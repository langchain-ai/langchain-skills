# LangGraph TypeScript

Use this reference for TypeScript applications. Inspect installed versions and
current imports before editing an existing project. Current documentation:
<https://docs.langchain.com/oss/javascript/langgraph/overview>.

## Packages and versions

Inspect `package.json`, the lockfile, and workspace configuration first.
Preserve the existing package manager and compatible versions, and add only
packages required by the graph and the components its nodes use. Verify current
LangGraph, LangChain integration, Node.js, peer-dependency, and checkpointer
requirements in official documentation and installed metadata. Avoid a static
version matrix. Verify imports and exercise the changed graph path afterward.

## Minimal graph

```typescript
import { END, START, StateGraph, StateSchema } from "@langchain/langgraph";
import { z } from "zod/v4";

const State = new StateSchema({
  input: z.string(),
  output: z.string().default(""),
});

const process = async (state: typeof State.State) => ({
  output: state.input.toUpperCase(),
});

const graph = new StateGraph(State)
  .addNode("process", process)
  .addEdge(START, "process")
  .addEdge("process", END)
  .compile();

const result = await graph.invoke({ input: "hello" });
```

For a new application, create it where requested and preserve the user's package
manager and provider choices. Confirm the supported Node.js version in current
documentation.

## Functional API

Use `entrypoint` and `task` when ordinary TypeScript control flow is clearer
than an explicit graph. Completed task results can be restored from a
checkpoint during replay.

```typescript
import { entrypoint, task } from "@langchain/langgraph";

const normalize = task("normalize", async (value: string) =>
  value.trim().toUpperCase(),
);

const workflow = entrypoint(
  { name: "workflow" },
  async (value: string) => normalize(value),
);

const result = await workflow.invoke(" hello ");
```

Entrypoint inputs, outputs, and task results must be serializable when the
workflow uses checkpointing. Put non-deterministic work and external effects in
tasks, and make effects idempotent because a task that started but did not
finish can run again.

## State and reducers

```typescript
import { ReducedValue, StateSchema } from "@langchain/langgraph";
import { z } from "zod/v4";

const State = new StateSchema({
  latest: z.string().default(""),
  results: new ReducedValue(
    z.array(z.string()).default(() => []),
    { reducer: (current, update) => current.concat(update) },
  ),
});
```

Return partial updates rather than mutating state. Without `ReducedValue`, a
later array update overwrites the earlier value.

Returning an empty array does not clear a `ReducedValue`. Use `Overwrite` when
bypassing the reducer is intentional. For conversation state, use
`MessagesValue`, which handles message append and replacement semantics.

## State and runtime boundaries

Use distinct input, output, and internal `StateSchema` objects when the public
contract should expose only part of the working state. Nodes can declare
private schemas for internal channels.

Private channels are not redacted from full-state streaming. Restrict
`outputKeys`, authorize stream access, and avoid putting secrets in state.

Use runtime context for request-scoped identity, connections, configuration,
and services. Do not checkpoint non-serializable runtime objects, credentials,
or caller authorization as graph state.

## Routing with Command

```typescript
import { Command } from "@langchain/langgraph";

const route = async (state: typeof State.State) =>
  new Command({
    update: { routed: true },
    goto: state.needsReview ? "review" : "finish",
  });

builder.addNode("route", route, { ends: ["review", "finish"] });
```

Declare possible destinations with `ends`. A static edge from the same node
still executes in addition to the `Command` destination.

## Parallel fan-out with Send

```typescript
import { Send } from "@langchain/langgraph";

const dispatch = (state: typeof State.State) =>
  state.tasks.map((task) => new Send("worker", { task }));
```

The receiving result field needs a reducer. Use the shared composition
reference for worker and subgraph design.

## Invoke, stream, and errors

```typescript
const result = await graph.invoke({ input: "hello" });

for await (const update of await graph.stream(
  { input: "hello" },
  { streamMode: "updates" },
)) {
  console.log(update);
}
```

Choose `values`, `updates`, `messages`, or `custom` based on what the caller
needs. Add a node retry policy only for transient failures. Always await graph
invocation, compile before running, and ensure every router returns a registered
node or `END`.

For new integrations, prefer `streamEvents`, which exposes typed projections
for messages, values, subgraphs, and output. Preserve `stream` and its existing
event contract when modifying a stream-mode consumer.

When a checkpointed run resumes, an affected node starts again from the
beginning. Keep side effects idempotent, use stable operation keys, and split
completed effects into separate nodes or tasks when that improves replay safety.

Use the shared persistence and HITL references when invocation requires a
thread identifier, checkpointer, store, or interrupt.
