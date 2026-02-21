---
name: LangChain Fundamentals
description: Create LangChain agents with create_agent, define tools, and use middleware for human-in-the-loop and error handling
---

<oneliner>
Build production agents using `create_agent()`, the `@tool` decorator / `tool()` function, and middleware patterns.
</oneliner>

<quick_start>
<python>
Create and invoke a basic agent with tools using create_agent.
```python
from langchain.agents import create_agent
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search for information on the web.

    Args:
        query: The search query
    """
    return f"Results for: {query}"

agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=[search],
    system_prompt="You are a helpful assistant."
)

result = agent.invoke({"messages": [("user", "Search for LangChain docs")]})
```
</python>
<typescript>
Create and invoke a basic agent with tools using createAgent.
```typescript
import { createAgent } from "@langchain/langgraph/prebuilt";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const search = tool(
  async ({ query }) => `Results for: ${query}`,
  {
    name: "search",
    description: "Search for information on the web.",
    schema: z.object({ query: z.string().describe("The search query") }),
  }
);

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-5",
  tools: [search],
  systemPrompt: "You are a helpful assistant.",
});

const result = await agent.invoke({ messages: [["user", "Search for LangChain docs"]] });
```
</typescript>
</quick_start>

<create_agent>
## Creating Agents with create_agent

`create_agent()` is the recommended way to build agents. It handles the agent loop, tool execution, and state management.

### Agent Configuration Options

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `model` | LLM to use | `"anthropic:claude-sonnet-4-5"` or model instance |
| `tools` | List of tools | `[search, calculator]` |
| `system_prompt` / `systemPrompt` | Agent instructions | `"You are a helpful assistant"` |
| `checkpointer` | State persistence | `MemorySaver()` |
| `middleware` | Processing hooks | `[human_in_the_loop_middleware]` |
| `max_iterations` / `maxIterations` | Loop limit | `10` |
</create_agent>

<ex-basic-agent>
<python>
Create a basic agent with a weather tool and invoke it with a user query.
```python
from langchain.agents import create_agent
from langchain_core.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get current weather for a location.

    Args:
        location: City name
    """
    return f"Weather in {location}: Sunny, 72F"

agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=[get_weather],
    system_prompt="You are a helpful assistant."
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "What's the weather in Paris?"}]
})
print(result["messages"][-1].content)
```
</python>
<typescript>
Create a basic agent with a weather tool and invoke it with a user query.
```typescript
import { createAgent } from "@langchain/langgraph/prebuilt";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const getWeather = tool(
  async ({ location }) => `Weather in ${location}: Sunny, 72F`,
  {
    name: "get_weather",
    description: "Get current weather for a location.",
    schema: z.object({ location: z.string().describe("City name") }),
  }
);

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-5",
  tools: [getWeather],
  systemPrompt: "You are a helpful assistant.",
});

const result = await agent.invoke({
  messages: [{ role: "user", content: "What's the weather in Paris?" }],
});
console.log(result.messages[result.messages.length - 1].content);
```
</typescript>
</ex-basic-agent>

<ex-agent-with-persistence>
<python>
Add MemorySaver checkpointer to maintain conversation state across invocations.
```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=[search],
    checkpointer=checkpointer,
)

config = {"configurable": {"thread_id": "user-123"}}
agent.invoke({"messages": [{"role": "user", "content": "My name is Alice"}]}, config=config)
result = agent.invoke({"messages": [{"role": "user", "content": "What's my name?"}]}, config=config)
# Agent remembers: "Your name is Alice"
```
</python>
<typescript>
Add MemorySaver checkpointer to maintain conversation state across invocations.
```typescript
import { createAgent } from "@langchain/langgraph/prebuilt";
import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-5",
  tools: [search],
  checkpointer,
});

const config = { configurable: { thread_id: "user-123" } };
await agent.invoke({ messages: [{ role: "user", content: "My name is Alice" }] }, config);
const result = await agent.invoke({ messages: [{ role: "user", content: "What's my name?" }] }, config);
// Agent remembers: "Your name is Alice"
```
</typescript>
</ex-agent-with-persistence>

<tools>
## Defining Tools

Tools are functions that agents can call. Use the `@tool` decorator (Python) or `tool()` function (TypeScript).
</tools>

<ex-basic-tool>
<python>
Define a calculator tool using the @tool decorator with parameter types.
```python
from langchain_core.tools import tool

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely.

    Args:
        expression: Math expression like "2 + 2" or "10 * 5"
    """
    allowed = set('0123456789+-*/(). ')
    if not all(c in allowed for c in expression):
        return "Error: Invalid characters in expression"
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"
```
</python>
<typescript>
Define a calculator tool using the tool() function with Zod schema validation.
```typescript
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const calculate = tool(
  async ({ expression }) => {
    const allowed = new Set("0123456789+-*/(). ".split(""));
    if (![...expression].every((c) => allowed.has(c))) {
      return "Error: Invalid characters in expression";
    }
    try {
      return String(eval(expression));
    } catch (e) {
      return `Error: ${e}`;
    }
  },
  {
    name: "calculate",
    description: "Evaluate a mathematical expression safely.",
    schema: z.object({
      expression: z.string().describe("Math expression like '2 + 2' or '10 * 5'"),
    }),
  }
);
```
</typescript>
</ex-basic-tool>

<middleware>
## Middleware for Agent Control

Middleware intercepts the agent loop to add human approval, error handling, logging, etc.
</middleware>

<ex-hitl-middleware>
<python>
Require human approval before executing sensitive tools like delete operations.
```python
from langchain.agents import create_agent, human_in_the_loop_middleware

@tool
def delete_record(record_id: str) -> str:
    """Delete a database record permanently.

    Args:
        record_id: ID of record to delete
    """
    db.delete(record_id)
    return f"Deleted record {record_id}"

agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=[delete_record, search],
    middleware=[
        human_in_the_loop_middleware(
            tools_requiring_approval=["delete_record"]
        )
    ],
)
```
</python>
<typescript>
Require human approval before executing sensitive tools like delete operations.
```typescript
import { createAgent, humanInTheLoopMiddleware } from "@langchain/langgraph/prebuilt";

const deleteRecord = tool(
  async ({ recordId }) => {
    await db.delete(recordId);
    return `Deleted record ${recordId}`;
  },
  {
    name: "delete_record",
    description: "Delete a database record permanently.",
    schema: z.object({ recordId: z.string().describe("ID of record to delete") }),
  }
);

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-5",
  tools: [deleteRecord, search],
  middleware: [
    humanInTheLoopMiddleware({
      toolsRequiringApproval: ["delete_record"],
    }),
  ],
});
```
</typescript>
</ex-hitl-middleware>

<ex-error-middleware>
<python>
Catch and handle tool errors gracefully with custom middleware.
```python
from langchain.agents import create_agent, wrap_tool_call

@wrap_tool_call
async def error_handler(tool_call, handler):
    try:
        return await handler(tool_call)
    except Exception as error:
        return {
            **tool_call,
            "content": f"Tool error: {str(error)}. Please try a different approach.",
        }

agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=[risky_tool],
    middleware=[error_handler],
)
```
</python>
<typescript>
Catch and handle tool errors gracefully with custom middleware.
```typescript
import { createAgent, wrapToolCall } from "@langchain/langgraph/prebuilt";

const errorHandler = wrapToolCall(async (toolCall, handler) => {
  try {
    return await handler(toolCall);
  } catch (error) {
    return {
      ...toolCall,
      content: `Tool error: ${error}. Please try a different approach.`,
    };
  }
});

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-5",
  tools: [riskyTool],
  middleware: [errorHandler],
});
```
</typescript>
</ex-error-middleware>

<model_config>
## Model Configuration

`create_agent` accepts model strings in `provider:model` format:

```
"anthropic:claude-sonnet-4-5"
"openai:gpt-4.1"
"bedrock:anthropic.claude-3-5-sonnet-20241022-v2:0"
```
</model_config>

<ex-model-instance>
<python>
Pass a model instance with custom settings instead of a model string.
```python
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(model="claude-sonnet-4-5", temperature=0)
agent = create_agent(model=model, tools=[...])
```
</python>
<typescript>
Pass a model instance with custom settings instead of a model string.
```typescript
import { ChatAnthropic } from "@langchain/anthropic";

const model = new ChatAnthropic({ model: "claude-sonnet-4-5", temperature: 0 });
const agent = createAgent({ model, tools: [...] });
```
</typescript>
</ex-model-instance>

<fix-missing-tool-description>
<python>
Clear descriptions help the agent know when to use each tool.
```python
# WRONG: Vague or missing description
@tool
def bad_tool(input: str) -> str:
    """Does stuff."""
    return "result"

# CORRECT: Clear, specific description with Args
@tool
def search(query: str) -> str:
    """Search the web for current information about a topic.

    Use this when you need recent data or facts.

    Args:
        query: The search query (2-10 words recommended)
    """
    return web_search(query)
```
</python>
<typescript>
Clear descriptions help the agent know when to use each tool.
```typescript
// WRONG: Vague description
const badTool = tool(async ({ input }) => "result", {
  name: "bad_tool",
  description: "Does stuff.", // Too vague!
  schema: z.object({ input: z.string() }),
});

// CORRECT: Clear, specific description
const search = tool(async ({ query }) => webSearch(query), {
  name: "search",
  description: "Search the web for current information about a topic. Use this when you need recent data or facts.",
  schema: z.object({
    query: z.string().describe("The search query (2-10 words recommended)"),
  }),
});
```
</typescript>
</fix-missing-tool-description>

<fix-no-checkpointer>
<python>
Add checkpointer and thread_id for conversation memory across invocations.
```python
# WRONG: No persistence - agent forgets between calls
agent = create_agent(model="anthropic:claude-sonnet-4-5", tools=[search])
agent.invoke({"messages": [{"role": "user", "content": "I'm Bob"}]})
agent.invoke({"messages": [{"role": "user", "content": "What's my name?"}]})
# Agent doesn't remember!

# CORRECT: Add checkpointer and thread_id
from langgraph.checkpoint.memory import MemorySaver

agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=[search],
    checkpointer=MemorySaver(),
)
config = {"configurable": {"thread_id": "session-1"}}
agent.invoke({"messages": [{"role": "user", "content": "I'm Bob"}]}, config=config)
agent.invoke({"messages": [{"role": "user", "content": "What's my name?"}]}, config=config)
# Agent remembers: "Your name is Bob"
```
</python>
<typescript>
Add checkpointer and thread_id for conversation memory across invocations.
```typescript
// WRONG: No persistence
const agent = createAgent({ model: "anthropic:claude-sonnet-4-5", tools: [search] });
await agent.invoke({ messages: [{ role: "user", content: "I'm Bob" }] });
await agent.invoke({ messages: [{ role: "user", content: "What's my name?" }] });
// Agent doesn't remember!

// CORRECT: Add checkpointer and thread_id
import { MemorySaver } from "@langchain/langgraph";

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-5",
  tools: [search],
  checkpointer: new MemorySaver(),
});
const config = { configurable: { thread_id: "session-1" } };
await agent.invoke({ messages: [{ role: "user", content: "I'm Bob" }] }, config);
await agent.invoke({ messages: [{ role: "user", content: "What's my name?" }] }, config);
// Agent remembers: "Your name is Bob"
```
</typescript>
</fix-no-checkpointer>

<fix-infinite-loop>
<python>
Set max_iterations to prevent runaway agent loops.
```python
# WRONG: No iteration limit - could loop forever
agent = create_agent(model="anthropic:claude-sonnet-4-5", tools=[search])

# CORRECT: Set max_iterations
agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=[search],
    max_iterations=10,  # Stop after 10 tool calls
)
```
</python>
<typescript>
Set maxIterations to prevent runaway agent loops.
```typescript
// WRONG: No iteration limit
const agent = createAgent({ model: "anthropic:claude-sonnet-4-5", tools: [search] });

// CORRECT: Set maxIterations
const agent = createAgent({
  model: "anthropic:claude-sonnet-4-5",
  tools: [search],
  maxIterations: 10, // Stop after 10 tool calls
});
```
</typescript>
</fix-infinite-loop>

<fix-accessing-result-wrong>
<python>
Access the messages array from the result, not result.content directly.
```python
# WRONG: Trying to access result.content directly
result = agent.invoke({"messages": [{"role": "user", "content": "Hello"}]})
print(result.content)  # AttributeError!

# CORRECT: Access messages from result dict
result = agent.invoke({"messages": [{"role": "user", "content": "Hello"}]})
print(result["messages"][-1].content)  # Last message content
```
</python>
<typescript>
Access the messages array from the result, not result.content directly.
```typescript
// WRONG: Trying to access result.content directly
const result = await agent.invoke({ messages: [{ role: "user", content: "Hello" }] });
console.log(result.content); // undefined!

// CORRECT: Access messages from result object
const result = await agent.invoke({ messages: [{ role: "user", content: "Hello" }] });
console.log(result.messages[result.messages.length - 1].content); // Last message content
```
</typescript>
</fix-accessing-result-wrong>

<related_skills>
- **langgraph-fundamentals**: For custom graph-based agents with StateGraph
- **langgraph-persistence**: For advanced persistence patterns with checkpointers
- **langchain-output**: For structured output with Pydantic/Zod models
- **langchain-rag**: For RAG pipelines with vector stores
</related_skills>
