---
name: LangGraph Execution Control
description: "INVOKE THIS SKILL for LangGraph workflows, parallel execution, interrupts, or streaming. Covers Send API for fan-out, interrupt() for human-in-the-loop, Command for resuming, and stream modes (values/updates/messages). CRITICAL: Fixes for interrupt without checkpointer, missing reducers for Send, and stream mode tuple unpacking."
---

<overview>
LangGraph provides execution control patterns for complex agent orchestration:

1. **Workflows vs Agents**: Predetermined paths vs dynamic decision-making
2. **Send API**: Fan-out to parallel workers (map-reduce)
3. **Interrupts**: Pause for human input, resume with Command
4. **Streaming**: Real-time state, tokens, and custom data
</overview>

<workflow-vs-agent>

| Characteristic | Workflow | Agent |
|----------------|----------|-------|
| **Control Flow** | Fixed, predetermined | Dynamic, model-driven |
| **Predictability** | High | Low |
| **Use Case** | Sequential tasks | Open-ended problems |

</workflow-vs-agent>

---

## Workflows and Agents

<ex-dynamic-agent>
<python>
ReAct agent pattern: model decides when to call tools, loop until done.
```python
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import ToolMessage
from typing import Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

model_with_tools = model.bind_tools([search])

def agent_node(state: AgentState) -> dict:
    return {"messages": [model_with_tools.invoke(state["messages"])]}

def tool_node(state: AgentState) -> dict:
    """Execute tool calls from the last AI message."""
    result = []
    for tc in state["messages"][-1].tool_calls:
        observation = tools_by_name[tc["name"]].invoke(tc["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tc["id"]))
    return {"messages": result}

def should_continue(state: AgentState):
    return "tools" if state["messages"][-1].tool_calls else END

agent = (
    StateGraph(AgentState)
    .add_node("agent", agent_node)
    .add_node("tools", tool_node)
    .add_edge(START, "agent")
    .add_conditional_edges("agent", should_continue)
    .add_edge("tools", "agent")  # Loop back after tool execution
    .compile()
)
```
</python>
<typescript>
ReAct agent pattern: model decides when to call tools, loop until done.
```typescript
import { StateGraph, StateSchema, MessagesValue, START, END } from "@langchain/langgraph";
import { ToolMessage } from "@langchain/core/messages";

const State = new StateSchema({ messages: MessagesValue });
const modelWithTools = model.bindTools([searchTool]);

const agentNode = async (state: typeof State.State) => ({
  messages: [await modelWithTools.invoke(state.messages)]
});

const toolNode = async (state: typeof State.State) => ({
  messages: await Promise.all(
    (state.messages.at(-1)?.tool_calls ?? []).map(async (tc) =>
      new ToolMessage({ content: await searchTool.invoke(tc.args), tool_call_id: tc.id })
    )
  )
});

const shouldContinue = (state: typeof State.State) =>
  state.messages.at(-1)?.tool_calls?.length ? "tools" : END;

const agent = new StateGraph(State)
  .addNode("agent", agentNode)
  .addNode("tools", toolNode)
  .addEdge(START, "agent")
  .addConditionalEdges("agent", shouldContinue)
  .addEdge("tools", "agent")
  .compile();
```
</typescript>
</ex-dynamic-agent>

<ex-orchestrator-worker>
<python>
Fan out tasks to parallel workers using the Send API and aggregate results.
```python
from langgraph.types import Send
from typing import Annotated
import operator

class OrchestratorState(TypedDict):
    tasks: list[str]
    results: Annotated[list, operator.add]

def orchestrator(state: OrchestratorState):
    """Fan out tasks to workers."""
    return [Send("worker", {"task": task}) for task in state["tasks"]]

def worker(state: dict) -> dict:
    return {"results": [f"Completed: {state['task']}"]}

def synthesize(state: OrchestratorState) -> dict:
    return {"summary": f"Processed {len(state['results'])} tasks"}

graph = (
    StateGraph(OrchestratorState)
    .add_node("worker", worker)
    .add_node("synthesize", synthesize)
    .add_conditional_edges(START, orchestrator, ["worker"])
    .add_edge("worker", "synthesize")
    .add_edge("synthesize", END)
    .compile()
)

result = graph.invoke({"tasks": ["Task A", "Task B", "Task C"]})
```
</python>
<typescript>
Fan out tasks to parallel workers using the Send API and aggregate results.
```typescript
import { Send, StateGraph, StateSchema, ReducedValue, START, END } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  tasks: z.array(z.string()),
  results: new ReducedValue(
    z.array(z.string()).default(() => []),
    { reducer: (curr, upd) => curr.concat(upd) }
  ),
});

const orchestrator = (state: typeof State.State) => {
  return state.tasks.map((task) => new Send("worker", { task }));
};

const worker = async (state: { task: string }) => {
  return { results: [`Completed: ${state.task}`] };
};

const synthesize = async (state: typeof State.State) => {
  return { summary: `Processed ${state.results.length} tasks` };
};

const graph = new StateGraph(State)
  .addNode("worker", worker)
  .addNode("synthesize", synthesize)
  .addConditionalEdges(START, orchestrator, ["worker"])
  .addEdge("worker", "synthesize")
  .addEdge("synthesize", END)
  .compile();
```
</typescript>
</ex-orchestrator-worker>

---

## Interrupts (Human-in-the-Loop)

<interrupt-type-selection>

| Type | When Set | Use Case |
|------|----------|----------|
| Dynamic (`interrupt()`) | Inside node code | Conditional pausing |
| Static (`interrupt_before`) | At compile time | Debug before nodes |
| Static (`interrupt_after`) | At compile time | Review after nodes |

</interrupt-type-selection>

<ex-dynamic-interrupt>
<python>
Pause execution for human review using dynamic interrupt and resume with Command.
```python
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver

def review_node(state):
    if state["needs_review"]:
        user_response = interrupt({
            "action": "review",
            "data": state["draft"],
            "question": "Approve this draft?"
        })
        if user_response == "reject":
            return {"status": "rejected"}
    return {"status": "approved"}

checkpointer = InMemorySaver()

graph = (
    StateGraph(State)
    .add_node("review", review_node)
    .add_edge(START, "review")
    .add_edge("review", END)
    .compile(checkpointer=checkpointer)
)

config = {"configurable": {"thread_id": "1"}}
result = graph.invoke({"needs_review": True, "draft": "content"}, config)

# Check for interrupt
if "__interrupt__" in result:
    print(result["__interrupt__"])

# Resume with user decision
result = graph.invoke(Command(resume="approve"), config)
```
</python>
<typescript>
Pause execution for human review using dynamic interrupt and resume with Command.
```typescript
import { interrupt, Command, MemorySaver, StateGraph, START, END } from "@langchain/langgraph";

const reviewNode = async (state: typeof State.State) => {
  if (state.needsReview) {
    const userResponse = interrupt({
      action: "review",
      data: state.draft,
      question: "Approve this draft?"
    });
    if (userResponse === "reject") {
      return { status: "rejected" };
    }
  }
  return { status: "approved" };
};

const checkpointer = new MemorySaver();

const graph = new StateGraph(State)
  .addNode("review", reviewNode)
  .addEdge(START, "review")
  .addEdge("review", END)
  .compile({ checkpointer });

const config = { configurable: { thread_id: "1" } };
let result = await graph.invoke({ needsReview: true, draft: "content" }, config);

// Check for interrupt
if (result.__interrupt__) {
  console.log(result.__interrupt__);
}

// Resume with user decision
result = await graph.invoke(new Command({ resume: "approve" }), config);
```
</typescript>
</ex-dynamic-interrupt>

<ex-static-breakpoints>
<python>
Set compile-time breakpoints to pause before specific nodes.
```python
graph = (
    StateGraph(State)
    .add_node("step1", step1)
    .add_node("step2", step2)
    .add_edge(START, "step1")
    .add_edge("step1", "step2")
    .add_edge("step2", END)
    .compile(
        checkpointer=checkpointer,
        interrupt_before=["step2"],  # Pause before step2
    )
)

config = {"configurable": {"thread_id": "1"}}
graph.invoke({"data": "test"}, config)  # Runs until step2
graph.invoke(None, config)  # Resume
```
</python>
<typescript>
Set compile-time breakpoints to pause before specific nodes.
```typescript
const graph = new StateGraph(State)
  .addNode("step1", step1)
  .addNode("step2", step2)
  .addEdge(START, "step1")
  .addEdge("step1", "step2")
  .addEdge("step2", END)
  .compile({
    checkpointer,
    interruptBefore: ["step2"],  // Pause before step2
  });

const config = { configurable: { thread_id: "1" } };
await graph.invoke({ data: "test" }, config);  // Runs until step2
await graph.invoke(null, config);  // Resume
```
</typescript>
</ex-static-breakpoints>

---

## Streaming

<stream-mode-selection>

| Mode | What it Streams | Use Case |
|------|----------------|----------|
| `values` | Full state after each step | Monitor complete state |
| `updates` | State deltas | Track incremental updates |
| `messages` | LLM tokens + metadata | Chat UIs |
| `custom` | User-defined data | Progress indicators |

</stream-mode-selection>

<ex-stream-llm-tokens>
<python>
Stream LLM tokens in real-time for chat UI display.
```python
for chunk in graph.stream(
    {"messages": [HumanMessage("Hello")]},
    stream_mode="messages"
):
    token, metadata = chunk
    if hasattr(token, "content"):
        print(token.content, end="", flush=True)
```
</python>
<typescript>
Stream LLM tokens in real-time for chat UI display.
```typescript
for await (const chunk of graph.stream(
  { messages: [new HumanMessage("Hello")] },
  { streamMode: "messages" }
)) {
  const [token, metadata] = chunk;
  if (token.content) {
    process.stdout.write(token.content);
  }
}
```
</typescript>
</ex-stream-llm-tokens>

<ex-stream-custom-data>
<python>
Emit custom progress updates from within nodes using the stream writer.
```python
from langgraph.config import get_stream_writer

def my_node(state):
    writer = get_stream_writer()
    writer("Processing step 1...")
    # Do work
    writer("Complete!")
    return {"result": "done"}

for chunk in graph.stream({"data": "test"}, stream_mode="custom"):
    print(chunk)
```
</python>
<typescript>
Emit custom progress updates from within nodes using the stream writer.
```typescript
import { getWriter } from "@langchain/langgraph";

const myNode = async (state: typeof State.State) => {
  const writer = getWriter();
  writer("Processing step 1...");
  // Do work
  writer("Complete!");
  return { result: "done" };
};

for await (const chunk of graph.stream({ data: "test" }, { streamMode: "custom" })) {
  console.log(chunk);
}
```
</typescript>
</ex-stream-custom-data>

<ex-multiple-stream-modes>
<python>
Stream multiple modes simultaneously.
```python
# Stream multiple modes simultaneously
for mode, chunk in graph.stream(
    {"messages": [HumanMessage("Hi")]},
    stream_mode=["updates", "messages", "custom"]
):
    print(f"{mode}: {chunk}")
```
</python>
</ex-multiple-stream-modes>

<boundaries>
### What You CAN Configure

- Choose workflow vs agent pattern
- Use Send API for parallel execution
- Call `interrupt()` anywhere in nodes
- Set compile-time breakpoints
- Resume with `Command(resume=...)`
- Choose stream modes

### What You CANNOT Configure

- Interrupt without checkpointer
- Resume without thread_id
- Change Send API message-passing model
</boundaries>

<fix-send-accumulator>
<python>
Use a reducer to accumulate parallel worker results (otherwise last worker overwrites).
```python
# WRONG: No reducer - last worker overwrites
class State(TypedDict):
    results: list

# CORRECT
class State(TypedDict):
    results: Annotated[list, operator.add]  # Accumulates
```
</python>
<typescript>
Use ReducedValue to accumulate parallel worker results.
```typescript
// WRONG: No reducer
const State = new StateSchema({ results: z.array(z.string()) });

// CORRECT
const State = new StateSchema({
  results: new ReducedValue(z.array(z.string()).default(() => []), { reducer: (curr, upd) => curr.concat(upd) }),
});
```
</typescript>
</fix-send-accumulator>

<fix-checkpointer-required-for-interrupts>
<python>
Checkpointer required for interrupt functionality.
```python
# WRONG
graph = builder.compile()

# CORRECT
graph = builder.compile(checkpointer=InMemorySaver())
```
</python>
<typescript>
Checkpointer required for interrupt functionality.
```typescript
// WRONG
const graph = builder.compile();

// CORRECT
const graph = builder.compile({ checkpointer: new MemorySaver() });
```
</typescript>
</fix-checkpointer-required-for-interrupts>

<fix-resume-with-command>
<python>
Use Command to resume from an interrupt (regular dict restarts graph).
```python
# WRONG
graph.invoke({"resume_data": "approve"}, config)

# CORRECT
graph.invoke(Command(resume="approve"), config)
```
</python>
<typescript>
Use Command to resume from an interrupt (regular object restarts graph).
```typescript
// WRONG
await graph.invoke({ resumeData: "approve" }, config);

// CORRECT
await graph.invoke(new Command({ resume: "approve" }), config);
```
</typescript>
</fix-resume-with-command>

<fix-agent-guardrails>
<python>
Add max iterations check to prevent infinite loops.
```python
# RISKY: Might loop forever
def should_continue(state):
    if state["messages"][-1].tool_calls:
        return "tools"
    return END

# BETTER
def should_continue(state):
    if state["iterations"] > 10:
        return END
    if state["messages"][-1].tool_calls:
        return "tools"
    return END
```
</python>
<typescript>
Add max iterations check to prevent infinite loops.
```typescript
// RISKY: Might loop forever
const shouldContinue = (state) => state.messages.at(-1)?.tool_calls?.length ? "tools" : END;

// BETTER
const shouldContinue = (state) => {
  if (state.iterations > 10) return END;
  return state.messages.at(-1)?.tool_calls?.length ? "tools" : END;
};
```
</typescript>
</fix-agent-guardrails>

<fix-messages-mode-requires-llm>
<python>
Messages stream mode requires an LLM to be invoked.
```python
# WRONG: No LLM called - nothing streamed
def node(state):
    return {"output": "static text"}

# CORRECT
def node(state):
    response = model.invoke(state["messages"])
    return {"messages": [response]}
```
</python>
</fix-messages-mode-requires-llm>

<fix-custom-mode-needs-stream-writer>
<python>
Use get_stream_writer() to emit custom data.
```python
# WRONG: print() isn't streamed
def node(state):
    print("Processing...")
    return {"data": "done"}

# CORRECT
def node(state):
    writer = get_stream_writer()
    writer("Processing...")  # Streamed!
    return {"data": "done"}
```
</python>
</fix-custom-mode-needs-stream-writer>

<fix-stream-modes-are-lists>
<python>
Pass multiple stream modes as a list, not a string.
```python
# WRONG
graph.stream({}, stream_mode="updates, messages")

# CORRECT
graph.stream({}, stream_mode=["updates", "messages"])
```
</python>
</fix-stream-modes-are-lists>
