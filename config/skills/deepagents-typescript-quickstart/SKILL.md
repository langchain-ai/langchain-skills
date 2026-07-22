---
name: deepagents-typescript-quickstart
description: "Scaffold a minimal local Deep Agent in TypeScript with createDeepAgent and provider-native web search (no Tavily). Use when the user wants to quickly build or try a Deep Agent locally."
---

# Deep Agents TypeScript quickstart

Get a working local Deep Agent that can research via **provider-side web search** (only a provider API key — no Tavily). Inspired by https://docs.langchain.com/oss/javascript/deepagents/overview and the research quickstart shape, without a second search vendor.

## Rules

- Ask which **provider and model** to use (showcase model-agnosticism). Default to `anthropic:claude-sonnet-5` if they don't care.
- Prefer Anthropic, OpenAI, or Google — each has a built-in web search tool. Only secret: that provider's API key. No Tavily, LangSmith, or other keys.
- Create a **new** directory (e.g. `deep-agent/`) and do all work there. Do not add files to the user's currently open project.
- Prefer the user edits `.env` themselves — do not ask them to paste keys into chat.
- Requires Node 22+. Stop after a successful run. Briefly point to `deep-agents-core` / docs for next steps.

## Steps

1. **Ask** for provider/model. Emphasize Deep Agents work with any LangChain chat model. Suggested prompt:

   > Which model should this agent use? Pass a `provider:model` string — e.g. `openai:gpt-5.5`, `anthropic:claude-sonnet-5`, `google-genai:gemini-3.5-flash`. Default if you're unsure: **`anthropic:claude-sonnet-5`**.  
   > We'll enable that provider's built-in web search (no separate search API key).

   Do not proceed until they answer or accept the default. Use their choice as `<MODEL>` below.

2. **Scaffold**
   ```bash
   mkdir deep-agent && cd deep-agent
   npm init -y
   npm install deepagents langchain @langchain/core zod dotenv
   ```
   Install the matching provider package for `<MODEL>` (e.g. `@langchain/openai`, `@langchain/anthropic`, `@langchain/google-genai`).
   Add `"type": "module"` to `package.json` if missing.

3. **Pick the provider web-search tool** for their model (look up current docs / package exports if names differ):

   | Provider | How to get the tool |
   |----------|---------------------|
   | Anthropic | From `@langchain/anthropic`: `tools.webSearch_20250305()` (or newer `webSearch_*` export if present) — or pass `{ type: "web_search_20250305", name: "web_search" }` |
   | OpenAI | `{ type: "web_search" }` |
   | Google | `{ google_search: {} }` (confirm against current `@langchain/google-genai` docs) |

   If they chose another provider, check that provider's LangChain chat docs for a built-in search tool; if none exists, tell them and fall back to Anthropic/OpenAI/Google.

4. **Write** `main.ts` (swap `<MODEL>` and search tool). Prefer `await createDeepAgent` if the installed API is async:

   ```typescript
   import "dotenv/config";
   import { createDeepAgent } from "deepagents";

   const researchInstructions = `You are an expert researcher. Conduct brief research and write a clear, polished answer.
   Use web search to gather current information when needed.`;

   const agent = await createDeepAgent({
     model: "<MODEL>",
     tools: [<PROVIDER_SEARCH_TOOL>],
     systemPrompt: researchInstructions,
   });

   const result = await agent.invoke({
     messages: [{ role: "user", content: "What is LangGraph?" }],
   });
   console.log(result.messages[result.messages.length - 1].content);
   ```

   Example for Anthropic default (adjust import to match installed `@langchain/anthropic`):

   ```typescript
   import { tools as anthropicTools } from "@langchain/anthropic";
   // tools: [anthropicTools.webSearch_20250305()]
   ```

5. **Env**
   - Create `.env` with a single empty placeholder for the key their provider needs.
   - Ensure `.env` is in `.gitignore`.
   - Ask them to fill it in, then wait.

6. **Run** with `npx tsx main.ts` (install `tsx` if needed). Show the output. If it fails: missing provider package, blank key, bad model id, or unsupported search tool — fix and retry.

7. **Done** — summarize files created. Suggest `deep-agents-core`, `deep-agents-memory`, `deep-agents-orchestration`, or Managed Deep Agents for deploy. Do not set up LangSmith tracing unless they ask.
