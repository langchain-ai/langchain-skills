# LangChain subagents and composition

A LangChain agent can be exposed as a tool when a parent agent needs a narrow,
delegated capability. The tool is the boundary: define the input, context,
result, errors, and persistence behavior explicitly.

## Python agent as a tool

```python
import os

from langchain.agents import create_agent
from langchain_core.tools import tool

research_agent = create_agent(
    model=os.environ["MODEL"],
    tools=[web_search],
    system_prompt="Research the question and return a concise sourced answer.",
)


@tool
def research(question: str) -> str:
    """Research a question that requires current external sources."""
    result = research_agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    return str(result["messages"][-1].content)
```

## TypeScript agent as a tool

```typescript
import { createAgent } from "langchain";
import { tool } from "@langchain/core/tools";
import * as z from "zod";

const model = process.env.MODEL;
if (!model) throw new Error("MODEL is required");

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
    return String(result.messages.at(-1)?.content ?? "");
  },
  {
    name: "research",
    description: "Research a question that requires current external sources.",
    schema: z.object({ question: z.string() }),
  },
);
```

The parent sees only the tool contract and returned value. Pass necessary
context deliberately; do not assume the delegated agent inherits the parent's
messages, middleware, checkpointer, store, or permissions. Use a LangGraph
subgraph when delegated work needs explicit multi-step control flow or shared
graph state.
