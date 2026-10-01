# Deep Agents middleware

`create_deep_agent` and `createDeepAgent` assemble an agent harness from
middleware. Inspect the current harness configuration before adding another
component: file operations, delegation, summarization, prompt caching, or other
behavior may already be present depending on language and package version.

Task planning is opt-in in current Python Deep Agents releases. In Python v0.7
and later, add LangChain's `TodoListMiddleware` when the application benefits
from an explicit `write_todos` planning tool.

## Python task planning

```python
from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_deep_agent(
    middleware=[TodoListMiddleware()],
)
```

Use task planning for work that is meaningfully multi-step or long-running.
Skip it for short requests where a maintained task list would add overhead.
If todo state must persist across invocations, configure resumable thread state
and reuse the same thread identity.

For TypeScript, verify whether the installed Deep Agents release exposes task
planning through a middleware component or another option before implementing
it. Do not translate the Python constructor mechanically.

When adding custom middleware, preserve the application's existing middleware
order and confirm whether a custom subagent receives that middleware. Configure
custom subagents explicitly when they require the same behavior. Test both the
middleware's trigger and its interaction with the harness's built-in tools.
