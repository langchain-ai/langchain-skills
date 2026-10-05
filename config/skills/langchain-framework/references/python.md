# LangChain Python

Use this reference for Python applications. Inspect the installed versions and
current imports before editing an existing project. The current documentation
starts at <https://docs.langchain.com/oss/python/langchain/overview> and the
quickstart is <https://docs.langchain.com/oss/python/langchain/quickstart>.

## Packages and versions

Inspect the project's dependency manifest and lockfile before changing
packages. Preserve its package manager and compatible versions. Add only the
LangChain framework and provider or integration packages required by the
requested implementation. Verify current package names, Python support, and
compatibility in official installation and integration documentation rather
than copying a static version matrix. After a change, verify imports and run the
application path that uses the dependency.

## Minimal agent

```python
import os

from langchain.agents import create_agent
from langchain.tools import tool


@tool
def get_weather(location: str) -> str:
    """Return the current weather for a city."""
    return f"The weather in {location} is sunny."


agent = create_agent(
    model=os.environ["MODEL"],
    tools=[get_weather],
    system_prompt="Answer accurately and use tools when needed.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Weather in Boston?"}]}
)
print(result["messages"][-1].content_blocks)
```

For a new application, create the project where the user requested it, use the
provider and model they selected, use the project's environment or
secret-management system, and install only the required LangChain and provider
packages. Reference secrets by name and never hardcode, log, or serialize their
values. Do not force a new directory or demo when modifying an existing
application.

## Structured output

```python
import os

from pydantic import BaseModel, Field
from langchain.agents import create_agent


class ContactInfo(BaseModel):
    name: str
    email: str
    phone: str = Field(description="Phone number including area code")


agent = create_agent(
    model=os.environ["MODEL"],
    tools=[],
    response_format=ContactInfo,
)
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Extract: Ana, ana@example.com, 555-0100"}]}
)
contact = result["structured_response"]
```

Passing a schema type lets LangChain select provider-native structured output
when the chosen model supports it and tool-based structured output otherwise.
Use `ProviderStrategy` or `ToolStrategy` from
`langchain.agents.structured_output` when the application must force one
strategy. JSON Schema dictionaries require an explicit strategy wrapper.

For a single model call with no agent loop, use the selected chat model's
`with_structured_output` support instead of creating an agent.

## Runtime context

Use runtime context for request-scoped dependencies and identity. Define
`context_schema`, pass `context` for each invocation, and access it through a
`ToolRuntime` parameter. The runtime parameter is injected and is not exposed
in the model-visible tool schema.

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool


@dataclass
class Context:
    user_id: str


@tool
def get_preferences(runtime: ToolRuntime[Context]) -> str:
    """Read preferences for the authenticated user."""
    return load_preferences(runtime.context.user_id)


agent = create_agent(
    model=model,
    tools=[get_preferences],
    context_schema=Context,
)
result = agent.invoke(
    {"messages": [{"role": "user", "content": "How should you respond?"}]},
    context=Context(user_id=authenticated_user_id),
)
```

Authenticate and authorize `authenticated_user_id` before invocation. Context
is dependency injection, not proof that a caller owns the referenced resource.

## Tool results and streaming

Ordinary tool return values become model-visible tool results. Use a LangGraph
`Command` with an appropriate `ToolMessage` when a tool must update agent state.
Keep state updates serializable and validate every external effect in the tool
implementation.

For new streaming integrations, prefer the typed event-streaming API, which
exposes separate projections for messages, tool calls, values, output, and
subgraphs. Existing applications may use `stream`/`astream` with `updates`,
`messages`, or `custom` modes; preserve the caller's expected event contract.

## Practical boundaries

- Import `tool` and `ToolRuntime` from `langchain.tools` in current releases.
- Return or inspect the agent state, including its `messages`; do not assume the
  invocation result is a message object.
- Use standardized `content_blocks` when a consumer needs normalized text,
  reasoning, tool, or multimodal blocks; use raw `content` only when its
  provider-specific shape is intentional.
- Set an appropriate `recursion_limit` in invocation config when tool loops
  need a hard bound.
- Route checkpointers, middleware, approvals, and composition to the shared
  capability references linked from the main skill.
