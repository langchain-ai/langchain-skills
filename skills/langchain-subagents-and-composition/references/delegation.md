# Delegation

Use delegation when a unit of work benefits from fresh context, specialized
instructions, a different model, or a restricted tool set. The parent remains
responsible for choosing the task and integrating the final result.

Deep Agents provides this pattern through subagent middleware and its `task`
tool. It automatically adds a synchronous `general-purpose` subagent unless the
application replaces or explicitly disables it. Do not add another generic
worker merely to reproduce that default; add named specialists when their
description, tools, instructions, model, or output contract differs.

Synchronous subagents block the supervisor until they return and can run in
parallel when the model issues several `task` calls in one turn. The default
`isolated` mode receives the delegated task in a fresh context. Put all
information needed for that unit of work in the instruction or in explicitly
shared storage.

## Python

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    subagents=[
        {
            "name": "researcher",
            "description": "Research a bounded question and cite the sources used",
            "system_prompt": "Return a concise answer with source URLs.",
            "tools": [web_search],
        }
    ]
)
```

## TypeScript

```typescript
import { createDeepAgent } from "deepagents";

const agent = createDeepAgent({
  subagents: [
    {
      name: "researcher",
      description: "Research a bounded question and cite the sources used",
      systemPrompt: "Return a concise answer with source URLs.",
      tools: [webSearch],
    },
  ],
});
```

Descriptions help the parent choose a worker. Instructions should identify the
goal, relevant context, limits, and expected result shape. Avoid a later call
that assumes an ephemeral worker remembers an earlier invocation.

For predictable machine-readable results, configure
`response_format`/`responseFormat`. Deep Agents serializes the validated result
into the tool result returned to the supervisor. For more complex workers, use
a `CompiledSubAgent` backed by a compiled LangGraph graph instead of forcing the
workflow into one prompt.

## Isolated and forked context

Use isolated mode for focused work that can be described as a complete task.
Use `mode: "fork"` only when the worker must continue the parent's existing
investigation: a fork receives the parent's conversation and, for dictionary
subagents, its system prompt. A compiled fork keeps the compiled graph's own
system prompt. Forking is version-sensitive and currently beta.

Forked context is larger and less isolated. It also has different capability
constraints, including no nested `task` delegation and no separately configured
skills in current releases. Keep isolated mode as the default.

## Background and dynamic delegation

Deep Agents background or async subagents are independent Agent
Protocol-compatible jobs. Starting one returns a task ID immediately; the
supervisor can later check, update, cancel, or list it. This is not ordinary
Python or JavaScript `async`/`await`. Use it for long-running work when the
supervisor should keep interacting with the user or steer work mid-flight.
Persist task identity outside compactable chat history and enforce ownership on
every status, update, and cancellation request.

Dynamic subagent dispatch through an interpreter can fan out from generated
code for many runtime work items. It is beta and expands resource and execution
authority. Prefer normal `task` calls or LangGraph `Send` until code-driven
orchestration is genuinely required, then bound concurrency and validate every
dispatched task.

Use typed subagent streaming when the UI needs progress rather than waiting for
one final result. Subagent names are also exposed through `lc_agent_name`
metadata for streaming, tools, and tracing.

Custom subagent inheritance is setting-specific. Current isolated subagents
inherit the parent's tools, model, approval policy, runtime context, and
filesystem permissions by default. Explicit tools or permissions replace the
inherited values. Custom middleware and skills do not inherit; the built-in
general-purpose subagent is the exception that inherits parent skills. Supply a
system prompt for every custom isolated subagent. Verify these rules against the
installed release before relying on them as an authorization boundary.

To remove synchronous delegation entirely, disable the active harness profile's
general-purpose subagent and provide no synchronous custom subagents. Do not
exclude the required subagent middleware directly.
