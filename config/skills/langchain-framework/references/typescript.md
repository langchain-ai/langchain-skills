# LangChain TypeScript

Use this reference for TypeScript applications. Inspect the installed versions
and current imports before editing an existing project. The current docs start
at <https://docs.langchain.com/oss/javascript/langchain/overview> and the
quickstart is <https://docs.langchain.com/oss/javascript/langchain/quickstart>.

## Packages and versions

Inspect `package.json` and the lockfile before changing packages. Preserve the
project's package manager, workspace structure, and compatible versions. Add
only the framework, provider, schema, or integration packages required by the
requested implementation. Verify current package names, Node.js support, peer
dependencies, and compatibility in official documentation rather than copying
a static version matrix. After a change, verify imports and run the application
path that uses the dependency.

## Minimal agent

```typescript
import { createAgent, tool } from "langchain";
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
the chosen package manager, use the provider and model they selected, and use
the project's environment or secret-management system. Reference secrets by
name and never hardcode, log, or serialize their values. Confirm the supported
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

Passing a supported schema lets LangChain select provider-native structured
output when the model supports it and tool-based structured output otherwise.
Use `providerStrategy` or `toolStrategy` from `langchain` when the application
must force one strategy. Current releases accept Zod, Standard Schema, and JSON
Schema formats; verify the installed release when using a schema library other
than the project's existing choice.

For a single model call with no agent loop, use the selected chat model's
`withStructuredOutput` method.

## Runtime context

Use runtime context for request-scoped dependencies and identity. Define a
`contextSchema`, pass `context` in invocation options, and access it through the
tool's injected runtime parameter.

```typescript
import { createAgent, tool, type ToolRuntime } from "langchain";
import * as z from "zod";

const contextSchema = z.object({ userId: z.string() });

const getPreferences = tool(
  async (_, runtime: ToolRuntime<any, typeof contextSchema>) =>
    loadPreferences(runtime.context?.userId),
  {
    name: "get_preferences",
    description: "Read preferences for the authenticated user.",
    schema: z.object({}),
  },
);

const agent = createAgent({ model, tools: [getPreferences], contextSchema });
const result = await agent.invoke(
  { messages: [{ role: "user", content: "How should you respond?" }] },
  { context: { userId: authenticatedUserId } },
);
```

Authenticate and authorize `authenticatedUserId` before invocation. Context is
dependency injection, not proof that a caller owns the referenced resource.

## Tool results and streaming

Ordinary tool return values become model-visible tool results. Return a
LangGraph `Command` when a tool must update agent state, and include the tool
message required by the current API. Keep updates serializable and validate
external effects inside the tool implementation.

For new streaming integrations, prefer `streamEvents`, which provides typed
projections for messages, tool calls, values, output, and subgraphs. Existing
applications may use `stream` with `updates`, `messages`, or `custom` modes;
preserve the caller's expected event contract.

## Practical boundaries

- Define a Zod schema and a precise description for every tool.
- Inspect the returned agent state and its `messages`; do not treat it as a
  message object.
- Use standardized content blocks when a consumer needs normalized text,
  reasoning, tool, or multimodal output; preserve raw `content` when its
  provider-specific shape is intentional.
- Set an appropriate `recursionLimit` when a tool loop needs a hard bound.
- Route checkpointers, middleware, approvals, and composition to the shared
  capability references linked from the main skill.
