---
name: langchain-typescript-quickstart
description: "Scaffold a minimal local LangChain agent in TypeScript with createAgent, one stub tool, and a provider API key. Use when the user wants to quickly build or try a LangChain agent locally."
---

# LangChain TypeScript quickstart

Get a working local LangChain agent with minimal setup. Mirror the official quickstart: https://docs.langchain.com/oss/javascript/langchain/quickstart

## Rules

- Ask which **provider and model** to use (showcase model-agnosticism). Default to `anthropic:claude-sonnet-5` if they don't care.
- Only secret: the provider API key. No Tavily, LangSmith, or other keys.
- Create a **new** directory (e.g. `langchain-agent/`) and do all work there. Do not add files to the user's currently open project.
- Use a stub weather tool (no network). Prefer the user edits `.env` themselves — do not ask them to paste keys into chat.
- Requires Node 22+. Stop after a successful run. Briefly point to `langchain-fundamentals` / docs for next steps.

## Steps

1. **Ask** for provider/model. Emphasize LangChain works with any supported chat model — not locked to one vendor. Suggested prompt:

   > Which model should this agent use? Pass a `provider:model` string — e.g. `openai:gpt-5.5`, `anthropic:claude-sonnet-5`, `google-genai:gemini-2.5-flash-lite`, or another [supported provider](https://docs.langchain.com/oss/javascript/integrations/chat). Default if you're unsure: **`anthropic:claude-sonnet-5`**.

   Do not proceed until they answer or accept the default. Use their choice as `<MODEL>` below.

2. **Scaffold**
   ```bash
   mkdir langchain-agent && cd langchain-agent
   npm init -y
   npm install langchain @langchain/core zod dotenv
   ```
   Install the matching provider package for `<MODEL>` (e.g. `@langchain/openai`, `@langchain/anthropic`, `@langchain/google-genai`).
   Add `"type": "module"` to `package.json` if missing.

3. **Write** `main.ts`:

   ```typescript
   import "dotenv/config";
   import { createAgent, tool } from "langchain";
   import * as z from "zod";

   const getWeather = tool(
     ({ city }) => `It's always sunny in ${city}!`,
     {
       name: "get_weather",
       description: "Get weather for a given city",
       schema: z.object({ city: z.string() }),
     }
   );

   const agent = createAgent({
     model: "<MODEL>",
     tools: [getWeather],
     systemPrompt: "You are a helpful assistant",
   });

   const result = await agent.invoke({
     messages: [{ role: "user", content: "What's the weather in San Francisco?" }],
   });
   console.log(result.messages[result.messages.length - 1].content);
   ```

4. **Env**
   - Create `.env` with a single empty placeholder for the key their provider needs (e.g. `ANTHROPIC_API_KEY=`, `OPENAI_API_KEY=`, `GOOGLE_API_KEY=`).
   - Ensure `.env` is in `.gitignore`.
   - Ask them to fill it in, then wait.

5. **Run** with `npx tsx main.ts` (install `tsx` if needed). Show the output. If it fails: missing provider package, blank key, or bad model id — fix and retry.

6. **Done** — summarize files created. Suggest customizing tools / `systemPrompt`, then `langchain-fundamentals` for middleware, memory, and structured output.
