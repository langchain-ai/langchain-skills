# Python

Use this reference for any Python task that creates or modifies an open-source
Deep Agent. It provides a local implementation baseline; use current official
documentation to verify APIs when the installed version differs or a requested
capability is not covered here.

## Minimal agent

```python
import os

from deepagents import create_deep_agent
from langchain.tools import tool


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Weather lookup result for {city}"


agent = create_deep_agent(
    model=os.environ["MODEL"],
    tools=[get_weather],
    system_prompt="Help the user answer weather questions.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is the weather in Boston?"}]}
)
print(result["messages"][-1].content)
```

Set `MODEL` to the user's provider-qualified model identifier. Replace the tool
implementation with real application behavior. Use the project's existing
model object when it already constructs one with provider-specific settings.

## Modify an existing application

Before editing, inspect:

- the installed `deepagents`, `langchain`, and `langgraph` versions;
- how the project constructs models and tools;
- how it invokes agents and consumes their results;
- whether the Deep Agent is standalone, called from a graph node, or exposed
  through another application boundary;
- existing checkpointer, store, backend, middleware, and run configuration.

Change only the configuration required by the requested behavior. Preserve the
existing provider, model construction, project layout, and invocation contract
unless the user asks to change them.

## Add a Deep Agent to a LangGraph node

Keep the graph-to-agent boundary explicit. Pass only the messages or task the
agent needs and return a partial graph-state update.

```python
deep_agent = create_deep_agent(
    model=model,
    tools=tools,
    system_prompt=agent_instructions,
)


def run_deep_agent(state: AppState) -> dict:
    result = deep_agent.invoke({"messages": state["messages"]})
    return {"messages": [result["messages"][-1]]}
```

Adapt the state key and reducer behavior to the graph's actual state schema.
Do not pass the entire state object when the agent needs only a focused input.

## Minimal new-project workflow

When the user wants a new minimal project:

1. Use the directory, package manager, provider, and model they supplied.
2. If those choices are absent, ask only for decisions that block a working
   implementation.
3. Add the `deepagents` package and the selected provider integration.
4. Store provider credentials outside source control and reference them by
   environment-variable name.
5. Implement the user's requested agent. Use the official research-agent
   quickstart only when the user asks for a tutorial or supplies no application
   requirements.
6. Run one meaningful invocation and inspect the returned messages and tool
   behavior.

Official quickstart:
`https://docs.langchain.com/oss/python/deepagents/quickstart`

Do not add tracing, persistence, approval flows, custom subagents, or skills
unless requested or already part of the project.
