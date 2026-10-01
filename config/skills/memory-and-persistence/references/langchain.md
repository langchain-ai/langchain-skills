# LangChain memory and persistence

LangChain agents use LangGraph persistence primitives. Use a checkpointer and a
stable thread identity for conversation state. Use a store when selected memory
must be shared across threads. Do not describe a checkpointer as cross-thread
long-term memory.

## Python thread state

```python
import os

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model=os.environ["MODEL"],
    tools=[search],
    checkpointer=InMemorySaver(),
)

config = {"configurable": {"thread_id": "conversation-123"}}
agent.invoke(
    {"messages": [{"role": "user", "content": "My name is Ana."}]},
    config=config,
)
result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is my name?"}]},
    config=config,
)
```

## TypeScript thread state

```typescript
import { createAgent } from "langchain";
import { MemorySaver } from "@langchain/langgraph";

const model = process.env.MODEL;
if (!model) throw new Error("MODEL is required");

const agent = createAgent({
  model,
  tools: [search],
  checkpointer: new MemorySaver(),
});

const config = { configurable: { thread_id: "conversation-123" } };
await agent.invoke(
  { messages: [{ role: "user", content: "My name is Ana." }] },
  config,
);
const result = await agent.invoke(
  { messages: [{ role: "user", content: "What is my name?" }] },
  config,
);
```

In-memory savers are for development and tests. Use a durable checkpointer for
restart-safe applications. Verify store injection and runtime access against
the installed LangChain and LangGraph versions before adding cross-thread
memory. Test thread isolation and restart behavior separately.
