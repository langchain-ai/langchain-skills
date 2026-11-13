"""Loaded before every sample by check_samples.py. Makes samples runnable offline.

- Chat models resolve to FakeChatModel: `init_chat_model`, provider strings in
  `create_agent` / `create_deep_agent`, and direct `ChatOpenAI` / `ChatAnthropic`.
- `OpenAIEmbeddings` resolves to a deterministic fake embedding.
- Outbound network connections fail fast, so nothing reaches a real service.
"""

from __future__ import annotations

import importlib
import os
import socket
import sys
from typing import Any

for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TAVILY_API_KEY", "PINECONE_API_KEY",
            "TYPESAFE_API_KEY", "LANGSMITH_API_KEY"):
    os.environ.setdefault(key, "fake-key-for-sample-check")
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"


# --- Network -------------------------------------------------------------------------------

_real_connect = socket.socket.connect


def _offline_connect(self: socket.socket, address: Any) -> Any:
    if self.family == socket.AF_UNIX:
        return _real_connect(self, address)
    host = address[0] if isinstance(address, tuple) else address
    if host in ("127.0.0.1", "::1", "localhost"):
        return _real_connect(self, address)
    raise ConnectionRefusedError(f"network is disabled in the sample check (tried {address})")


socket.socket.connect = _offline_connect  # type: ignore[method-assign]


# --- Fake chat model ------------------------------------------------------------------------

from langchain_core.embeddings import DeterministicFakeEmbedding  # noqa: E402
from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402
from langchain_core.runnables import RunnableLambda  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from pydantic import ConfigDict  # noqa: E402


def _fake_value(schema: dict[str, Any]) -> Any:
    kind = schema.get("type")
    if "enum" in schema:
        return schema["enum"][0]
    if "anyOf" in schema:
        return _fake_value(schema["anyOf"][0])
    if kind == "string":
        return "fake"
    if kind in ("number", "integer"):
        return 1
    if kind == "boolean":
        return True
    if kind == "array":
        return []
    if kind == "object":
        return _fake_args(schema)
    return None


def _fake_args(schema: dict[str, Any]) -> dict[str, Any]:
    props = schema.get("properties", {})
    return {name: _fake_value(prop) for name, prop in props.items()}


class FakeChatModel(BaseChatModel):
    """Answers every call with a short text reply.

    When the caller forces a tool call (`tool_choice="any"`, as `create_agent` does for
    structured output), it calls the last bound tool with placeholder arguments.
    """

    model_config = ConfigDict(extra="allow")
    model: str = "fake-model"

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def _generate(self, messages: Any, stop: Any = None, run_manager: Any = None,
                  **kwargs: Any) -> ChatResult:
        tools = kwargs.get("tools") or []
        if tools and kwargs.get("tool_choice") in ("any", "required"):
            fn = tools[-1]["function"]
            message = AIMessage(content="", tool_calls=[{
                "name": fn["name"], "args": _fake_args(fn.get("parameters", {})),
                "id": "call_fake", "type": "tool_call",
            }])
        else:
            message = AIMessage(content="fake response")
        return ChatResult(generations=[ChatGeneration(message=message)])

    def bind_tools(self, tools: Any, *, tool_choice: Any = None, **kwargs: Any) -> Any:
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools],
                         tool_choice=tool_choice, **kwargs)

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        spec = convert_to_openai_tool(schema)["function"]
        args = _fake_args(spec.get("parameters", {}))
        if isinstance(schema, type):
            return RunnableLambda(lambda _: schema.model_construct(**args)
                                  if hasattr(schema, "model_construct") else schema(**args))
        return RunnableLambda(lambda _: args)


class FakeEmbeddings(DeterministicFakeEmbedding):
    model_config = ConfigDict(extra="allow")
    size: int = 64


def fake_init_chat_model(model: Any = None, *args: Any, **kwargs: Any) -> FakeChatModel:
    return FakeChatModel(model=str(model or "fake-model"))


# --- Swap the real classes for fakes everywhere they were imported ------------------------

_replacements: dict[int, Any] = {}


def _register(module: str, name: str, fake: Any) -> None:
    try:
        mod = importlib.import_module(module)
    except ImportError:
        return
    original = getattr(mod, name, None)
    if original is not None:
        _replacements[id(original)] = fake


_register("langchain.chat_models", "init_chat_model", fake_init_chat_model)
_register("langchain.chat_models.base", "init_chat_model", fake_init_chat_model)
_register("langchain_openai", "ChatOpenAI", type("ChatOpenAI", (FakeChatModel,), {}))
_register("langchain_openai", "AzureChatOpenAI", type("AzureChatOpenAI", (FakeChatModel,), {}))
_register("langchain_openai", "OpenAIEmbeddings", type("OpenAIEmbeddings", (FakeEmbeddings,), {}))
_register("langchain_anthropic", "ChatAnthropic", type("ChatAnthropic", (FakeChatModel,), {}))

# Import the libraries that resolve models internally, so the sweep below reaches them.
for _module in ("langchain.agents", "langchain.agents.factory", "deepagents", "deepagents.graph",
                "deepagents._models"):
    try:
        importlib.import_module(_module)
    except ImportError:
        pass

for _mod in list(sys.modules.values()):
    _vars = getattr(_mod, "__dict__", None)
    if not isinstance(_vars, dict):
        continue
    for _name, _value in list(_vars.items()):
        _fake = _replacements.get(id(_value))
        if _fake is not None:
            _vars[_name] = _fake
