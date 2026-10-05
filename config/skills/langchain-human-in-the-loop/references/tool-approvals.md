# Tool approvals

Use tool approvals when an agent may propose a consequential tool call but a
person must approve, edit, or reject it before execution. Apply the policy on
the agent that owns the tool, including a custom subagent when it owns the
action.

Base LangChain agents provide this behavior through human-in-the-loop
middleware. Deep Agents exposes the same kind of policy through
`interrupt_on`/`interruptOn` configuration.

Decision support is not currently identical across languages:

| Decision | Python | TypeScript | Meaning |
|---|---|---|---|
| `approve` | Yes | Yes | Execute the proposed tool call unchanged |
| `edit` | Yes | Yes | Execute a reviewed replacement action |
| `reject` | Yes | Yes | Skip the tool and return rejection feedback |
| `respond` | Yes | Not currently documented | Skip execution and return the person's message as the tool result |

Use `respond` only when the person is acting as the tool, such as answering an
`ask_user` request. Use `reject` to deny a side-effecting action. A `respond`
message is treated as a successful tool result and must not represent denial.

## Base LangChain agent

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_agent(
    model=model,
    tools=[send_email],
    checkpointer=checkpointer,
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
```

```typescript
import { createAgent, humanInTheLoopMiddleware } from "langchain";

const agent = createAgent({
  model,
  tools: [sendEmail],
  checkpointer,
  middleware: [
    humanInTheLoopMiddleware({
      interruptOn: {
        send_email: { allowedDecisions: ["approve", "edit", "reject"] },
      },
    }),
  ],
});
```

## Deep Agent

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    tools=[execute_sql],
    checkpointer=checkpointer,
    interrupt_on={
        "execute_sql": {"allowed_decisions": ["approve", "reject"]},
        "read_record": False,
    },
)
```

```typescript
import { createDeepAgent } from "deepagents";

const agent = createDeepAgent({
  tools: [executeSql],
  checkpointer,
  interruptOn: {
    execute_sql: { allowedDecisions: ["approve", "reject"] },
    read_record: false,
  },
});
```

Prefer an explicit `allowed_decisions`/`allowedDecisions` list over the `True`
or `true` shorthand when behavior must match across Python and TypeScript. The
current TypeScript Deep Agents documentation is inconsistent about whether the
shorthand includes `respond`; an explicit list avoids depending on that
default.

When only some calls to a tool need review, use the release's conditional
`when` predicate. It receives the proposed tool-call request and should return
true only for calls that must pause. Keep authorization in the tool as well:
returning false from `when` means the call proceeds without human review.
Conditional predicates are version-gated, and Deep Agents TypeScript does not
currently document the same conditional configuration as Python, so verify the
installed language package before adding one.

Select tools from their effect and the application's risk boundary, not from
their names alone. An approval allowlist is part of authorization policy; keep
the actual tool implementation authorized as well. Inspect the returned
interrupt before presenting it, and verify current edit and rejection payload
schemas before implementing the review surface.

For Deep Agents, configure approvals on the agent that owns the tool. A custom
subagent can define its own `interrupt_on`/`interruptOn` policy, which overrides
the main agent's settings for that subagent. Do not assume the parent's policy
protects tools owned by a custom subagent.

Tool-review middleware can batch several proposed tool calls into one
interrupt. Provide one decision per action request in the same order. This
ordered decision list is different from resuming independent interrupts raised
by parallel LangGraph branches, which uses interrupt IDs.
