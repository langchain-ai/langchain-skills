---
name: LangChain Structured Output & HITL
description: "INVOKE THIS SKILL when you need structured/typed output from LLMs OR human-in-the-loop approval. Covers with_structured_output(), Pydantic schemas, union types for multiple formats, and HITL middleware. CRITICAL: Fixes for accessing structured response wrong, missing field descriptions, and Pydantic v1 vs v2."
---

<overview>
Two critical patterns for production agents:

1. **Structured Output**: Transform unstructured model responses into validated, typed data
2. **Human-in-the-Loop**: Add human oversight to agent tool calls, pausing for approval

**Key Concepts:**
- **response_format**: Define expected output schema
- **with_structured_output()**: Model method for direct structured output
- **human_in_the_loop_middleware**: Pauses execution for human decisions
</overview>

<when-to-use-structured-output>

| Use Case | Use Structured Output? |
|----------|----------------------|
| Extract contact info, dates | Yes |
| Form filling | Yes |
| API integration | Yes |
| Open-ended Q&A | No |

</when-to-use-structured-output>

---

## Structured Output

<ex-basic-structured-output>
<python>
Extract contact information from text using a Pydantic schema with email validation.
```python
from langchain.agents import create_agent
from pydantic import BaseModel, Field

class ContactInfo(BaseModel):
    name: str
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    phone: str

agent = create_agent(model="gpt-4", response_format=ContactInfo)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract: John Doe, john@example.com, (555) 123-4567"}]
})
print(result["structured_response"])
# ContactInfo(name='John Doe', email='john@example.com', phone='(555) 123-4567')
```
</python>
<typescript>
Extract contact information from text using a Zod schema with email validation.
```typescript
import { ChatOpenAI } from "@langchain/openai";
import { z } from "zod";

const ContactInfo = z.object({
  name: z.string(),
  email: z.string().email(),
  phone: z.string(),
});

const model = new ChatOpenAI({ model: "gpt-4" });
const structuredModel = model.withStructuredOutput(ContactInfo);

const response = await structuredModel.invoke(
  "Extract: John Doe, john@example.com, (555) 123-4567"
);
console.log(response);
// { name: 'John Doe', email: 'john@example.com', phone: '(555) 123-4567' }
```
</typescript>
</ex-basic-structured-output>

<ex-model-direct-structured-output>
<python>
Get movie details as a validated Pydantic object using with_structured_output().
```python
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

class Movie(BaseModel):
    """Movie information."""
    title: str = Field(description="Movie title")
    year: int = Field(description="Release year")
    director: str
    rating: float = Field(ge=0, le=10)

model = ChatOpenAI(model="gpt-4")
structured_model = model.with_structured_output(Movie)

response = structured_model.invoke("Tell me about Inception")
print(response)
# Movie(title="Inception", year=2010, director="Christopher Nolan", rating=8.8)
```
</python>
<typescript>
Get movie details as a validated Zod object using withStructuredOutput().
```typescript
import { ChatOpenAI } from "@langchain/openai";
import { z } from "zod";

const Movie = z.object({
  title: z.string().describe("Movie title"),
  year: z.number().describe("Release year"),
  director: z.string(),
  rating: z.number().min(0).max(10),
});

const model = new ChatOpenAI({ model: "gpt-4" });
const structuredModel = model.withStructuredOutput(Movie);

const response = await structuredModel.invoke("Tell me about Inception");
// { title: "Inception", year: 2010, director: "Christopher Nolan", rating: 8.8 }
```
</typescript>
</ex-model-direct-structured-output>

<ex-enum-and-literal-types>
<python>
Define a classification schema with constrained enum values using Literal types.
```python
from pydantic import BaseModel, Field
from typing import Literal

class Classification(BaseModel):
    category: Literal["urgent", "normal", "low"]
    sentiment: Literal["positive", "neutral", "negative"]
    confidence: float = Field(ge=0, le=1)
```
</python>
<typescript>
Define a classification schema with constrained enum values using z.enum().
```typescript
import { z } from "zod";

const Classification = z.object({
  category: z.enum(["urgent", "normal", "low"]),
  sentiment: z.enum(["positive", "neutral", "negative"]),
  confidence: z.number().min(0).max(1),
});
```
</typescript>
</ex-enum-and-literal-types>

<ex-complex-nested-schema>
<python>
Define a complex schema with nested objects and validated fields.
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip: str

class Person(BaseModel):
    name: str
    age: int = Field(gt=0)
    email: str
    address: Address
    tags: List[str] = Field(default_factory=list)
```
</python>
</ex-complex-nested-schema>

---

## Human-in-the-Loop

<ex-basic-hitl-setup>
<python>
Set up an agent with HITL middleware that pauses before sending emails for approval.
```python
from langchain.agents import create_agent, human_in_the_loop_middleware
from langgraph.checkpoint.memory import MemorySaver
from langchain.tools import tool

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to}"

agent = create_agent(
    model="gpt-4",
    tools=[send_email],
    checkpointer=MemorySaver(),  # Required for HITL
    middleware=[
        human_in_the_loop_middleware(
            interrupt_on={
                "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},
            }
        )
    ],
)
```
</python>
<typescript>
Set up an agent with HITL that pauses before sending emails for human approval.
```typescript
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { MemorySaver } from "@langchain/langgraph";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const sendEmail = tool(
  async ({ to, subject, body }) => `Email sent to ${to}`,
  {
    name: "send_email",
    description: "Send an email",
    schema: z.object({ to: z.string(), subject: z.string(), body: z.string() }),
  }
);

const agent = createReactAgent({
  llm: model,
  tools: [sendEmail],
  checkpointer: new MemorySaver(),  // Required for HITL
  interruptBefore: ["send_email"],
});
```
</typescript>
</ex-basic-hitl-setup>

<ex-running-with-interrupts>
<python>
Run the agent, detect an interrupt, then resume execution after human approval.
```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "session-1"}}

# Step 1: Agent runs until it needs to call tool
result1 = agent.invoke({
    "messages": [{"role": "user", "content": "Send email to john@example.com"}]
}, config=config)

# Check for interrupt
if "__interrupt__" in result1:
    print(f"Waiting for approval: {result1['__interrupt__']}")

# Step 2: Human approves
result2 = agent.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config
)
```
</python>
<typescript>
Run the agent, detect an interrupt, then resume execution after human approval.
```typescript
import { Command } from "@langchain/langgraph";

const config = { configurable: { thread_id: "session-1" } };

// Step 1: Agent runs until it needs to call tool
const result1 = await agent.invoke({
  messages: [{ role: "user", content: "Send email to john@example.com" }]
}, config);

// Check for interrupt
if (result1.__interrupt__) {
  console.log(`Waiting for approval: ${result1.__interrupt__}`);
}

// Step 2: Human approves
const result2 = await agent.invoke(
  new Command({ resume: { decisions: [{ type: "approve" }] } }),
  config
);
```
</typescript>
</ex-running-with-interrupts>

<ex-editing-tool-arguments>
<python>
Edit the tool arguments before approving when the original values need correction.
```python
# Human edits the arguments
result2 = agent.invoke(
    Command(resume={
        "decisions": [{
            "type": "edit",
            "args": {
                "to": "alice@company.com",  # Fixed email
                "subject": "Project Meeting - Updated",
                "body": "...",
            },
        }]
    }),
    config=config
)
```
</python>
</ex-editing-tool-arguments>

<ex-rejecting-with-feedback>
<python>
Reject a tool call and provide feedback explaining why it was rejected.
```python
# Human rejects
result2 = agent.invoke(
    Command(resume={
        "decisions": [{
            "type": "reject",
            "feedback": "Cannot delete customer data without manager approval",
        }]
    }),
    config=config
)
```
</python>
</ex-rejecting-with-feedback>

<ex-multiple-tools-different-policies>
<python>
Configure different HITL policies for each tool based on risk level.
```python
agent = create_agent(
    model="gpt-4.1",
    tools=[send_email, read_email, delete_email],
    checkpointer=MemorySaver(),
    middleware=[
        human_in_the_loop_middleware(
            interrupt_on={
                "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},
                "delete_email": {"allowed_decisions": ["approve", "reject"]},  # No edit
                "read_email": False,  # No HITL for reading
            }
        )
    ],
)
```
</python>
</ex-multiple-tools-different-policies>

<boundaries>
### What You CAN Configure

**Structured Output:**
- Schema structure: Any valid Pydantic/Zod model
- Field validation: Types, ranges, regex, etc.

**HITL:**
- Which tools require approval
- Allowed decisions per tool (approve, edit, reject)
</boundaries>

<fix-accessing-response-wrong>
<python>
Access structured output using the correct key.
```python
# WRONG
print(result["response"])  # KeyError!

# CORRECT
print(result["structured_response"])
```
</python>
<typescript>
With withStructuredOutput, response IS the structured data.
```typescript
const response = await structuredModel.invoke("...");
console.log(response);  // Directly the parsed object
```
</typescript>
</fix-accessing-response-wrong>

<fix-missing-descriptions>
<python>
Add field descriptions to guide the model on expected formats.
```python
# WRONG: No descriptions
class Data(BaseModel):
    date: str
    amount: float

# CORRECT
class Data(BaseModel):
    date: str = Field(description="Date in YYYY-MM-DD format")
    amount: float = Field(description="Amount in USD")
```
</python>
<typescript>
Add field descriptions to guide the model on expected formats.
```typescript
// WRONG
const Data = z.object({ date: z.string(), amount: z.number() });

// CORRECT
const Data = z.object({
  date: z.string().describe("Date in YYYY-MM-DD format"),
  amount: z.number().describe("Amount in USD"),
});
```
</typescript>
</fix-missing-descriptions>

<fix-not-using-correct-type-hints>
<python>
Use proper type hints for Pydantic fields for correct schema generation.
```python
# WRONG: Missing type hints
class Data(BaseModel):
    items = []  # No type hint!

# CORRECT
class Data(BaseModel):
    items: List[str] = Field(default_factory=list)
```
</python>
</fix-not-using-correct-type-hints>

<fix-missing-checkpointer>
<python>
HITL middleware requires a checkpointer to persist state.
```python
# WRONG
agent = create_agent(model="gpt-4", tools=[send_email], middleware=[human_in_the_loop_middleware({...})])

# CORRECT
agent = create_agent(
    model="gpt-4", tools=[send_email],
    checkpointer=MemorySaver(),  # Required
    middleware=[human_in_the_loop_middleware({...})]
)
```
</python>
<typescript>
HITL requires a checkpointer to persist state.
```typescript
// WRONG
const agent = createReactAgent({ llm: model, tools: [sendEmail], interruptBefore: ["send_email"] });

// CORRECT
const agent = createReactAgent({
  llm: model, tools: [sendEmail],
  checkpointer: new MemorySaver(),  // Required
  interruptBefore: ["send_email"]
});
```
</typescript>
</fix-missing-checkpointer>

<fix-no-thread-id>
<python>
Always provide thread_id when using HITL to track conversation state.
```python
# WRONG
agent.invoke(input)  # No config!

# CORRECT
agent.invoke(input, config={"configurable": {"thread_id": "user-123"}})
```
</python>
</fix-no-thread-id>

<fix-wrong-resume-syntax>
<python>
Use Command class to resume execution after an interrupt.
```python
# WRONG
agent.invoke({"resume": {"decisions": [...]}})

# CORRECT
from langgraph.types import Command
agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)
```
</python>
<typescript>
Use Command class to resume execution after an interrupt.
```typescript
// WRONG
await agent.invoke({ resume: { decisions: [...] } });

// CORRECT
import { Command } from "@langchain/langgraph";
await agent.invoke(new Command({ resume: { decisions: [{ type: "approve" }] } }), config);
```
</typescript>
</fix-wrong-resume-syntax>
