---
name: langgraph-typescript-quickstart
description: "Scaffold a minimal local LangGraph agent in TypeScript with StateGraph (tool-calling loop), one stub tool, and a provider API key. Use when the user wants to quickly build or try a LangGraph agent locally."
---

# LangGraph TypeScript quickstart

Get a working local LangGraph agent with minimal setup. Inspired by the Graph API quickstart: https://docs.langchain.com/oss/javascript/langgraph/quickstart  
(Uses a stub weather tool instead of the docs calculator so setup stays provider-key-only.)

## Rules

- Ask which **provider and model** to use (showcase model-agnosticism). Default to `anthropic:claude-sonnet-5` if they don't care.
- Only secret: the provider API key. No Tavily, LangSmith, or other keys.
- Create a **new** directory (e.g. `langgraph-agent/`) and do all work there. Do not add files to the user's currently open project.
- Use a stub weather tool (no network). Prefer the user edits `.env` themselves — do not ask them to paste keys into chat.
- Use the Graph API (`StateGraph`), not deprecated prebuilt ReAct helpers. Skip graph visualization.
- Stop after a successful run. Briefly point to `langgraph-fundamentals` / docs for next steps.

## Steps

1. **Ask** for provider/model. Emphasize LangGraph works with any LangChain chat model — not locked to one vendor. Suggested prompt:

   > Which model should this agent use? Pass a `provider:model` string — e.g. `openai:gpt-5.5`, `anthropic:claude-sonnet-5`, `google-genai:gemini-2.5-flash-lite`, or another [supported provider](https://docs.langchain.com/oss/javascript/integrations/chat). Default if you're unsure: **`anthropic:claude-sonnet-5`**.

   Do not proceed until they answer or accept the default. Use their choice as `<MODEL>` below.

2. **Scaffold**
   ```bash
   mkdir langgraph-agent && cd langgraph-agent
   npm init -y
   npm install @langchain/langgraph @langchain/core langchain zod dotenv
   ```
   Install the matching provider package for `<MODEL>` (e.g. `@langchain/openai`, `@langchain/anthropic`, `@langchain/google-genai`).
   Add `"type": "module"` to `package.json` if missing.

3. **Write** `main.ts` — minimal ReAct graph with one stub tool. Use `initChatModel` from `langchain` with `<MODEL>`:

   ```typescript
   import "dotenv/config";
   import { initChatModel } from "langchain";
   import { tool } from "@langchain/core/tools";
   import { HumanMessage, SystemMessage, ToolMessage } from "@langchain/core/messages";
   import { StateGraph, START, END, MessagesAnnotation } from "@langchain/langgraph";
   import { z } from "zod";

   const model = await initChatModel("<MODEL>");
   // If using Claude Sonnet 5+, omit temperature/top_p/top_k (unsupported).
   // For older models you may pass { temperature: 0 }.

   const getWeather = tool(
     ({ city }) => `It's always sunny in ${city}!`,
     {
       name: "get_weather",
       description: "Get weather for a given city",
       schema: z.object({ city: z.string() }),
     }
   );

   const toolsByName = { get_weather: getWeather };
   const modelWithTools = model.bindTools([getWeather]);

   async function llmCall(state: typeof MessagesAnnotation.State) {
     const response = await modelWithTools.invoke([
       new SystemMessage("You are a helpful assistant."),
       ...state.messages,
     ]);
     return { messages: [response] };
   }

   async function toolNode(state: typeof MessagesAnnotation.State) {
     const last = state.messages[state.messages.length - 1];
     const results: ToolMessage[] = [];
     for (const call of last.tool_calls ?? []) {
       const observation = await toolsByName[call.name as keyof typeof toolsByName].invoke(
         call.args
       );
       results.push(
         new ToolMessage({ content: String(observation), tool_call_id: call.id! })
       );
     }
     return { messages: results };
   }

   function shouldContinue(state: typeof MessagesAnnotation.State) {
     const last = state.messages[state.messages.length - 1];
     return last.tool_calls?.length ? "tool_node" : END;
   }

   const agent = new StateGraph(MessagesAnnotation)
     .addNode("llm_call", llmCall)
     .addNode("tool_node", toolNode)
     .addEdge(START, "llm_call")
     .addConditionalEdges("llm_call", shouldContinue, ["tool_node", END])
     .addEdge("tool_node", "llm_call")
     .compile();

   const result = await agent.invoke({
     messages: [new HumanMessage("What's the weather in San Francisco?")],
   });
   console.log(result.messages[result.messages.length - 1].content);
   ```

   If `MessagesAnnotation` / `initChatModel` imports differ in the installed version, follow the current JS LangGraph quickstart — keep the same graph shape.

4. **Env**
   - Create `.env` with a single empty placeholder for the key their provider needs.
   - Ensure `.env` is in `.gitignore`.
   - Ask them to fill it in, then wait.

5. **Run** with `npx tsx main.ts` (install `tsx` if needed). Show the output. If it fails: missing provider package, blank key, or bad model id — fix and retry.

6. **Done** — summarize files created. Suggest `langgraph-fundamentals`, `langgraph-persistence`, or `langgraph-human-in-the-loop` next. For a higher-level agent API, use LangChain `createAgent` instead.
