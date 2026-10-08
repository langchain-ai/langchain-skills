# Explicit interrupts

Use a LangGraph `interrupt(value)` when the application must pause at a point
defined by workflow logic rather than only before a tool call. The interrupt
surfaces a serializable review payload. `Command(resume=value)` continues the
same checkpointed thread and returns the resume value from the interrupt call.

## Python

```python
from typing_extensions import TypedDict
from langgraph.types import Command, interrupt


class ReviewDecision(TypedDict):
    approved: bool


def review(state: State) -> dict:
    decision = interrupt(
        {"question": "Approve this draft?", "draft": state["draft"]},
        response_schema=ReviewDecision,
    )
    return {"approved": decision["approved"]}


paused = graph.invoke({"draft": "..."}, config=config)
result = graph.invoke(Command(resume={"approved": True}), config=config)
```

## TypeScript

```typescript
import { Command, interrupt } from "@langchain/langgraph";
import * as z from "zod";

const ReviewDecision = z.object({ approved: z.boolean() });

const review = async (state: typeof State.State) => {
  const decision = interrupt(
    {
      question: "Approve this draft?",
      draft: state.draft,
    },
    { responseSchema: ReviewDecision },
  );
  return { approved: decision.approved };
};

const paused = await graph.invoke({ draft: "..." }, config);
const result = await graph.invoke(
  new Command({ resume: { approved: true } }),
  config,
);
```

Compile the graph with a checkpointer and supply a stable thread identity for
both calls. Keep the review payload minimal, serializable, and safe to show to
the reviewing actor. Prefer `response_schema`/`responseSchema` when the installed
LangGraph version supports it. A Python type, Pydantic model, or TypeScript Zod
schema validates the resume value; a raw JSON Schema is exposed to clients but
does not itself validate the value.

With the default invoke API, pending interrupts appear under `__interrupt__`.
Newer Python v2 graph output exposes an `interrupts` collection, and v3 event
streaming exposes `stream.interrupted` and `stream.interrupts`. TypeScript also
exposes interrupts through its selected invoke or streaming surface. Handle the
shape returned by the API mode the application actually uses rather than
mixing examples from different modes.

`interrupt()` pauses by raising a framework control-flow exception. Do not wrap
it in a broad `try`/`except` or `try`/`catch`, which can swallow the pause. Keep
error-prone work outside that handler or catch only the specific application
errors expected around it.

When one node contains more than one interrupt call, LangGraph associates
resume values with those calls by their encounter order. Keep their order
deterministic across re-execution. Do not conditionally skip, reorder, or place
them in a loop whose iterations can change after resume; use separate nodes and
conditional edges for a dynamic review sequence.

For parallel interrupts, identify pending interrupts by the IDs returned by the
installed release and use its current mapping form. Do not associate decisions
by list order.
