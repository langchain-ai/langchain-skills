---
name: LangChain Fundamentals
description: Create LangChain agents with create_agent, define tools, and use middleware for human-in-the-loop and error handling
---

<oneliner>
Build production agents using `create_agent()`, middleware patterns, and the `@tool` decorator / `tool()` function. When creating LangChain agents, you MUST use create_agent(), with middleware for custom flows. All other alternatives are outdated.
</oneliner>

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
| `middleware` | Processing hooks | `[HumanInTheLoopMiddleware]` (Python) / `[humanInTheLoopMiddleware({...})]` (TypeScript) |
</create_agent>

<ex-basic-agent>
<python>
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
```typescript
import { createAgent } from "langchain";
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
import { createAgent } from "langchain";
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
```python
from langchain_core.tools import tool

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: Math expression like "2 + 2" or "10 * 5"
    """
    return str(eval(expression))
```
</python>
<typescript>
```typescript
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const calculate = tool(
  async ({ expression }) => String(eval(expression)),
  {
    name: "calculate",
    description: "Evaluate a mathematical expression.",
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
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

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
        HumanInTheLoopMiddleware(
            interrupt_on={"delete_record": True}
        )
    ],
)
```
</python>
<typescript>
Require human approval before executing sensitive tools like delete operations.
```typescript
import { createAgent, humanInTheLoopMiddleware } from "langchain";

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

### Resuming After HITL Interrupt

When middleware interrupts, the result contains `__interrupt__`. Resume with `Command(resume=...)`:

<python>
```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "session-1"}}

# Initial request triggers interrupt on dangerous tool
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Delete record 123"}]}, config=config
)

# Check for interrupt
if "__interrupt__" in result:
    print("Approval needed:", result["__interrupt__"])

    # Approve and resume
    result = agent.invoke(
        Command(resume={"decisions": [{"type": "approve"}]}), config=config
    )
    # Other options:
    # Command(resume={"decisions": [{"type": "reject", "message": "Not allowed"}]})
    # Command(resume={"decisions": [{"type": "edit", "args": {"record_id": "456"}}]})
```
</python>
<typescript>
```typescript
import { Command } from "@langchain/langgraph";

const config = { configurable: { thread_id: "session-1" } };

// Initial request triggers interrupt on dangerous tool
const result = await agent.invoke(
  { messages: [{ role: "user", content: "Delete record 123" }] }, config
);

// Check for interrupt
if ("__interrupt__" in result) {
  console.log("Approval needed:", result.__interrupt__);

  // Approve and resume
  const resumed = await agent.invoke(
    new Command({ resume: { decisions: [{ type: "approve" }] } }), config
  );
}
```
</typescript>
</ex-hitl-middleware>

<ex-error-middleware>
<python>
Catch and handle tool errors gracefully with custom middleware.
```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call

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
import { createAgent, createMiddleware } from "langchain";

const errorHandler = createMiddleware({
  name: "ErrorHandler",
  wrapToolCall: async (request, handler) => {
    try {
      return await handler(request);
    } catch (error) {
      return {
        ...request.toolCall,
        content: `Tool error: ${error}. Please try a different approach.`,
      };
    }
  },
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

`create_agent` accepts model strings (`"anthropic:claude-sonnet-4-5"`, `"openai:gpt-4.1"`) or model instances for custom settings:

```python
from langchain_anthropic import ChatAnthropic
agent = create_agent(model=ChatAnthropic(model="claude-sonnet-4-5", temperature=0), tools=[...])
```
</model_config>

<ex-custom-middleware>
## Defining Custom Middleware

Middleware hooks: `before_model`, `after_model`, `wrap_tool_call`, `before_agent`, `after_agent`, `wrap_model_call`.

<python>
```python
from langchain.agents.middleware import wrap_tool_call

# @wrap_tool_call creates middleware from a function
@wrap_tool_call
async def retry_on_error(request, handler):
    """Retry failed tool calls once before giving up."""
    try:
        return await handler(request)
    except Exception:
        return await handler(request)  # Retry once

# Apply to specific tools only
@wrap_tool_call(tools=[flaky_api_tool], name="RetryFlaky")
async def retry_flaky(request, handler):
    return await handler(request)

agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=[flaky_api_tool, stable_tool],
    middleware=[retry_on_error],
)
```
</python>
<typescript>
```typescript
import { createMiddleware } from "langchain";

// createMiddleware accepts hook functions
const retryOnError = createMiddleware({
  name: "RetryOnError",
  wrapToolCall: async (request, handler) => {
    try {
      return await handler(request);
    } catch {
      return await handler(request); // Retry once
    }
  },
});

const agent = createAgent({
  model: "anthropic:claude-sonnet-4-5",
  tools: [flakyApiTool, stableTool],
  middleware: [retryOnError],
});
```
</typescript>
</ex-custom-middleware>

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
Set recursion_limit in the invoke config to prevent runaway agent loops.
```python
# WRONG: No iteration limit - could loop forever
result = agent.invoke({"messages": [("user", "Do research")]})

# CORRECT: Set recursion_limit in config
result = agent.invoke(
    {"messages": [("user", "Do research")]},
    config={"recursion_limit": 10},  # Stop after 10 steps
)
```
</python>
<typescript>
Set recursionLimit in the invoke config to prevent runaway agent loops.
```typescript
// WRONG: No iteration limit
const result = await agent.invoke({ messages: [["user", "Do research"]] });

// CORRECT: Set recursionLimit in config
const result = await agent.invoke(
  { messages: [["user", "Do research"]] },
  { recursionLimit: 10 }, // Stop after 10 steps
);
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
