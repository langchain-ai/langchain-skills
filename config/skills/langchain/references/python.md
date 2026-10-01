# LangChain Python

Use this reference for Python applications. Inspect the installed versions and
current imports before editing an existing project. The current documentation
starts at <https://docs.langchain.com/oss/python/langchain/overview> and the
quickstart is <https://docs.langchain.com/oss/python/langchain/quickstart>.

## Minimal agent

```python
import os

from langchain.agents import create_agent
from langchain_core.tools import tool


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
print(result["messages"][-1].content)
```

For a new application, create the project where the user requested it, use the
provider and model they selected, put provider credentials in a gitignored
environment file, and install only the required LangChain and provider packages.
Do not force a new directory or demo when modifying an existing application.

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

For a single model call with no agent loop, use the selected chat model's
`with_structured_output` support instead of creating an agent.

## Practical boundaries

- Import `tool` from the package used by the installed release; current code
  commonly uses `langchain_core.tools`.
- Return or inspect the agent state, including its `messages`; do not assume the
  invocation result is a message object.
- Set an appropriate `recursion_limit` in invocation config when tool loops
  need a hard bound.
- Route checkpointers, middleware, approvals, and composition to the shared
  capability references linked from the main skill.
