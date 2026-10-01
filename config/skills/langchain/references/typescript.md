# LangChain TypeScript

Use this reference for TypeScript applications. Inspect the installed versions
and current imports before editing an existing project. The current docs start
at <https://docs.langchain.com/oss/javascript/langchain/overview> and the
quickstart is <https://docs.langchain.com/oss/javascript/langchain/quickstart>.

## Minimal agent

```typescript
import { createAgent } from "langchain";
import { tool } from "@langchain/core/tools";
import * as z from "zod";

const model = process.env.MODEL;
if (!model) throw new Error("MODEL is required");

const getWeather = tool(
  async ({ location }) => `The weather in ${location} is sunny.`,
  {
    name: "get_weather",
    description: "Return the current weather for a city.",
    schema: z.object({ location: z.string().describe("City name") }),
  },
);

const agent = createAgent({
  model,
  tools: [getWeather],
  systemPrompt: "Answer accurately and use tools when needed.",
});

const result = await agent.invoke({
  messages: [{ role: "user", content: "Weather in Boston?" }],
});
console.log(result.messages.at(-1)?.content);
```

For a new application, create the project where the user requested it, preserve
the chosen package manager, use the provider and model they selected, and keep
provider credentials in a gitignored environment file. Confirm the supported
Node.js version in current LangChain documentation.

## Structured output

```typescript
import { createAgent } from "langchain";
import * as z from "zod";

const model = process.env.MODEL;
if (!model) throw new Error("MODEL is required");

const ContactInfo = z.object({
  name: z.string(),
  email: z.string().email(),
  phone: z.string().describe("Phone number including area code"),
});

const agent = createAgent({
  model,
  tools: [],
  responseFormat: ContactInfo,
});

const result = await agent.invoke({
  messages: [
    { role: "user", content: "Extract: Ana, ana@example.com, 555-0100" },
  ],
});
const contact = result.structuredResponse;
```

Verify the installed release's `responseFormat` API. For a single model call
with no agent loop, use the selected chat model's `withStructuredOutput` method.

## Practical boundaries

- Define a Zod schema and a precise description for every tool.
- Inspect the returned agent state and its `messages`; do not treat it as a
  message object.
- Set an appropriate `recursionLimit` when a tool loop needs a hard bound.
- Route checkpointers, middleware, approvals, and composition to the shared
  capability references linked from the main skill.
