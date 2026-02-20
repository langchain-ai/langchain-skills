---
name: LangChain Models & Streaming
description: "INVOKE THIS SKILL when configuring chat models OR implementing streaming in LangChain/LangGraph. Covers init_chat_model, provider setup (OpenAI/Anthropic/Azure), streaming tokens, and multimodal inputs. CRITICAL: Fixes for messages mode tuple unpacking (token, metadata), sync vs async streaming, and multi-mode stream handling."
---

<overview>
Chat models are the core of LangChain applications. They take messages as input and return AI-generated messages as output with a unified interface across providers.

**Key Concepts:**
- **init_chat_model()**: Universal initialization for any provider
- **Provider classes**: Direct initialization (ChatOpenAI, ChatAnthropic, etc.)
- **Streaming**: Real-time token-by-token responses
- **Multimodal**: Images, PDFs, and other non-text data
</overview>

<provider-selection>

| Provider | Best For | Package |
|----------|----------|---------|
| **OpenAI** | General purpose, reasoning | `langchain-openai` |
| **Anthropic** | Safety, analysis, long context | `langchain-anthropic` |
| **Google** | Multimodal, speed | `langchain-google-genai` |

</provider-selection>

<stream-mode-selection>

| Mode | Use When | Returns |
|------|----------|---------|
| `"values"` | Need full state after each step | Complete state dict |
| `"updates"` | Need only what changed | State deltas |
| `"messages"` | Need LLM token stream | (token, metadata) tuples |

</stream-mode-selection>

---

## Model Initialization

<ex-basic-model-initialization>
<python>
Initialize a chat model using the universal init_chat_model() function with provider prefix or shorthand.
```python
from langchain.chat_models import init_chat_model

# Universal initialization
model = init_chat_model("openai:gpt-4")

# Or with provider shorthand
model = init_chat_model("gpt-4")  # Defaults to OpenAI

# API key from environment
import os
os.environ["OPENAI_API_KEY"] = "your-api-key"
```
</python>
<typescript>
Initialize chat models directly using provider-specific classes from LangChain packages.
```typescript
import { ChatOpenAI } from "@langchain/openai";
import { ChatAnthropic } from "@langchain/anthropic";

// OpenAI
const model = new ChatOpenAI({ model: "gpt-4" });

// Anthropic
const anthropic = new ChatAnthropic({ model: "claude-sonnet-4-5-20250929" });
```
</typescript>
</ex-basic-model-initialization>

<ex-provider-specific>
<python>
Configure provider-specific chat models with custom parameters like temperature and max tokens.
```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# OpenAI
openai = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    max_tokens=1000,
)

# Anthropic
anthropic = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0,
    max_tokens=2000,
)
```
</python>
<typescript>
Configure provider-specific chat models with custom parameters like temperature and max tokens.
```typescript
import { ChatOpenAI } from "@langchain/openai";
import { ChatAnthropic } from "@langchain/anthropic";

const openai = new ChatOpenAI({
  model: "gpt-4",
  temperature: 0.7,
  maxTokens: 1000,
});

const anthropic = new ChatAnthropic({
  model: "claude-sonnet-4-5-20250929",
  temperature: 0,
  maxTokens: 2000,
});
```
</typescript>
</ex-provider-specific>

<ex-azure-openai>
<python>
Configure Azure OpenAI with endpoint, API key, API version, and deployment name.
```python
from langchain_openai import AzureChatOpenAI
import os

azure = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    deployment_name="your-deployment-name",
)
```
</python>
</ex-azure-openai>

<ex-aws-bedrock>
<python>
Configure AWS Bedrock using credentials from environment or ~/.aws/credentials.
```python
from langchain_aws import ChatBedrock

# AWS credentials from environment or ~/.aws/credentials
bedrock = ChatBedrock(
    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
    region_name="us-east-1",
)
```
</python>
</ex-aws-bedrock>

---

## Invocation

<ex-simple-invocation>
<python>
Invoke a chat model with either a simple string or an array of message objects.
```python
model = init_chat_model("gpt-4")

# String input
response = model.invoke("What is LangChain?")
print(response.content)

# Message array
response = model.invoke([{"role": "user", "content": "Hello!"}])
```
</python>
<typescript>
Invoke a chat model with either a simple string or an array of message objects.
```typescript
const model = new ChatOpenAI({ model: "gpt-4" });

// String input
const response = await model.invoke("What is LangChain?");
console.log(response.content);

// Message array
const response2 = await model.invoke([{ role: "user", content: "Hello!" }]);
```
</typescript>
</ex-simple-invocation>

<ex-multi-turn-conversation>
<python>
Build multi-turn conversations by maintaining message history and appending responses.
```python
model = init_chat_model("gpt-4.1")

# Build conversation history
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the capital of France?"},
]

response1 = model.invoke(messages)
messages.append({"role": "assistant", "content": response1.content})

# Continue conversation
messages.append({"role": "user", "content": "What's its population?"})
response2 = model.invoke(messages)
# Model knows we're talking about Paris
```
</python>
</ex-multi-turn-conversation>

---

## Streaming

<ex-basic-token-streaming>
<python>
Stream tokens in real-time using the synchronous stream() method with a for loop.
```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4")

for chunk in model.stream("Explain quantum computing"):
    print(chunk.content, end="", flush=True)
```
</python>
<typescript>
Stream tokens in real-time using for await with the async stream() method.
```typescript
import { ChatOpenAI } from "@langchain/openai";

const model = new ChatOpenAI({ model: "gpt-4" });

for await (const chunk of await model.stream("Explain quantum computing")) {
  process.stdout.write(chunk.content);
}
```
</typescript>
</ex-basic-token-streaming>

<ex-agent-progress-streaming>
<python>
Stream agent steps using "updates" mode to see progress during execution.
```python
from langchain.agents import create_agent

agent = create_agent(model="gpt-4.1", tools=[search_tool])

# Stream agent steps with "updates" mode
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Search for AI news"}]},
    stream_mode=["updates"],
):
    print(f"Step: {chunk}")
```
</python>
</ex-agent-progress-streaming>

<ex-combined-streaming>
<python>
Stream both LLM tokens and agent progress simultaneously using multiple stream modes.
```python
# Stream both LLM tokens AND agent progress
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Research LangChain"}]},
    stream_mode=["updates", "messages"],
):
    if mode == "messages":
        # LLM token stream
        token, metadata = chunk
        if token.content:
            print(token.content, end="", flush=True)
    elif mode == "updates":
        # Agent step updates
        print(f"\nStep update: {chunk}")
```
</python>
</ex-combined-streaming>

<ex-async-streaming>
<python>
Use astream() for async streaming within an async function context.
```python
import asyncio

async def main():
    model = init_chat_model("gpt-4")
    async for chunk in model.astream("Explain AI"):
        print(chunk.content, end="", flush=True)

asyncio.run(main())
```
</python>
<typescript>
Stream responses asynchronously using for await with the stream() method.
```typescript
const model = new ChatOpenAI({ model: "gpt-4" });

for await (const chunk of await model.stream("Explain AI")) {
  process.stdout.write(chunk.content);
}
```
</typescript>
</ex-async-streaming>

---

## Multimodal

<ex-image-input>
<python>
Send images to multimodal models using URL or base64-encoded data in content blocks.
```python
from langchain_openai import ChatOpenAI
from langchain.schema.messages import HumanMessage
import base64

model = ChatOpenAI(model="gpt-4o")

# From URL
message = HumanMessage(content_blocks=[
    {"type": "text", "text": "What's in this image?"},
    {"type": "image", "url": "https://example.com/photo.jpg"},
])

# From base64
with open("./photo.jpg", "rb") as f:
    base64_image = base64.b64encode(f.read()).decode("utf-8")

message = HumanMessage(content_blocks=[
    {"type": "text", "text": "Describe this image"},
    {"type": "image", "base64": base64_image, "mime_type": "image/jpeg"},
])

response = model.invoke([message])
```
</python>
<typescript>
Send images to multimodal models using URL or base64-encoded data URL format.
```typescript
import { ChatOpenAI } from "@langchain/openai";
import { HumanMessage } from "@langchain/core/messages";
import * as fs from "fs";

const model = new ChatOpenAI({ model: "gpt-4o" });

// From URL
const message = new HumanMessage({
  content: [
    { type: "text", text: "What's in this image?" },
    { type: "image_url", image_url: { url: "https://example.com/photo.jpg" } },
  ],
});

// From base64
const imageData = fs.readFileSync("./photo.jpg").toString("base64");
const message2 = new HumanMessage({
  content: [
    { type: "text", text: "Describe this image" },
    { type: "image_url", image_url: { url: `data:image/jpeg;base64,${imageData}` } },
  ],
});

const response = await model.invoke([message]);
```
</typescript>
</ex-image-input>

<ex-pdf-document-analysis>
<python>
Analyze PDF documents by encoding them as base64 and using file content blocks.
```python
from langchain_anthropic import ChatAnthropic
import base64

model = ChatAnthropic(model="claude-sonnet-4-5-20250929")

with open("./document.pdf", "rb") as pdf_file:
    base64_pdf = base64.b64encode(pdf_file.read()).decode("utf-8")

message = HumanMessage(content_blocks=[
    {"type": "text", "text": "Summarize this PDF document"},
    {"type": "file", "base64": base64_pdf, "mime_type": "application/pdf"},
])

response = model.invoke([message])
```
</python>
</ex-pdf-document-analysis>

<boundaries>
### What You CAN Configure

- Model Selection: Any supported model
- Temperature: Control randomness (0-1)
- Max Tokens: Limit response length
- Stream modes

### What You CANNOT Configure

- Model Training Data
- Token Costs: Set by provider
- Rate Limits: Set by provider
</boundaries>

<fix-response-content-access>
<python>
Access .content property to get the actual response text.
```python
# WRONG
print(response)  # AIMessage object, not string

# CORRECT
print(response.content)  # "Hello! How can I help you?"
```
</python>
<typescript>
Access .content property to get the actual response text.
```typescript
// WRONG
console.log(response);  // AIMessage object

// CORRECT
console.log(response.content);
```
</typescript>
</fix-response-content-access>

<fix-streaming-requires-iteration>
<python>
Iterate over the stream generator with a for loop to receive chunks.
```python
# WRONG: Not iterating
stream = model.stream("Hello")  # Generator object

# CORRECT
for chunk in model.stream("Hello"):
    print(chunk.content, end="", flush=True)
```
</python>
<typescript>
Iterate over the async stream with for await to receive chunks.
```typescript
// WRONG: Not iterating
const stream = model.stream("Hello");  // AsyncGenerator

// CORRECT
for await (const chunk of await model.stream("Hello")) {
  process.stdout.write(chunk.content);
}
```
</typescript>
</fix-streaming-requires-iteration>

<fix-sync-vs-async>
<python>
Use astream() in async contexts to avoid blocking the event loop.
```python
# WRONG: Blocks async loop!
async def process():
    for chunk in model.stream("Hello"):
        print(chunk.content)

# CORRECT
async def process():
    async for chunk in model.astream("Hello"):
        print(chunk.content, flush=True)
```
</python>
<typescript>
TypeScript is async by default - always use await.
```typescript
const response = await model.invoke("Hello");
for await (const chunk of await model.stream("Hello")) {
  process.stdout.write(chunk.content);
}
```
</typescript>
</fix-sync-vs-async>

<fix-api-key-not-found>
<python>
Set API key via environment variable or pass directly.
```python
# WRONG
model.invoke("Hello")  # Error: API key not found

# CORRECT: Environment variable
os.environ["OPENAI_API_KEY"] = "sk-..."
model = init_chat_model("openai:gpt-4.1")

# Or pass directly
model = ChatOpenAI(model="gpt-4.1", api_key="sk-...")
```
</python>
</fix-api-key-not-found>

<fix-import-errors>
<python>
Use provider-specific packages instead of deprecated imports.
```python
# WRONG: Deprecated
from langchain.chat_models import ChatOpenAI

# CORRECT
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
```
</python>
</fix-import-errors>

<fix-azure-configuration>
<python>
Azure OpenAI requires endpoint, API key, deployment name, and API version.
```python
# WRONG: Missing required fields
model = AzureChatOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"))

# CORRECT
model = AzureChatOpenAI(
    azure_endpoint="https://my-instance.openai.azure.com/",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment="gpt-4", api_version="2024-02-01"
)
```
</python>
</fix-azure-configuration>

<fix-tuple-unpacking-for-messages-mode>
<python>
Messages mode returns (token, metadata) tuples that must be unpacked.
```python
# WRONG
for mode, chunk in agent.stream(input, stream_mode=["messages"]):
    print(chunk.content)  # AttributeError!

# CORRECT: Unpack the tuple
for mode, chunk in agent.stream(input, stream_mode=["messages"]):
    token, metadata = chunk
    print(token.content)
```
</python>
</fix-tuple-unpacking-for-messages-mode>

<fix-model-doesnt-support-multimodal>
<python>
Use vision-capable models (gpt-4.1, gpt-4o) for image inputs.
```python
# WRONG: Text-only model
model = ChatOpenAI(model="gpt-3.5-turbo")
model.invoke([image_message])  # Error!

# CORRECT
model = ChatOpenAI(model="gpt-4.1")
```
</python>
</fix-model-doesnt-support-multimodal>

<fix-missing-mime-type-for-base64>
<python>
Always include MIME type with base64-encoded images.
```python
# WRONG
{"type": "image", "base64": base64_data}

# CORRECT
{"type": "image", "base64": base64_data, "mime_type": "image/jpeg"}
```
</python>
</fix-missing-mime-type-for-base64>
