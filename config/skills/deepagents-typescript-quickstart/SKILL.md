---
name: deepagents-typescript-quickstart
description: "Scaffold a minimal local Deep Agent in TypeScript by following the official quickstart, using provider-native web search instead of Tavily. Use when the user wants to quickly build or try a Deep Agent locally."
---

# Deep Agents TypeScript quickstart

Follow the live docs — do not invent an alternate API from memory:

**https://docs.langchain.com/oss/javascript/deepagents/quickstart**

Fetch that page (Docs MCP or HTTP) and implement the research-agent shape it shows (`createDeepAgent`, research system prompt, invoke with a research question like “What is LangGraph?”). Requires Node 22+.

## Local setup constraints

Apply these on top of the quickstart (they keep setup minimal and model-agnostic):

1. **Ask** which provider/model to use. Showcase that Deep Agents are model-agnostic. Suggested prompt:

   > Which model should this agent use? Pass a `provider:model` string — e.g. `openai:gpt-5.5`, `anthropic:claude-sonnet-5`, `google-genai:gemini-3.5-flash`. Default if you're unsure: **`anthropic:claude-sonnet-5`**.  
   > We'll use that provider's built-in web search (no separate search API key).

2. Create a **new** directory (e.g. `deep-agent/`) and do all work there — do not pollute the open project.

3. **Do not use Tavily** (or `@langchain/tavily`). Replace the quickstart's search tool with the chosen provider's built-in web search. Look up the current export/tool shape on that provider's LangChain docs (examples as of writing — re-check if needed):

   | Provider | Built-in search tool |
   |----------|----------------------|
   | Anthropic | `@langchain/anthropic` `tools.webSearch_*()` (or equivalent dict) |
   | OpenAI | `{ type: "web_search" }` |
   | Google | `{ google_search: {} }` |

   Prefer Anthropic / OpenAI / Google so provider search is available. Only secret: that provider's API key in `.env` (gitignored). Skip LangSmith tracing unless they ask.

4. Install packages from the quickstart **minus** Tavily; add the provider package for their model.

5. Run the research example, show output, then stop. Point to `deep-agents-core` / customization / Managed Deep Agents for next steps.
