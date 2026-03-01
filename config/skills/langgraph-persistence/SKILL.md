---
name: LangGraph Persistence & Memory
description: "INVOKE THIS SKILL when your LangGraph needs to remember state across calls, use memory, or persist conversations. Covers checkpointers (MemorySaver, Postgres), thread_id configuration, and Store for long-term memory."
---

<overview>
LangGraph's persistence layer enables durable execution by checkpointing graph state:

- **Checkpointer**: Saves/loads graph state at every super-step
- **Thread ID**: Identifies separate checkpoint sequences (conversations)
- **Store**: Cross-thread memory for user preferences, facts

**Two memory types:**
- **Short-term** (checkpointer): Thread-scoped conversation history
- **Long-term** (store): Cross-thread user preferences, facts
</overview>

<checkpointer-selection>

| Checkpointer | Use Case | Production Ready |
|--------------|----------|------------------|
| `MemorySaver` | Testing, development | No |
| `SqliteSaver` | Local development | Partial |
| `PostgresSaver` | Production | Yes |

</checkpointer-selection>

---

## Checkpointer Setup

<ex-basic-persistence>
<python>
Set up a basic graph with in-memory checkpointing and thread-based state persistence.
```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
import operator

class State(TypedDict):
    messages: Annotated[list, operator.add]

def add_message(state: State) -> dict:
    return {"messages": ["Bot response"]}

checkpointer = InMemorySaver()

graph = (
    StateGraph(State)
    .add_node("respond", add_message)
    .add_edge(START, "respond")
    .add_edge("respond", END)
    .compile(checkpointer=checkpointer)  # Pass at compile time
)

# ALWAYS provide thread_id
config = {"configurable": {"thread_id": "conversation-1"}}

result1 = graph.invoke({"messages": ["Hello"]}, config)
print(len(result1["messages"]))  # 2

result2 = graph.invoke({"messages": ["How are you?"]}, config)
print(len(result2["messages"]))  # 4 (previous + new)
```
</python>
<typescript>
Set up a basic graph with in-memory checkpointing and thread-based state persistence.
```typescript
import { MemorySaver, StateGraph, StateSchema, MessagesValue, START, END } from "@langchain/langgraph";
import { HumanMessage } from "@langchain/core/messages";

const State = new StateSchema({ messages: MessagesValue });

const addMessage = async (state: typeof State.State) => {
  return { messages: [{ role: "assistant", content: "Bot response" }] };
};

const checkpointer = new MemorySaver();

const graph = new StateGraph(State)
  .addNode("respond", addMessage)
  .addEdge(START, "respond")
  .addEdge("respond", END)
  .compile({ checkpointer });

// ALWAYS provide thread_id
const config = { configurable: { thread_id: "conversation-1" } };

const result1 = await graph.invoke({ messages: [new HumanMessage("Hello")] }, config);
console.log(result1.messages.length);  // 2

const result2 = await graph.invoke({ messages: [new HumanMessage("How are you?")] }, config);
console.log(result2.messages.length);  // 4 (previous + new)
```
</typescript>
</ex-basic-persistence>

<ex-production-postgres>
<python>
Configure PostgreSQL-backed checkpointing for production deployments.
```python
from langgraph.checkpoint.postgres import PostgresSaver

# from_conn_string returns a context manager in v3+
with PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/db"
) as checkpointer:
    checkpointer.setup()  # only needed on first use to create tables
    graph = builder.compile(checkpointer=checkpointer)
```
</python>
<typescript>
Configure PostgreSQL-backed checkpointing for production deployments.
```typescript
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";

const checkpointer = PostgresSaver.fromConnString(
  "postgresql://user:pass@localhost/db"
);
await checkpointer.setup(); // only needed on first use to create tables

const graph = builder.compile({ checkpointer });
```
</typescript>
</ex-production-postgres>

---

## Thread Management

<ex-separate-threads>
<python>
Demonstrate isolated state between different thread IDs.
```python
# Different threads maintain separate state
alice_config = {"configurable": {"thread_id": "user-alice"}}
bob_config = {"configurable": {"thread_id": "user-bob"}}

graph.invoke({"messages": ["Hi from Alice"]}, alice_config)
graph.invoke({"messages": ["Hi from Bob"]}, bob_config)

# Alice's state is isolated from Bob's
```
</python>
<typescript>
Demonstrate isolated state between different thread IDs.
```typescript
// Different threads maintain separate state
const aliceConfig = { configurable: { thread_id: "user-alice" } };
const bobConfig = { configurable: { thread_id: "user-bob" } };

await graph.invoke({ messages: [new HumanMessage("Hi from Alice")] }, aliceConfig);
await graph.invoke({ messages: [new HumanMessage("Hi from Bob")] }, bobConfig);

// Alice's state is isolated from Bob's
```
</typescript>
</ex-separate-threads>

<ex-resume-from-checkpoint>
<python>
Time travel: browse checkpoint history and replay or fork from a past state.
```python
config = {"configurable": {"thread_id": "session-1"}}

result = graph.invoke({"messages": ["start"]}, config)

# Browse checkpoint history
states = list(graph.get_state_history(config))

# Replay from a past checkpoint
past = states[-2]
result = graph.invoke(None, past.config)  # None = resume from checkpoint

# Or fork: update state at a past checkpoint, then resume
fork_config = graph.update_state(past.config, {"messages": ["edited"]})
result = graph.invoke(None, fork_config)
```
</python>
<typescript>
Time travel: browse checkpoint history and replay or fork from a past state.
```typescript
const config = { configurable: { thread_id: "session-1" } };

const result = await graph.invoke({ messages: ["start"] }, config);

// Browse checkpoint history (async iterable, collect to array)
const states: Awaited<ReturnType<typeof graph.getState>>[] = [];
for await (const state of graph.getStateHistory(config)) {
  states.push(state);
}

// Replay from a past checkpoint
const past = states[states.length - 2];
const replayed = await graph.invoke(null, past.config);  // null = resume from checkpoint

// Or fork: update state at a past checkpoint, then resume
const forkConfig = await graph.updateState(past.config, { messages: ["edited"] });
const forked = await graph.invoke(null, forkConfig);
```
</typescript>
</ex-resume-from-checkpoint>

<ex-update-state>
<python>
Manually update graph state before resuming execution.
```python
config = {"configurable": {"thread_id": "session-1"}}

# Modify state before resuming
graph.update_state(config, {"data": "manually_updated"})

# Resume with updated state
result = graph.invoke(None, config)
```
</python>
<typescript>
Manually update graph state before resuming execution.
```typescript
const config = { configurable: { thread_id: "session-1" } };

// Modify state before resuming
await graph.updateState(config, { data: "manually_updated" });

// Resume with updated state
const result = await graph.invoke(null, config);
```
</typescript>
</ex-update-state>

---

## Long-Term Memory (Store)

<ex-long-term-memory-store>
<python>
Use a Store for cross-thread memory to share user preferences across conversations.
```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# Save user preference (available across ALL threads)
store.put(("alice", "preferences"), "language", {"preference": "short responses"})

# Node with store injection
def respond(state, *, store):
    prefs = store.get((state["user_id"], "preferences"), "language")
    return {"response": f"Using preference: {prefs.value}"}

# Compile with BOTH checkpointer and store
graph = builder.compile(checkpointer=checkpointer, store=store)

# Both threads access same long-term memory
graph.invoke({"user_id": "alice"}, {"configurable": {"thread_id": "thread-1"}})
graph.invoke({"user_id": "alice"}, {"configurable": {"thread_id": "thread-2"}})  # Same preferences!
```
</python>
<typescript>
Use a Store for cross-thread memory to share user preferences across conversations.
```typescript
import { InMemoryStore } from "@langchain/langgraph";

const store = new InMemoryStore();

// Save user preference (available across ALL threads)
await store.put(["alice", "preferences"], "language", { preference: "short responses" });

// Node with store - access via config
const respond = async (state: typeof State.State, config: any) => {
  const item = await config.store.get(["alice", "preferences"], "language");
  return { response: `Using preference: ${item?.value?.preference}` };
};

// Compile with BOTH checkpointer and store
const graph = builder.compile({ checkpointer, store });

// Both threads access same long-term memory
await graph.invoke({ userId: "alice" }, { configurable: { thread_id: "thread-1" } });
await graph.invoke({ userId: "alice" }, { configurable: { thread_id: "thread-2" } });  // Same preferences!
```
</typescript>
</ex-long-term-memory-store>

<ex-store-operations>
<python>
Basic store operations: put, get, search, and delete.
```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

store.put(("user-123", "facts"), "location", {"city": "San Francisco"})  # Put
item = store.get(("user-123", "facts"), "location")  # Get
results = store.search(("user-123", "facts"), filter={"city": "San Francisco"})  # Search
store.delete(("user-123", "facts"), "location")  # Delete
```
</python>
</ex-store-operations>

<boundaries>
### What You CAN Configure

- Choose checkpointer implementation
- Specify thread IDs for conversation isolation
- Retrieve/update state at any checkpoint
- Use stores for cross-thread memory

### What You CANNOT Configure

- Checkpoint timing (happens every super-step)
- Share short-term memory across threads
- Skip checkpointer for persistence features
</boundaries>

<fix-thread-id-required>
<python>
Always provide thread_id in config to enable state persistence.
```python
# WRONG: No thread_id - state NOT persisted!
graph.invoke({"messages": ["Hello"]})
graph.invoke({"messages": ["What did I say?"]})  # Doesn't remember!

# CORRECT: Always provide thread_id
config = {"configurable": {"thread_id": "session-1"}}
graph.invoke({"messages": ["Hello"]}, config)
graph.invoke({"messages": ["What did I say?"]}, config)  # Remembers!
```
</python>
<typescript>
Always provide thread_id in config to enable state persistence.
```typescript
// WRONG: No thread_id - state NOT persisted!
await graph.invoke({ messages: [new HumanMessage("Hello")] });
await graph.invoke({ messages: [new HumanMessage("What did I say?")] });  // Doesn't remember!

// CORRECT: Always provide thread_id
const config = { configurable: { thread_id: "session-1" } };
await graph.invoke({ messages: [new HumanMessage("Hello")] }, config);
await graph.invoke({ messages: [new HumanMessage("What did I say?")] }, config);  // Remembers!
```
</typescript>
</fix-thread-id-required>


<fix-inmemory-not-for-production>
<python>
Use PostgresSaver instead of InMemorySaver for production persistence.
```python
# WRONG: Data lost on process restart
checkpointer = InMemorySaver()  # In-memory only!

# CORRECT: Use persistent storage for production
from langgraph.checkpoint.postgres import PostgresSaver
with PostgresSaver.from_conn_string("postgresql://...") as checkpointer:
    checkpointer.setup()  # only needed on first use to create tables
    graph = builder.compile(checkpointer=checkpointer)
```
</python>
<typescript>
Use PostgresSaver instead of MemorySaver for production persistence.
```typescript
// WRONG: Data lost on process restart
const checkpointer = new MemorySaver();  // In-memory only!

// CORRECT: Use persistent storage for production
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";
const checkpointer = PostgresSaver.fromConnString("postgresql://...");
await checkpointer.setup(); // only needed on first use to create tables
```
</typescript>
</fix-inmemory-not-for-production>

<fix-resume-with-none>
<python>
Pass None to resume from checkpoint instead of providing new input.
```python
# WRONG: Providing new input restarts from beginning
graph.invoke({"messages": ["New message"]}, config)  # Restarts!

# CORRECT: Use None to resume from checkpoint
graph.invoke(None, config)  # Continues from where it paused
```
</python>
<typescript>
Pass null to resume from checkpoint instead of providing new input.
```typescript
// WRONG: Providing new input restarts from beginning
await graph.invoke({ messages: ["New message"] }, config);  // Restarts!

// CORRECT: Use null to resume from checkpoint
await graph.invoke(null, config);  // Continues from where it paused
```
</typescript>
</fix-resume-with-none>

<fix-update-state-with-reducers>
<python>
Use Overwrite to replace state values instead of passing through reducers.
```python
from langgraph.types import Overwrite

# State with reducer: items: Annotated[list, operator.add]
# Current state: {"items": ["A", "B"]}

# update_state PASSES THROUGH reducers
graph.update_state(config, {"items": ["C"]})  # Result: ["A", "B", "C"] - Appended!

# To REPLACE instead, use Overwrite
graph.update_state(config, {"items": Overwrite(["C"])})  # Result: ["C"] - Replaced
```
</python>
<typescript>
Use Overwrite to replace state values instead of passing through reducers.
```typescript
import { Overwrite } from "@langchain/langgraph";

// State with reducer: items uses concat reducer
// Current state: { items: ["A", "B"] }

// updateState PASSES THROUGH reducers
await graph.updateState(config, { items: ["C"] });  // Result: ["A", "B", "C"] - Appended!

// To REPLACE instead, use Overwrite
await graph.updateState(config, { items: new Overwrite(["C"]) });  // Result: ["C"] - Replaced
```
</typescript>
</fix-update-state-with-reducers>

<fix-store-injection>
<python>
Inject store via keyword parameter to access it in graph nodes.
```python
# WRONG: Store not available in node
def my_node(state):
    store.put(...)  # NameError! store not defined

# CORRECT: Inject store via keyword parameter
from langgraph.store.base import BaseStore

def my_node(state, *, store: BaseStore):
    store.put(...)  # Correct store instance injected
```
</python>
<typescript>
Access store via config parameter in graph nodes.
```typescript
// WRONG: Store not available in node
const myNode = async (state) => {
  store.put(...);  // ReferenceError!
};

// CORRECT: Access store via config parameter
const myNode = async (state, config) => {
  await config.store.put(...);  // Correct store instance
};
```
</typescript>
</fix-store-injection>
