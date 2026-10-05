# Custom middleware

Write custom middleware when behavior must consistently wrap part of the agent
loop and no maintained component matches it. Give each component one clear
responsibility and use the narrowest applicable hook.

Hooks have two shapes:

- **Node hooks** run before or after the agent or model and return ordinary
  state updates.
- **Wrap hooks** surround model or tool execution. A wrapper may call its
  handler zero times to short-circuit, once for the normal path, or multiple
  times for a bounded retry or fallback.

Use synchronous hooks for synchronous agents and the corresponding asynchronous
Python hooks for asynchronous agents. Do not perform blocking work in an async
hook.

## Python tool wrapper

Use runtime context for request-scoped identity and dependencies. This example
records tool activity without changing the tool result or retrying a side
effect:

```python
import logging
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call


logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    request_id: str


@wrap_tool_call
def audit_tool_call(request, handler):
    request_id = request.runtime.context.request_id
    tool_name = request.tool_call["name"]
    logger.info("tool_started", extra={"request_id": request_id, "tool": tool_name})
    try:
        return handler(request)
    finally:
        logger.info("tool_finished", extra={"request_id": request_id, "tool": tool_name})


agent = create_agent(
    model=model,
    tools=[search],
    middleware=[audit_tool_call],
    context_schema=RequestContext,
)
```

## TypeScript tool wrapper

```typescript
import * as z from "zod";
import { createAgent, createMiddleware } from "langchain";

const requestContextSchema = z.object({ requestId: z.string() });

const auditToolCall = createMiddleware({
  name: "auditToolCall",
  contextSchema: requestContextSchema,
  wrapToolCall: async (request, handler) => {
    const { requestId } = request.runtime.context;
    const tool = request.toolCall.name;
    console.info("tool_started", { requestId, tool });
    try {
      return await handler(request);
    } finally {
      console.info("tool_finished", { requestId, tool });
    }
  },
});

const agent = createAgent({
  model,
  tools: [search],
  middleware: [auditToolCall],
  contextSchema: requestContextSchema,
});
```

Wrap hooks receive a request and handler. Call the handler exactly when the
underlying operation should proceed; returning early short-circuits it. Do not
use `yield` in a synchronous Python wrapper. Verify hook names, sync and async
behavior, and request, state, and runtime signatures against the installed
version.

Runtime context is the right place for request identity, service clients, and
other invocation-scoped dependencies. Put only durable, serializable values in
checkpointed state.

Prefer built-in retry middleware over a hand-written retry wrapper. A retry can
repeat side effects, so keep attempts bounded and restrict it to read-only or
idempotent operations, or supply an idempotency key. Preserve errors the caller
needs to distinguish rather than turning every failure into model-visible text.

Custom middleware can also extend a Deep Agent because its harness uses the
same middleware system. In Python, a supplied component whose `.name` matches a
core component replaces that component in place. Other supplied components are
inserted after the core entries and before profile, prompt-caching, and memory
middleware. Current TypeScript documentation describes supplied middleware as
appended. Verify this behavior against the installed version before relying on
an exact position.

Custom subagents do not inherit custom middleware from their parent. Configure
each custom subagent explicitly when it needs the same behavior.
