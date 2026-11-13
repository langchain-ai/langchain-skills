"""Strands support agent that answers product questions and opens support tickets.

Documentation search and ticket creation run in the separate tools service,
which the agent's tools call over HTTP. A scripted model stands in for a
provider model so every run is deterministic.
"""

from __future__ import annotations

import json
import os
import urllib.request

from strands import Agent, tool
from strands.models import Model

TOOLS_URL = os.environ.get("TOOLS_SERVICE_URL", "http://127.0.0.1:8765")

TICKET_PHRASES = ("open a ticket", "escalate", "talk to support")
CLOSING_PHRASES = ("that's all", "thanks, bye", "no more questions")


def call_tool(name: str, arguments: dict) -> dict:
    request = urllib.request.Request(
        f"{TOOLS_URL}/{name}",
        data=json.dumps(arguments).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


@tool
def search_docs(query: str) -> str:
    """Search product documentation for articles relevant to the query."""
    return json.dumps(call_tool("search_docs", {"query": query}))


@tool
def create_ticket(summary: str) -> str:
    """Open a support ticket with the given summary."""
    return json.dumps(call_tool("create_ticket", {"summary": summary}))


def _user_texts(messages: list[dict]) -> list[str]:
    return [b["text"] for m in messages if m["role"] == "user" for b in m["content"] if "text" in b]


class ScriptedModel(Model):
    """Deterministic stand-in for a provider model."""

    def __init__(self) -> None:
        self.config: dict = {}

    def get_config(self) -> dict:
        return self.config

    def update_config(self, **model_config) -> None:
        self.config.update(model_config)

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError("structured output is not used by this assistant")

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        results = [b["toolResult"] for b in messages[-1]["content"] if "toolResult" in b]
        if results:
            tool_use = next(b["toolUse"] for b in messages[-2]["content"] if "toolUse" in b)
            text = self._reply(tool_use["name"], json.loads(results[0]["content"][0]["text"]))
            async for event in self._text(text):
                yield event
            return
        texts = _user_texts(messages)
        last = texts[-1].lower()
        if any(p in last for p in CLOSING_PHRASES):
            async for event in self._text("Glad I could help. Have a great day!"):
                yield event
            return
        if any(p in last for p in TICKET_PHRASES):
            name, arguments = "create_ticket", {"summary": texts[0]}
        else:
            name, arguments = "search_docs", {"query": last}
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"call-{len(messages)}", "name": name}}}}
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(arguments)}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}

    @staticmethod
    def _reply(tool_name: str, result: dict) -> str:
        if tool_name == "create_ticket":
            return f"I've opened ticket {result['ticket_id']}. Our team will follow up by email."
        articles = result.get("articles") or []
        if not articles:
            return "I couldn't find documentation on that. Would you like me to open a ticket?"
        top = articles[0]
        return f"{top['body']} (See \"{top['title']}\".)"

    @staticmethod
    async def _text(text: str):
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": text}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}


_agents: dict[str, Agent] = {}


def handle_turn(conversation_id: str, history: list[dict], user_message: str) -> str:
    agent = _agents.get(conversation_id)
    if agent is None:
        agent = Agent(model=ScriptedModel(), tools=[search_docs, create_ticket], callback_handler=None)
        _agents[conversation_id] = agent
    return str(agent(user_message)).strip()
