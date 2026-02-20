---
name: LangGraph Fundamentals
description: "INVOKE THIS SKILL when writing ANY LangGraph code. Covers StateGraph creation, node functions, edges, state schemas with reducers (Annotated), and the Command API. CRITICAL: Contains fixes for returning partial state updates (not full state), missing reducers, and mutable defaults."
---

<overview>
LangGraph models agent workflows as **directed graphs**:

- **StateGraph**: Main class for building stateful graphs
- **Nodes**: Functions that perform work and update state
- **Edges**: Define execution order (static or conditional)
- **START/END**: Special nodes marking entry and exit points
- **State with Reducers**: Control how state updates are merged

Graphs must be `compile()`d before execution.
</overview>

<when-to-use-langgraph>

| Use LangGraph When | Use Alternatives When |
|-------------------|----------------------|
| Need fine-grained control over agent orchestration | Quick prototyping → LangChain agents |
| Building complex workflows with branching/loops | Simple stateless workflows → LCEL |
| Require human-in-the-loop, persistence | Batteries-included features → Deep Agents |

</when-to-use-langgraph>

---

## State Management

<state-update-strategies>

| Need | Solution | Example |
|------|----------|---------|
| Overwrite value | No reducer (default) | Simple fields like counters |
| Append to list | Reducer (operator.add / concat) | Message history, logs |
| Custom logic | Custom reducer function | Complex merging |

</state-update-strategies>

<ex-state-with-reducer>
<python>
Define state schema with reducers for accumulating lists and summing integers.
```python
from typing_extensions import TypedDict, Annotated
import operator

class State(TypedDict):
    name: str  # Default: overwrites on update
    messages: Annotated[list, operator.add]  # Appends to list
    total: Annotated[int, operator.add]  # Sums integers
```
</python>
<typescript>
Use StateSchema with ReducedValue for accumulating arrays.
```typescript
import { StateSchema, ReducedValue, MessagesValue } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  name: z.string(),  // Default: overwrites
  messages: MessagesValue,  // Built-in for messages
  items: new ReducedValue(
    z.array(z.string()).default(() => []),
    { reducer: (current, update) => current.concat(update) }
  ),
});
```
</typescript>
</ex-state-with-reducer>

<ex-messages-accumulating>
<python>
Messages accumulate via reducer - new messages append, not overwrite.
```python
from typing import Annotated
import operator
from langchain.messages import BaseMessage, HumanMessage, AIMessage

class MessagesState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

def add_response(state: MessagesState) -> dict:
    user_msg = state["messages"][-1].content
    return {"messages": [AIMessage(content=f"Response to: {user_msg}")]}

# After invoke: messages list has BOTH original + response (not overwritten)
```
</python>
<typescript>
MessagesValue provides built-in accumulation for message arrays.
```typescript
import { StateSchema, MessagesValue, StateGraph, START, END } from "@langchain/langgraph";
import { HumanMessage, AIMessage } from "@langchain/core/messages";

const State = new StateSchema({ messages: MessagesValue });

const addResponse = async (state: typeof State.State) => {
  const lastMessage = state.messages.at(-1);
  return { messages: [new AIMessage({ content: `Response to: ${lastMessage?.content}` })] };
};

// After invoke: messages list has BOTH original + response
```
</typescript>
</ex-messages-accumulating>

<fix-forgot-reducer-for-list>
<python>
Without a reducer, returning a list overwrites previous values.
```python
# WRONG: List will be OVERWRITTEN
class State(TypedDict):
    messages: list  # No reducer!

# Node 1 returns: {"messages": ["A"]}
# Node 2 returns: {"messages": ["B"]}
# Final: {"messages": ["B"]}  # "A" is LOST!

# CORRECT: Use Annotated with operator.add
from typing import Annotated
import operator

class State(TypedDict):
    messages: Annotated[list, operator.add]
# Final: {"messages": ["A", "B"]}
```
</python>
<typescript>
Without ReducedValue, arrays are overwritten not appended.
```typescript
// WRONG: Array will be overwritten
const State = new StateSchema({
  items: z.array(z.string()),  // No reducer!
});
// Node 1: { items: ["A"] }, Node 2: { items: ["B"] }
// Final: { items: ["B"] }  // A is lost!

// CORRECT: Use ReducedValue
const State = new StateSchema({
  items: new ReducedValue(
    z.array(z.string()).default(() => []),
    { reducer: (current, update) => current.concat(update) }
  ),
});
// Final: { items: ["A", "B"] }
```
</typescript>
</fix-forgot-reducer-for-list>

<fix-state-must-return-dict>
<python>
Nodes must return partial updates, not mutate and return full state.
```python
# WRONG: Returning entire state object
def my_node(state: State) -> State:
    state["field"] = "updated"
    return state  # Don't mutate and return!

# CORRECT: Return dict with only the updates
def my_node(state: State) -> dict:
    return {"field": "updated"}
```
</python>
<typescript>
Return partial updates only, not the full state object.
```typescript
// WRONG: Returning entire state
const myNode = async (state: typeof State.State) => {
  state.field = "updated";
  return state;  // Don't do this!
};

// CORRECT: Return partial updates
const myNode = async (state: typeof State.State) => {
  return { field: "updated" };
};
```
</typescript>
</fix-state-must-return-dict>

---

## Building Graphs

<edge-type-selection>

| Need | Edge Type | When to Use |
|------|-----------|-------------|
| Always go to same node | `add_edge()` | Fixed, deterministic flow |
| Route based on state | `add_conditional_edges()` | Dynamic branching |
| Update state AND route | `Command` | Combine logic in single node |
| Fan-out to multiple nodes | `Send` | Parallel processing with dynamic inputs |

</edge-type-selection>

<ex-basic-graph>
<python>
Simple two-node graph with linear edges.
```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class State(TypedDict):
    input: str
    output: str

def process_input(state: State) -> dict:
    return {"output": f"Processed: {state['input']}"}

def finalize(state: State) -> dict:
    return {"output": state["output"].upper()}

graph = (
    StateGraph(State)
    .add_node("process", process_input)
    .add_node("finalize", finalize)
    .add_edge(START, "process")
    .add_edge("process", "finalize")
    .add_edge("finalize", END)
    .compile()
)

result = graph.invoke({"input": "hello"})
print(result["output"])  # "PROCESSED: HELLO"
```
</python>
<typescript>
Chain nodes with addEdge and compile before invoking.
```typescript
import { StateGraph, StateSchema, START, END } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  input: z.string(),
  output: z.string().default(""),
});

const processInput = async (state: typeof State.State) => {
  return { output: `Processed: ${state.input}` };
};

const finalize = async (state: typeof State.State) => {
  return { output: state.output.toUpperCase() };
};

const graph = new StateGraph(State)
  .addNode("process", processInput)
  .addNode("finalize", finalize)
  .addEdge(START, "process")
  .addEdge("process", "finalize")
  .addEdge("finalize", END)
  .compile();

const result = await graph.invoke({ input: "hello" });
console.log(result.output);  // "PROCESSED: HELLO"
```
</typescript>
</ex-basic-graph>

<ex-conditional-edges>
<python>
Route to different nodes based on state with conditional edges.
```python
from typing import Literal
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    query: str
    route: str

def classify(state: State) -> dict:
    if "weather" in state["query"].lower():
        return {"route": "weather"}
    return {"route": "general"}

def route_query(state: State) -> Literal["weather", "general"]:
    return state["route"]

graph = (
    StateGraph(State)
    .add_node("classify", classify)
    .add_node("weather", lambda s: {"result": "Sunny, 72F"})
    .add_node("general", lambda s: {"result": "General response"})
    .add_edge(START, "classify")
    .add_conditional_edges("classify", route_query, ["weather", "general"])
    .add_edge("weather", END)
    .add_edge("general", END)
    .compile()
)
```
</python>
<typescript>
addConditionalEdges routes based on function return value.
```typescript
import { StateGraph, StateSchema, START, END } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  query: z.string(),
  route: z.string().default(""),
});

const classify = async (state: typeof State.State) => {
  if (state.query.toLowerCase().includes("weather")) {
    return { route: "weather" };
  }
  return { route: "general" };
};

const routeQuery = (state: typeof State.State) => state.route;

const graph = new StateGraph(State)
  .addNode("classify", classify)
  .addNode("weather", async () => ({ result: "Sunny, 72F" }))
  .addNode("general", async () => ({ result: "General response" }))
  .addEdge(START, "classify")
  .addConditionalEdges("classify", routeQuery, ["weather", "general"])
  .addEdge("weather", END)
  .addEdge("general", END)
  .compile();
```
</typescript>
</ex-conditional-edges>

<ex-command-state-and-routing>
<python>
Command lets you update state AND choose next node in one return.
```python
from langgraph.types import Command
from typing import Literal

class State(TypedDict):
    count: int
    result: str

def node_a(state: State) -> Command[Literal["node_b", "node_c"]]:
    """Update state AND decide next node in one return."""
    new_count = state["count"] + 1
    if new_count > 5:
        return Command(update={"count": new_count}, goto="node_c")
    return Command(update={"count": new_count}, goto="node_b")

graph = (
    StateGraph(State)
    .add_node("node_a", node_a)
    .add_node("node_b", lambda s: {"result": "B"})
    .add_node("node_c", lambda s: {"result": "C"})
    .add_edge(START, "node_a")
    .add_edge("node_b", END)
    .add_edge("node_c", END)
    .compile()
)
```
</python>
<typescript>
Return Command with update and goto to combine state change with routing.
```typescript
import { StateGraph, StateSchema, START, END, Command } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  count: z.number().default(0),
  result: z.string().default(""),
});

const nodeA = async (state: typeof State.State) => {
  const newCount = state.count + 1;
  if (newCount > 5) {
    return new Command({ update: { count: newCount }, goto: "node_c" });
  }
  return new Command({ update: { count: newCount }, goto: "node_b" });
};

const graph = new StateGraph(State)
  .addNode("node_a", nodeA)
  .addNode("node_b", async () => ({ result: "B" }))
  .addNode("node_c", async () => ({ result: "C" }))
  .addEdge(START, "node_a")
  .addEdge("node_b", END)
  .addEdge("node_c", END)
  .compile();
```
</typescript>
</ex-command-state-and-routing>

<ex-map-reduce-with-send>
<python>
Send creates parallel workers; reducer accumulates their results.
```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing import Annotated
import operator

class State(TypedDict):
    items: list[str]
    results: Annotated[list, operator.add]  # Accumulates from parallel workers

def fan_out(state: State):
    return [Send("worker", {"item": item}) for item in state["items"]]

def worker(state: dict) -> dict:
    return {"results": [f"Processed: {state['item']}"]}

graph = (
    StateGraph(State)
    .add_node("worker", worker)
    .add_conditional_edges(START, fan_out, ["worker"])
    .add_edge("worker", END)
    .compile()
)
# invoke({"items": ["a", "b", "c"]}) -> results: ["Processed: a", "Processed: b", "Processed: c"]
```
</python>
<typescript>
Map items to Send objects for parallel execution.
```typescript
import { StateGraph, StateSchema, START, END, Send, ReducedValue } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  items: z.array(z.string()),
  results: new ReducedValue(z.array(z.string()).default(() => []), {
    reducer: (current, update) => current.concat(update)
  }),
});

const fanOut = (state: typeof State.State) =>
  state.items.map((item) => new Send("worker", { item }));

const worker = async (state: { item: string }) =>
  ({ results: [`Processed: ${state.item}`] });

const graph = new StateGraph(State)
  .addNode("worker", worker)
  .addConditionalEdges(START, fanOut, ["worker"])
  .addEdge("worker", END)
  .compile();
// invoke({ items: ["a", "b", "c"] }) -> results: ["Processed: a", "Processed: b", "Processed: c"]
```
</typescript>
</ex-map-reduce-with-send>

<ex-graph-with-loop>
<python>
Conditional edge to END prevents infinite loops.
```python
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    count: int
    max_iterations: int

def increment(state: State) -> dict:
    return {"count": state["count"] + 1}

def should_continue(state: State) -> str:
    if state["count"] >= state["max_iterations"]:
        return END
    return "increment"

graph = (
    StateGraph(State)
    .add_node("increment", increment)
    .add_edge(START, "increment")
    .add_conditional_edges("increment", should_continue)
    .compile()
)

result = graph.invoke({"count": 0, "max_iterations": 5})
print(result["count"])  # 5
```
</python>
<typescript>
Return END from conditional function to terminate loop.
```typescript
import { StateGraph, StateSchema, START, END } from "@langchain/langgraph";
import { z } from "zod";

const State = new StateSchema({
  count: z.number().default(0),
  maxIterations: z.number(),
});

const increment = async (state: typeof State.State) => {
  return { count: state.count + 1 };
};

const shouldContinue = (state: typeof State.State) => {
  if (state.count >= state.maxIterations) return END;
  return "increment";
};

const graph = new StateGraph(State)
  .addNode("increment", increment)
  .addEdge(START, "increment")
  .addConditionalEdges("increment", shouldContinue)
  .compile();

const result = await graph.invoke({ count: 0, maxIterations: 5 });
console.log(result.count);  // 5
```
</typescript>
</ex-graph-with-loop>

<fix-compile-before-execution>
<python>
Must compile() to get executable graph.
```python
# WRONG
builder.invoke({"input": "test"})  # AttributeError!

# CORRECT
graph = builder.compile()
graph.invoke({"input": "test"})
```
</python>
<typescript>
Must compile() to get executable graph.
```typescript
// WRONG
await builder.invoke({ input: "test" });

// CORRECT
const graph = builder.compile();
await graph.invoke({ input: "test" });
```
</typescript>
</fix-compile-before-execution>

<fix-infinite-loop-needs-exit>
<python>
Provide conditional path to END to avoid infinite loops.
```python
# WRONG: Loops forever
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", "node_a")

# CORRECT
def should_continue(state):
    return END if state["count"] > 10 else "node_b"
builder.add_conditional_edges("node_a", should_continue)
```
</python>
<typescript>
Use conditional edges with END return to break loops.
```typescript
// WRONG: Loops forever
builder.addEdge("node_a", "node_b").addEdge("node_b", "node_a");

// CORRECT
builder.addConditionalEdges("node_a", (state) => state.count > 10 ? END : "node_b");
```
</typescript>
</fix-infinite-loop-needs-exit>

<fix-conditional-edge-destinations>
<python>
Router must return names of nodes that exist in the graph.
```python
# WRONG: missing_node not added to graph
builder.add_conditional_edges("node_a", router, ["missing_node"])

# CORRECT: Add destination nodes first
builder.add_node("missing_node", func)
builder.add_conditional_edges("node_a", router, ["missing_node"])
```
</python>
</fix-conditional-edge-destinations>

<fix-command-type-annotation>
<python>
Command return type needs Literal for routing destinations.
```python
# WRONG
def node_a(state) -> Command:
    return Command(goto="node_b")

# CORRECT
def node_a(state) -> Command[Literal["node_b", "node_c"]]:
    return Command(goto="node_b")
```
</python>
</fix-command-type-annotation>

<fix-reducer-type-mismatch>
<python>
Reducer expects specific type - return value must match.
```python
# WRONG: Reducer expects list
return {"items": "not a list"}  # Type error!

# CORRECT
return {"items": ["item"]}
```
</python>
</fix-reducer-type-mismatch>

<fix-start-not-destination>
<python>
START is entry-only - cannot route back to it.
```python
# WRONG
builder.add_edge("node_a", START)  # Error!

# CORRECT: Use a named entry node for loops
builder.add_node("entry", entry_func)
builder.add_edge(START, "entry")
builder.add_edge("node_a", "entry")
```
</python>
</fix-start-not-destination>

<fix-always-await-nodes>
<typescript>
Always await graph.invoke() - it returns a Promise.
```typescript
// WRONG
const result = graph.invoke({ input: "test" });  // Promise!

// CORRECT
const result = await graph.invoke({ input: "test" });
```
</typescript>
</fix-always-await-nodes>

<boundaries>
### What You CAN Configure

- Define custom state schemas with TypedDict/StateSchema
- Add reducers to control how state updates are merged
- Create nodes (any function)
- Add static and conditional edges
- Use Command for combined state/routing
- Create loops with conditional termination

### What You CANNOT Configure

- Modify START/END behavior
- Change the Pregel execution model
- Access state outside node functions
- Modify state directly (must return updates)
</boundaries>
