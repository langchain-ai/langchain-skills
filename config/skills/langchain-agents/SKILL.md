---
name: langchain-agents
description: Use this skill for ANY coding question involving LangChain products (LangChain, LangGraph, LangSmith SDK). Covers agent development patterns, primitives, context management, multi-agent systems, and when to use create_agent vs create_deep_agent vs raw LangGraph. Consult this BEFORE writing any LangChain-related code.
---

# LangChain Ecosystem Guide

Build production-ready agents with LangGraph, from basic primitives to advanced context management.

## Quick Start: Which Tool?

**IMPORTANT:** Use modern abstractions. Older helpers like `create_sql_agent`, `create_tool_calling_agent`, `create_react_agent`, etc. are outdated.

**Simple tool-calling agent?** → [`create_agent`](https://docs.langchain.com/oss/python/langchain/agents)
```python
from langchain.agents import create_agent
graph = create_agent(model="anthropic:claude-sonnet-4-5", tools=[search], system_prompt="...")
```
**Use this for:** Basic ReAct loops, tool-calling agents, simple Q&A bots.

**Need planning + filesystem + subagents?** → [`create_deep_agent`](https://docs.langchain.com/oss/python/deepagents/overview)
```python
from deepagents import create_deep_agent
agent = create_deep_agent(model=model, tools=tools, backend=FilesystemBackend())
```
**Use this for:** Research agents, complex workflows, agents that need to store intermediate results, multi-step planning.

**Custom control flow / multi-agent / advanced context?** → **LangGraph** (this guide)
**Use this for:** Custom routing logic, supervisor patterns, specialized state management, non-standard workflows.

**Start simple:** Build with basic ReAct loops first. Only add complexity (multi-agent, advanced context management) when your use case requires it.

## 1. Core Primitives

### Using create_agent (Recommended Starting Point)

```python
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.tools import tool

@tool
def my_tool(query: str) -> str:
    """Tool description that the model sees."""
    return perform_operation(query)

model = ChatAnthropic(model="claude-sonnet-4-5")
agent = create_agent(
    model=model,
    tools=[my_tool],
    system_prompt="Your agent behavior and guidelines."
)

result = agent.invoke({"messages": [("user", "Your question")]})
```

**Pattern applies to:** SQL agents, search agents, Q&A bots, tool-calling workflows.
**Replaces:** Legacy convenience helpers and `LLMChain` patterns.

### Example: Calculator Agent

```python
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.tools import tool

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    try:
        # Only allow safe math operations
        allowed = set('0123456789+-*/(). ')
        if not all(c in allowed for c in expression):
            return "Error: Invalid characters"
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

@tool
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between common units."""
    conversions = {
        ("km", "miles"): 0.621371,
        ("miles", "km"): 1.60934,
        ("kg", "lbs"): 2.20462,
        ("lbs", "kg"): 0.453592,
    }
    factor = conversions.get((from_unit, to_unit), None)
    if factor:
        return f"{value * factor:.2f} {to_unit}"
    return "Conversion not supported"

model = ChatAnthropic(model="claude-sonnet-4-5")
agent = create_agent(
    model=model,
    tools=[calculate, convert_units],
    system_prompt="You are a helpful calculator assistant."
)

result = agent.invoke({"messages": [("user", "What is 15% of 250?")]})
```

**Pattern applies to:** SQL agents, search agents, Q&A bots, tool-calling workflows.

### Basic ReAct Agent from Scratch

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

class State(TypedDict):
    messages: Annotated[list, add_messages]

tools = [search_tool]
tool_node = ToolNode(tools)  # Handles ToolMessage generation

def agent(state: State):
    return {"messages": [model.bind_tools(tools).invoke(state["messages"])]}

def route(state: State):
    return "tools" if state["messages"][-1].tool_calls else END

# Build graph
workflow = StateGraph(State)
workflow.add_node("agent", agent)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", route)
workflow.add_edge("tools", "agent")
app = workflow.compile()
```

**The loop:** Agent → tools → agent → END

### ToolMessages: Critical Detail

When implementing custom tool execution, you **must** create a `ToolMessage` for each tool call:

```python
def custom_tool_node(state: State) -> dict:
    """Execute tools manually."""
    last_message = state["messages"][-1]
    tool_messages = []

    for tool_call in last_message.tool_calls:
        result = execute_tool(tool_call["name"], tool_call["args"])

        # CRITICAL: tool_call_id must match!
        tool_messages.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))

    return {"messages": tool_messages}
```

### Commands: Routing with Updates

```python
from langgraph.types import Command
from typing import Literal

def router(state: State) -> Command[Literal["research", "write", END]]:
    """Route and update state simultaneously."""
    if needs_more_context(state):
        return Command(
            update={"notes": "Starting research phase"},
            goto="research"
        )
    return Command(goto=END)

# Human-in-loop: pause and resume
def ask_user(state: State) -> Command:
    response = interrupt("Please clarify:")
    return Command(
        update={"messages": [HumanMessage(content=response)]},
        goto="continue"
    )

# Resume: graph.invoke(Command(resume=user_input), config)
```

## 2. Context Management Strategies

### Strategy 1: Subagent Delegation

**Pattern:** Offload work to subagents, return only summaries.

```python
# Specialized subagent (compiles full workflow internally)
researcher_subgraph = build_researcher_graph().compile()

# Main agent delegates
def main_agent(state: State) -> Command:
    if needs_research(state["messages"][-1]):
        result = researcher_subgraph.invoke({"query": extract_query(state)})
        # Add ONLY summary to main context
        return Command(
            update={"context": state["context"] + f"\n{result['summary']}"},
            goto="respond"
        )
    return Command(goto="respond")
```

**Why:** Subagent handles complexity, main agent only sees compressed summary.

### Strategy 2: Filesystem Context Management

**Pattern:** Write intermediate work to files, pass file paths instead of full content.

```python
class State(TypedDict):
    messages: Annotated[list, add_messages]
    context_files: list[str]  # File paths, not content

def research_and_save(state: State) -> dict:
    research_result = conduct_research(state["messages"][-1])
    file_path = Path("workspace") / f"research_{len(state['context_files'])}.json"

    with open(file_path, "w") as f:
        json.dump(research_result, f)

    return {"context_files": [str(file_path)]}  # Store path only

def respond_with_context(state: State) -> dict:
    # Load only last 3 files
    context = [json.load(open(p)) for p in state["context_files"][-3:]]
    messages = state["messages"] + [SystemMessage(content=str(context))]
    return {"messages": [model.invoke(messages)]}
```

**Why:** State stays small, full context lives in files, load selectively.

### Strategy 3: Progressive Message Trimming

**Pattern:** Remove old messages but preserve recent context and critical system messages.

```python
def trim_messages(messages: list, max_messages: int = 20) -> list:
    """Keep system messages + recent conversation."""
    # Separate system messages from conversation
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    conversation = [m for m in messages if not isinstance(m, SystemMessage)]

    # Keep only recent conversation
    recent = conversation[-max_messages:]

    # Recombine
    return system_msgs + recent

def agent_with_trimming(state: State) -> dict:
    """Call model with trimmed context."""
    trimmed = trim_messages(state["messages"], max_messages=15)
    response = model.invoke(trimmed)
    return {"messages": [response]}
```

**Advanced: Remove by token count**
```python
def trim_by_tokens(messages: list, max_tokens: int = 4000) -> list:
    """Trim to fit token budget."""
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    conversation = [m for m in messages if not isinstance(m, SystemMessage)]

    # Count tokens (pseudo-code, use tiktoken)
    total_tokens = sum(count_tokens(m) for m in conversation)

    while total_tokens > max_tokens and len(conversation) > 5:
        # Remove oldest non-system message
        removed = conversation.pop(0)
        total_tokens -= count_tokens(removed)

    return system_msgs + conversation
```

### Strategy 4: Compression with Summarization

**Pattern:** Summarize old context into compact form, keep only recent messages raw.

```python
def compress_history(state: State) -> dict:
    """Compress old messages into summary."""
    messages = state["messages"]

    # If conversation too long, compress
    if len(messages) > 30:
        # Separate into old (to compress) and recent (keep raw)
        old_messages = messages[:-10]
        recent_messages = messages[-10:]

        # Summarize old messages
        summary_prompt = f"""Summarize this conversation history concisely:
{format_messages(old_messages)}"""

        summary = model.invoke([HumanMessage(content=summary_prompt)])

        # Replace old messages with summary
        compressed = [
            SystemMessage(content=f"Previous context:\n{summary.content}")
        ] + recent_messages

        return {"messages": {"type": "override", "value": compressed}}

    return {}  # No compression needed

# Custom reducer for override
def override_reducer(current: list, update: dict | list) -> list:
    if isinstance(update, dict) and update.get("type") == "override":
        return update["value"]
    return current + (update if isinstance(update, list) else [update])

class State(TypedDict):
    messages: Annotated[list, override_reducer]
```

### Strategy 5: Hierarchical Context with State Layers

**Pattern:** Separate working memory (ephemeral) from long-term context (persistent).

```python
class WorkingState(TypedDict):
    """Ephemeral working memory."""
    messages: Annotated[list, add_messages]
    current_task: str

class LongTermState(TypedDict):
    """Persistent context across tasks."""
    user_id: str
    learned_facts: list[str]
    conversation_summaries: list[str]

class FullState(WorkingState, LongTermState):
    """Combined state."""
    pass

def agent_with_context_layers(state: FullState, store: BaseStore) -> dict:
    """Use hierarchical context."""
    # Load long-term context
    namespace = ("users", state["user_id"])
    learned = store.get(namespace, "facts")

    # Build prompt with layers
    long_term_context = "\n".join(learned.value if learned else [])
    working_context = state["current_task"]

    prompt = f"""Long-term context:
{long_term_context}

Current task: {working_context}

Recent conversation:
{format_messages(state["messages"][-5:])}"""

    response = model.invoke([SystemMessage(content=prompt)])
    return {"messages": [response]}

def save_learnings(state: FullState, store: BaseStore) -> dict:
    """Persist important facts."""
    namespace = ("users", state["user_id"])

    # Extract learnings from conversation
    learnings = extract_key_facts(state["messages"])

    # Append to long-term storage
    existing = store.get(namespace, "facts")
    all_facts = (existing.value if existing else []) + learnings
    store.put(namespace, "facts", all_facts)

    return {}
```

### Strategy 6: Dynamic Subagent Context Isolation

**Pattern:** Spawn subagents with only relevant context slice, not entire conversation.

```python
def spawn_focused_subagent(state: State, task: str) -> dict:
    """Create subagent with minimal context."""
    # Extract only relevant messages for this task
    relevant_msgs = filter_relevant_messages(state["messages"], task)

    # Create subagent with focused context
    subagent_state = {
        "messages": relevant_msgs[-5:],  # Only last 5 relevant msgs
        "task": task
    }

    result = subagent.invoke(subagent_state)

    # Bring back only the final answer
    return {
        "messages": [AIMessage(content=f"Task '{task}' complete: {result['answer']}")]
    }

def filter_relevant_messages(messages: list, task: str) -> list:
    """Use embedding similarity to find relevant messages."""
    task_embedding = embed(task)

    scored = []
    for msg in messages:
        if isinstance(msg, (HumanMessage, AIMessage)):
            similarity = cosine_similarity(task_embedding, embed(msg.content))
            scored.append((similarity, msg))

    # Return top-k most relevant
    scored.sort(reverse=True)
    return [msg for _, msg in scored[:10]]
```

## 3. Multi-Agent Patterns

### Supervisor with Context Budget

```python
class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    research_notes: list[str]  # Summaries only
    next_agent: str

def supervisor(state: SupervisorState) -> Command[Literal["researcher", "writer", END]]:
    """Coordinate agents with compressed context."""
    # Build minimal context for routing decision
    recent = state["messages"][-3:]
    summaries = "\n".join(state["research_notes"][-2:])  # Only recent summaries

    routing_prompt = f"""Recent conversation: {recent}
Research summaries: {summaries}
What should we do next?"""

    decision = routing_model.with_structured_output(Routing).invoke([
        HumanMessage(content=routing_prompt)
    ])

    if decision.done:
        return Command(goto=END)
    return Command(goto=decision.next_agent)

def researcher(state: SupervisorState) -> dict:
    """Research and return summary only."""
    research_result = conduct_research(state["messages"][-1])

    # Compress research into summary
    summary = summarize(research_result)

    return {
        "research_notes": [summary],  # Add summary, not full result
        "messages": [AIMessage(content="Research complete")]
    }
```

### Parallel Subagents with Result Synthesis

```python
async def parallel_research_with_synthesis(state: State) -> dict:
    """Run multiple subagents, synthesize results."""
    query = state["messages"][-1].content

    # Spawn 3 researchers with different strategies
    tasks = [
        researcher_1.ainvoke({"query": query, "strategy": "academic"}),
        researcher_2.ainvoke({"query": query, "strategy": "news"}),
        researcher_3.ainvoke({"query": query, "strategy": "social"})
    ]

    results = await asyncio.gather(*tasks)

    # Synthesize into single summary
    synthesis_prompt = f"""Synthesize these research results:
1. Academic: {results[0]['summary']}
2. News: {results[1]['summary']}
3. Social: {results[2]['summary']}

Provide unified 3-sentence summary:"""

    synthesis = model.invoke([HumanMessage(content=synthesis_prompt)])

    # Return only synthesis, not individual results
    return {"messages": [synthesis]}
```

## 4. Practical Patterns

### Checkpointer + Store for Persistence

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

checkpointer = MemorySaver()  # Thread-level state
store = InMemoryStore()       # Cross-thread memory

app = graph.compile(
    checkpointer=checkpointer,  # Enables conversation continuity
    store=store                  # Enables learning across conversations
)

# Thread-specific conversation
app.invoke(
    {"messages": [HumanMessage("Hello")]},
    config={"configurable": {"thread_id": "user-123"}}
)
```

### Structured Output for Reliability

```python
from pydantic import BaseModel, Field

class ResearchOutput(BaseModel):
    summary: str = Field(description="3-sentence summary")
    sources: list[str] = Field(description="Source URLs")
    confidence: float = Field(description="0-1 confidence score")

model_with_structure = model.with_structured_output(ResearchOutput)

def structured_research(state: State) -> dict:
    result = model_with_structure.invoke(state["messages"])
    # result is guaranteed to have summary, sources, confidence
    return {"research": result.model_dump()}
```

### Middleware for Cross-Cutting Concerns

**Pattern:** Wrap nodes with logging, timing, error handling, or filtering.

```python
def logging_middleware(func):
    """Log inputs/outputs for any node."""
    def wrapper(state):
        print(f"[{func.__name__}] Input: {state}")
        result = func(state)
        print(f"[{func.__name__}] Output: {result}")
        return result
    return wrapper

# Apply to nodes
workflow.add_node("agent", logging_middleware(agent))

# Or apply at compile time for all nodes
app = workflow.compile(middleware=[logging_middleware])
```

## 5. DeepAgents: Batteries Included

When you need context management built-in:

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend

# Mix filesystem (working files) + store (memories)
backend = CompositeBackend({
    "/workspace/": FilesystemBackend("./workspace"),
    "/memories/": StoreBackend(store)
})

agent = create_deep_agent(
    model=model,
    tools=[search, scrape],
    subagents=[researcher_agent, analyst_agent],
    backend=backend
)
```

**DeepAgents provides:**
- Filesystem: Write/read context files automatically
- Planning: Break tasks into steps
- Subagents: Delegate to specialists
- Memory: Persistent storage across sessions

## Quick Reference

**Context Management:**
```python
# Subagent delegation → compress result
result = subagent.invoke(query)
return {"context": result["summary"]}

# Filesystem → store path, not content
with open(file_path, "w") as f: json.dump(data, f)
return {"files": [str(file_path)]}

# Trim messages → keep recent
messages[-20:]

# Compress → summarize old
summary = model.invoke(f"Summarize: {old_msgs}")
return {"messages": [SystemMessage(summary)] + recent}

# Hierarchical → separate working/long-term
prompt = f"{long_term_context}\n{working_context}"

# Focused subagent → relevant slice only
subagent.invoke({"messages": relevant[-5:]})
```

**Commands:**
```python
Command(update={...}, goto="next")
Command(goto=END)
Command(resume=user_input)
```

**Tool Messages:**
```python
ToolMessage(content=result, tool_call_id=call["id"])
```

**State Override:**
```python
{"messages": {"type": "override", "value": compressed}}
```

## Resources

- [LangGraph Docs](https://docs.langchain.com/langgraph)
- [create_agent](https://docs.langchain.com/oss/python/langchain/agents)
- [DeepAgents](https://docs.langchain.com/oss/python/deepagents/overview)
- [LangGraph 101 Multi-Agent](https://github.com/langchain-ai/langgraph-101/blob/main/notebooks/LG201/multi_agent.ipynb)
- [Deep Research Example](https://github.com/langchain-samples/deep_research_101)
