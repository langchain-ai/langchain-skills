---
name: langchain-python-quickstart
description: "Scaffold a minimal local LangChain agent in Python by following the official quickstart. Use when the user wants to quickly build or try a LangChain agent locally."
---

# LangChain Python quickstart

Follow the live docs — do not invent an alternate API from memory:

**https://docs.langchain.com/oss/python/langchain/quickstart**

Fetch that page (Docs MCP or HTTP) and implement what it shows (weather agent + `create_agent`).

## Local setup constraints

Apply these on top of the quickstart (they keep setup minimal and model-agnostic):

1. **Ask** which provider/model to use. Showcase that LangChain is model-agnostic. Suggested prompt:

   > Which model should this agent use? Pass a `provider:model` string — e.g. `openai:gpt-5.5`, `anthropic:claude-sonnet-5`, `google_genai:gemini-2.5-flash-lite`. Default if you're unsure: **`anthropic:claude-sonnet-5`**.

   Swap the quickstart's model string for their choice (or the default).

2. Create a **new** directory (e.g. `langchain-agent/`) and do all work there — do not pollute the open project.

3. Only secret: the provider API key in `.env` (gitignored). No LangSmith / Tavily unless they ask. Prefer they edit `.env` themselves — don't paste keys into chat.

4. Install the provider package needed for their model if the quickstart's base install isn't enough.

5. Run the example, show output, then stop. Point to `langchain-fundamentals` for next steps.
