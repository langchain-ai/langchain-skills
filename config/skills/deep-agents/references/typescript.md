# TypeScript

Use this reference for any TypeScript task that creates or modifies an
open-source Deep Agent. It provides a local implementation baseline; use
current official documentation to verify APIs when the installed version
differs or a requested capability is not covered here.

## Minimal agent

```typescript
import { createDeepAgent } from "deepagents";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const model = process.env.MODEL;
if (!model) throw new Error("MODEL is required");

const getWeather = tool(
  async ({ city }) => `Weather lookup result for ${city}`,
  {
    name: "get_weather",
    description: "Get the current weather for a city.",
    schema: z.object({ city: z.string() }),
  },
);

const agent = await createDeepAgent({
  model,
  tools: [getWeather],
  systemPrompt: "Help the user answer weather questions.",
});

const result = await agent.invoke({
  messages: [{ role: "user", content: "What is the weather in Boston?" }],
});
console.log(result.messages.at(-1)?.content);
```

Set `MODEL` to the user's provider-qualified model identifier. Replace the tool
implementation with real application behavior. Use the project's existing
model object when it already constructs one with provider-specific settings.

## Modify an existing application

Before editing, inspect:

- the installed `deepagents`, `langchain`, and `@langchain/langgraph` versions;
- the package manager, module format, and TypeScript configuration;
- how the project constructs models, tools, and schemas;
- how it invokes agents and consumes their results;
- whether the Deep Agent is standalone, called from a graph node, or exposed
  through another application boundary;
- existing checkpointer, store, backend, middleware, and run configuration.

Change only the configuration required by the requested behavior. Preserve the
existing provider, model construction, schema library, project layout, and
invocation contract unless the user asks to change them.

## Add a Deep Agent to a LangGraph node

Keep the graph-to-agent boundary explicit. Pass only the messages or task the
agent needs and return a partial graph-state update.

```typescript
const deepAgent = await createDeepAgent({
  model,
  tools,
  systemPrompt: agentInstructions,
});

const runDeepAgent = async (state: AppState): Promise<Partial<AppState>> => {
  const result = await deepAgent.invoke({ messages: state.messages });
  return { messages: [result.messages.at(-1)!] };
};
```

Adapt the state key and reducer behavior to the graph's actual state schema.
Do not pass the entire state object when the agent needs only a focused input.

## Minimal new-project workflow

When the user wants a new minimal project:

1. Inspect or establish the Node version, package manager, module format,
   schema library, provider, and model.
2. Ask only for decisions that block a working implementation.
3. Add `deepagents` and the selected provider integration using the project's
   package manager.
4. Store provider credentials outside source control and reference them by
   environment-variable name.
5. Implement the user's requested agent. Use the official research-agent
   quickstart only when the user asks for a tutorial or supplies no application
   requirements.
6. Run one meaningful invocation and inspect the returned messages and tool
   behavior.

Official quickstart:
`https://docs.langchain.com/oss/javascript/deepagents/quickstart`

Do not add tracing, persistence, approval flows, custom subagents, or skills
unless requested or already part of the project.
