# Deep Agents subagents and composition

Deep Agents exposes delegation through its subagent middleware and `task` tool.
A delegated call starts with fresh context and returns one final result to the
caller. Put all information needed for that unit of work in the instruction or
in explicitly shared storage.

## Python custom subagent

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

## TypeScript custom subagent

```typescript
import { createDeepAgent } from "deepagents";

const agent = await createDeepAgent({
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

Descriptions help the parent decide when to delegate. Prompts should specify
the output contract, and tools should match the delegated responsibility.
Avoid a second call that assumes the worker remembers its first call.

Custom subagent configuration and inheritance behavior vary by release. Do not
assume it inherits the parent's skills, middleware, backend, model, or approval
rules. Supply required configuration explicitly and verify it in current docs.

A Deep Agent can also participate in a broader application as a LangGraph node,
a tool-like operation, or an orchestrator that delegates to a compiled graph.
Make state conversion and error propagation explicit at that boundary. Test
that the delegated worker receives only the intended context and that its final
result is usable by the parent.
