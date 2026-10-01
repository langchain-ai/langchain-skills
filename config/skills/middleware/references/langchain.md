# LangChain middleware

Use LangChain middleware for behavior that wraps the agent loop. Keep explicit
business workflow in LangGraph nodes and edges. Inspect existing middleware and
its order before adding another component.

## Python tool wrapper

```python
import os

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call


@wrap_tool_call
def retry_transient_tool_error(request, handler):
    for attempt in range(3):
        try:
            return handler(request)
        except TimeoutError:
            if attempt == 2:
                raise


agent = create_agent(
    model=os.environ["MODEL"],
    tools=[search],
    middleware=[retry_transient_tool_error],
)
```

Wrap hooks receive a request and handler. Call the handler exactly when the
underlying operation should proceed; returning early short-circuits it. Do not
use `yield` in a synchronous wrapper.

## TypeScript tool wrapper

```typescript
import { createAgent, createMiddleware } from "langchain";

const model = process.env.MODEL;
if (!model) throw new Error("MODEL is required");

const retryTransientToolError = createMiddleware({
  name: "retryTransientToolError",
  wrapToolCall: async (request, handler) => {
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        return await handler(request);
      } catch (error) {
        if (attempt === 2) throw error;
      }
    }
    throw new Error("Unreachable");
  },
});

const agent = createAgent({
  model,
  tools: [search],
  middleware: [retryTransientToolError],
});
```

Verify available hook names and state/runtime signatures against the installed
version. Give custom middleware a single responsibility, preserve ordering,
and test both its trigger and its interaction with other middleware. Use the
`human-in-the-loop` skill for approval middleware.
