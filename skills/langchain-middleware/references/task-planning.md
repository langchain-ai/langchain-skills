# Task planning

Add task-planning middleware when an agent handles work that is meaningfully
multi-step or long-running and benefits from an explicit task list. Skip it for
short requests where maintaining the list would add overhead.

Task planning is opt-in in current Python and TypeScript Deep Agents releases.
LangChain's `TodoListMiddleware` adds the `write_todos` planning tool:

```python
from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_deep_agent(
    middleware=[TodoListMiddleware()],
)
```

Current TypeScript releases expose the same capability through
`todoListMiddleware`:

```typescript
import { createDeepAgent } from "deepagents";
import { todoListMiddleware } from "langchain";

const agent = createDeepAgent({
  middleware: [todoListMiddleware()],
});
```

The model maintains items through `pending`, `in_progress`, and `completed`
statuses. Frontends can render the latest list from streamed values, for example
`stream.values.todos`. Treat it as working state: the model may revise it as it
learns more.

These APIs are version-sensitive. Verify the installed language package; do not
assume `write_todos` is present unless the middleware is configured or the
installed release documents another default. Some current TypeScript docs show
`await createDeepAgent(...)` while others omit `await`; awaiting a non-Promise
is harmless, but keep examples internally consistent with the installed API.

The task list is agent working state, not application workflow. Use LangGraph
state, nodes, and edges when the application must enforce a sequence,
transition, approval, or business invariant.

If task state must survive invocations, configure a checkpointer and reuse the
same authorized thread identity. Treat task text as untrusted model-generated
data: it cannot expand tool access, grant permission, or remove a required
human review.
