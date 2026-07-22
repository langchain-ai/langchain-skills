---
name: langchain-python-quickstart
description: "Scaffold a minimal local LangChain agent in Python with create_agent, one stub tool, and a provider API key. Use when the user wants to quickly build or try a LangChain agent locally."
---

# LangChain Python quickstart

Get a working local LangChain agent with minimal setup. Mirror the official quickstart: https://docs.langchain.com/oss/python/langchain/quickstart

## Rules

- Ask which **provider and model** to use (showcase model-agnosticism). Default to `anthropic:claude-sonnet-5` if they don't care.
- Only secret: the provider API key. No Tavily, LangSmith, or other keys.
- Create a **new** directory (e.g. `langchain-agent/`) and do all work there. Do not add files to the user's currently open project.
- Use a stub weather tool (no network). Prefer the user edits `.env` themselves — do not ask them to paste keys into chat.
- Stop after a successful run. Briefly point to `langchain-fundamentals` / docs for next steps.

## Steps

1. **Ask** for provider/model. Emphasize LangChain works with any supported chat model — not locked to one vendor. Suggested prompt:

   > Which model should this agent use? Pass a `provider:model` string — e.g. `openai:gpt-5.5`, `anthropic:claude-sonnet-5`, `google_genai:gemini-2.5-flash-lite`, or another [supported provider](https://docs.langchain.com/oss/python/integrations/chat). Default if you're unsure: **`anthropic:claude-sonnet-5`**.

   Do not proceed until they answer or accept the default. Use their choice as `<MODEL>` below.

2. **Scaffold**
   ```bash
   mkdir langchain-agent && cd langchain-agent
   uv init
   uv add langchain python-dotenv
   ```
   Install the matching provider package for `<MODEL>` (e.g. `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`).

3. **Write** `main.py`:

   ```python
   from dotenv import load_dotenv
   load_dotenv()

   from langchain.agents import create_agent

   def get_weather(city: str) -> str:
       """Get weather for a given city."""
       return f"It's always sunny in {city}!"

   agent = create_agent(
       model="<MODEL>",
       tools=[get_weather],
       system_prompt="You are a helpful assistant",
   )

   result = agent.invoke(
       {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
   )
   print(result["messages"][-1].content)
   ```

4. **Env**
   - Create `.env` with a single empty placeholder for the key their provider needs (e.g. `ANTHROPIC_API_KEY=`, `OPENAI_API_KEY=`, `GOOGLE_API_KEY=`).
   - Ensure `.env` is in `.gitignore`.
   - Ask them to fill it in, then wait.

5. **Run** `uv run python main.py`. Show the output. If it fails: missing provider package, blank key, or bad model id — fix and retry.

6. **Done** — summarize files created. Suggest customizing tools / `system_prompt`, then `langchain-fundamentals` for middleware, memory, and structured output.
