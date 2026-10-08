# Agentic retrieval

Use agentic retrieval when an agent should decide whether a knowledge search is
needed, formulate the query, or perform more than one search. Expose retrieval
through a narrow tool with a clear description and a structured result that
preserves sources.

The same retrieval tool can be attached to a base LangChain agent or a Deep
Agent, and either agent can run inside a LangGraph node.

## Python

```python
from langchain.agents import create_agent
from langchain_core.tools import tool


@tool
def search_knowledge_base(query: str) -> list[dict]:
    """Search internal documentation relevant to a question."""
    documents = retriever.invoke(query)
    authorized = [document for document in documents if can_read(document)]
    return [
        {"content": document.page_content, "source": document.metadata["source"]}
        for document in authorized
    ]


agent = create_agent(
    model=model,
    tools=[search_knowledge_base],
    system_prompt="Use the knowledge base for questions about internal documentation.",
)
```

To use the same tool with the more opinionated harness, pass it to
`create_deep_agent(tools=[search_knowledge_base], ...)`. A graph node can invoke
either agent and translate its result into graph state.

## TypeScript

```typescript
import { createAgent } from "langchain";
import { tool } from "@langchain/core/tools";
import * as z from "zod";

const searchKnowledgeBase = tool(
  async ({ query }) => {
    const documents = await retriever.invoke(query);
    return documents
      .filter((document) => canRead(document))
      .map((document) => ({
        content: document.pageContent,
        source: document.metadata.source,
      }));
  },
  {
    name: "search_knowledge_base",
    description: "Search internal documentation relevant to a question.",
    schema: z.object({ query: z.string() }),
  },
);

const agent = createAgent({
  model,
  tools: [searchKnowledgeBase],
  systemPrompt: "Use the knowledge base for questions about internal documentation.",
});
```

For a Deep Agent, pass the tool to `createDeepAgent({ tools:
[searchKnowledgeBase], ... })`. In LangGraph, use a deterministic retrieval node
when workflow policy requires search, or invoke the agent in a node when the
agent should decide.

Treat tool queries and retrieved results as untrusted. Enforce authorization
inside the tool rather than relying on the agent prompt. Limit result count and
size, preserve citations, and define behavior for no authorized match. If the
agent can choose collections or filters, validate those choices against the
caller's allowed scope.
