# LangChain human in the loop

LangChain provides human review of tool calls through agent middleware. The
agent needs a checkpointer, and the initial invocation and resume must use the
same thread identity.

## Python

```python
import os

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

agent = create_agent(
    model=os.environ["MODEL"],
    tools=[send_email],
    checkpointer=InMemorySaver(),
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email": {
                    "allowed_decisions": ["approve", "edit", "reject"]
                }
            }
        )
    ],
)

config = {"configurable": {"thread_id": "review-123"}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Send the status email."}]},
    config=config,
)

# After the application displays the interrupt and records approval:
result = agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config,
)
```

## TypeScript

```typescript
import { createAgent, humanInTheLoopMiddleware } from "langchain";
import { Command, MemorySaver } from "@langchain/langgraph";

const model = process.env.MODEL;
if (!model) throw new Error("MODEL is required");

const agent = createAgent({
  model,
  tools: [sendEmail],
  checkpointer: new MemorySaver(),
  middleware: [
    humanInTheLoopMiddleware({
      interruptOn: {
        send_email: { allowedDecisions: ["approve", "edit", "reject"] },
      },
    }),
  ],
});

const config = { configurable: { thread_id: "review-123" } };
let result = await agent.invoke(
  { messages: [{ role: "user", content: "Send the status email." }] },
  config,
);

result = await agent.invoke(
  new Command({ resume: { decisions: [{ type: "approve" }] } }),
  config,
);
```

Inspect the returned interrupt payload before presenting a decision UI. Verify
the installed release's exact edit and rejection payload fields instead of
copying them from another language or version. Use a durable checkpointer in
production and authorize the actor who resumes the thread.
