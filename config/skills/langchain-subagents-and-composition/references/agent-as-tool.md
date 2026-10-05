# Agent as tool

Use an agent-as-tool boundary when a parent agent needs a narrow delegated
capability and only needs the final result. The tool schema is the contract:
define input, context, result, errors, timeout, and persistence behavior.

The wrapped runnable can be a base LangChain agent, a Deep Agent, or a compiled
LangGraph workflow. This base-agent example keeps the boundary visible.

## Python

```python
from langchain.agents import create_agent
from langchain.tools import tool

research_agent = create_agent(
    model=model,
    tools=[web_search],
    system_prompt="Research the question and return a concise sourced answer.",
)


@tool
def research(question: str) -> str:
    """Research a question that requires current external sources."""
    result = research_agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    return result["messages"][-1].text
```

## TypeScript

```typescript
import { createAgent, tool } from "langchain";
import * as z from "zod";

const researchAgent = createAgent({
  model,
  tools: [webSearch],
  systemPrompt: "Research the question and return a concise sourced answer.",
});

const research = tool(
  async ({ question }) => {
    const result = await researchAgent.invoke({
      messages: [{ role: "user", content: question }],
    });
    return result.messages.at(-1)?.text ?? "";
  },
  {
    name: "research",
    description: "Research a question that requires current external sources.",
    schema: z.object({ question: z.string() }),
  },
);
```

Pass only the context needed for the operation, validate its result as
untrusted input, and surface errors in a form the parent can handle. The child
does not inherit messages, middleware, storage, or permissions merely because
the parent calls it through a tool.

Choose the input deliberately:

- Pass only the task for an isolated, stateless invocation.
- Read selected fields from `ToolRuntime` when the worker needs authenticated
  runtime context or a small part of parent state.
- Pass conversation history only when the worker must continue prior work;
  filter messages and avoid forwarding unrelated or sensitive context.

Plain text is appropriate when the supervisor only needs a concise answer. Use
the child agent's structured-output support when downstream code needs fields
with stable types. Do not stringify arbitrary message content blocks and then
parse them as a data contract.

A tool can return the release's `Command` form when the child must update
specific parent-state fields in addition to returning a tool result. Define an
allowlist of fields, validate the update, and include the required tool message;
do not merge the child's full state into the parent.

Use a subgraph when delegated work needs shared graph state or explicit
multi-step control flow. Use fresh-context delegation when the parent should
choose among named specialists without owning a custom tool wrapper.
