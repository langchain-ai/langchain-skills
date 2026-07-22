---
name: langgraph-python-quickstart
description: "Scaffold a minimal local LangGraph agent in Python with StateGraph (tool-calling loop), one stub tool, and a provider API key. Use when the user wants to quickly build or try a LangGraph agent locally."
---

# LangGraph Python quickstart

Get a working local LangGraph agent with minimal setup. Inspired by the Graph API quickstart: https://docs.langchain.com/oss/python/langgraph/quickstart  
(Uses a stub weather tool instead of the docs calculator so setup stays provider-key-only.)

## Rules

- Ask which **provider and model** to use (showcase model-agnosticism). Default to `anthropic:claude-sonnet-5` if they don't care.
- Only secret: the provider API key. No Tavily, LangSmith, or other keys.
- Create a **new** directory (e.g. `langgraph-agent/`) and do all work there. Do not add files to the user's currently open project.
- Use a stub weather tool (no network). Prefer the user edits `.env` themselves — do not ask them to paste keys into chat.
- Use the Graph API (`StateGraph`), not deprecated `create_react_agent`. Skip graph visualization / IPython display.
- Stop after a successful run. Briefly point to `langgraph-fundamentals` / docs for next steps.

## Steps

1. **Ask** for provider/model. Emphasize LangGraph works with any LangChain chat model — not locked to one vendor. Suggested prompt:

   > Which model should this agent use? Pass a `provider:model` string — e.g. `openai:gpt-5.5`, `anthropic:claude-sonnet-5`, `google_genai:gemini-2.5-flash-lite`, or another [supported provider](https://docs.langchain.com/oss/python/integrations/chat). Default if you're unsure: **`anthropic:claude-sonnet-5`**.

   Do not proceed until they answer or accept the default. Use their choice as `<MODEL>` below.

2. **Scaffold**
   ```bash
   mkdir langgraph-agent && cd langgraph-agent
   uv init
   uv add langgraph langchain python-dotenv
   ```
   Install the matching provider package for `<MODEL>` (e.g. `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`).

3. **Write** `main.py` — minimal ReAct graph with one stub tool:

   ```python
   from dotenv import load_dotenv
   load_dotenv()

   import operator
   from typing import Literal

   from typing_extensions import Annotated, TypedDict

   from langchain.chat_models import init_chat_model
   from langchain.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
   from langchain.tools import tool
   from langgraph.graph import END, START, StateGraph

   model = init_chat_model("<MODEL>")
   # If using Claude Sonnet 5+, omit temperature/top_p/top_k (unsupported).
   # For older models you may pass temperature=0.

   @tool
   def get_weather(city: str) -> str:
       """Get weather for a given city."""
       return f"It's always sunny in {city}!"

   tools = [get_weather]
   tools_by_name = {t.name: t for t in tools}
   model_with_tools = model.bind_tools(tools)

   class MessagesState(TypedDict):
       messages: Annotated[list[AnyMessage], operator.add]

   def llm_call(state: MessagesState):
       return {
           "messages": [
               model_with_tools.invoke(
                   [SystemMessage(content="You are a helpful assistant.")]
                   + state["messages"]
               )
           ]
       }

   def tool_node(state: MessagesState):
       result = []
       for tool_call in state["messages"][-1].tool_calls:
           observation = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
           result.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
       return {"messages": result}

   def should_continue(state: MessagesState) -> Literal["tool_node", END]:
       return "tool_node" if state["messages"][-1].tool_calls else END

   agent = (
       StateGraph(MessagesState)
       .add_node("llm_call", llm_call)
       .add_node("tool_node", tool_node)
       .add_edge(START, "llm_call")
       .add_conditional_edges("llm_call", should_continue, ["tool_node", END])
       .add_edge("tool_node", "llm_call")
       .compile()
   )

   result = agent.invoke(
       {"messages": [HumanMessage(content="What's the weather in San Francisco?")]}
   )
   print(result["messages"][-1].content)
   ```

4. **Env**
   - Create `.env` with a single empty placeholder for the key their provider needs.
   - Ensure `.env` is in `.gitignore`.
   - Ask them to fill it in, then wait.

5. **Run** `uv run python main.py`. Show the output. If it fails: missing provider package, blank key, or bad model id — fix and retry.

6. **Done** — summarize files created. Suggest `langgraph-fundamentals` (state, edges, `Command`), `langgraph-persistence`, or `langgraph-human-in-the-loop` next. For a higher-level agent API, use LangChain `create_agent` instead.
