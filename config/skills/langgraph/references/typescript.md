# LangGraph TypeScript

Use this reference for TypeScript applications. Inspect installed versions and
current imports before editing an existing project. Current documentation:
<https://docs.langchain.com/oss/javascript/langgraph/overview>.

## Minimal graph

```typescript
import { END, START, StateGraph, StateSchema } from "@langchain/langgraph";
import * as z from "zod";

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

## State and reducers

```typescript
import { ReducedValue, StateSchema } from "@langchain/langgraph";
import * as z from "zod";

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

Use the shared persistence and HITL references when invocation requires a
thread identifier, checkpointer, store, or interrupt.
