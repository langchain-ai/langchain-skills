# Deep Agents human in the loop

Deep Agents can interrupt before selected tool calls. Configure the approval
policy on the agent or subagent that owns the tool. Resumption requires a
checkpointer and the same thread configuration used for the interrupted run.

## Python

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

agent = create_deep_agent(
    interrupt_on={
        "write_file": True,
        "execute_sql": {"allowed_decisions": ["approve", "reject"]},
        "read_file": False,
    },
    checkpointer=MemorySaver(),
)

config = {"configurable": {"thread_id": "review-123"}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Update the record"}]},
    config=config,
)

# After the application presents the interrupt and obtains approval:
result = agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config,
)
```

## TypeScript

```typescript
import { createDeepAgent } from "deepagents";
import { Command, MemorySaver } from "@langchain/langgraph";

const agent = await createDeepAgent({
  interruptOn: {
    write_file: true,
    execute_sql: { allowedDecisions: ["approve", "reject"] },
    read_file: false,
  },
  checkpointer: new MemorySaver(),
});

const config = { configurable: { thread_id: "review-123" } };
let result = await agent.invoke(
  { messages: [{ role: "user", content: "Update the record" }] },
  config,
);

result = await agent.invoke(
  new Command({ resume: { decisions: [{ type: "approve" }] } }),
  config,
);
```

Use a durable checkpointer outside local development. Inspect the returned
interrupt payload rather than assuming a pause from the invocation result.
Before supporting edit or rejection feedback, verify the current decision
schema in the installed Python or TypeScript release and current docs.

When approval is configured inside a custom subagent, configure that subagent
explicitly and ensure the parent invocation supplies resumable state. Test the
actual UI or API round trip, including process restart if the application must
survive one.
