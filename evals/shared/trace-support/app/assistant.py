"""Support assistant that answers product questions and opens support tickets.

Documentation search and ticket creation run in the separate tools service,
which the assistant calls over HTTP.
"""

from __future__ import annotations

import json
import os
import urllib.request

TOOLS_URL = os.environ.get("TOOLS_SERVICE_URL", "http://127.0.0.1:8765")

TICKET_PHRASES = ("open a ticket", "escalate", "talk to support")
CLOSING_PHRASES = ("that's all", "thanks, bye", "no more questions")


class ScriptedModel:
    """Deterministic stand-in for a chat model."""

    def plan(self, messages: list[dict]) -> dict | None:
        last = messages[-1]["content"].lower()
        if any(p in last for p in CLOSING_PHRASES):
            return None
        if any(p in last for p in TICKET_PHRASES):
            summary = next(m["content"] for m in messages if m["role"] == "user")
            return {"tool": "create_ticket", "arguments": {"summary": summary}}
        return {"tool": "search_docs", "arguments": {"query": last}}

    def respond(self, messages: list[dict], tool_name: str | None, tool_result: dict | None) -> str:
        if tool_name is None:
            return "Glad I could help. Have a great day!"
        if tool_name == "create_ticket":
            return f"I've opened ticket {tool_result['ticket_id']}. Our team will follow up by email."
        articles = tool_result.get("articles") or []
        if not articles:
            return "I couldn't find documentation on that. Would you like me to open a ticket?"
        top = articles[0]
        return f"{top['body']} (See \"{top['title']}\".)"


model = ScriptedModel()


def call_tool(name: str, arguments: dict) -> dict:
    request = urllib.request.Request(
        f"{TOOLS_URL}/{name}",
        data=json.dumps(arguments).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def handle_turn(conversation_id: str, history: list[dict], user_message: str) -> str:
    messages = history + [{"role": "user", "content": user_message}]
    step = model.plan(messages)
    if step is None:
        return model.respond(messages, None, None)
    result = call_tool(step["tool"], step["arguments"])
    return model.respond(messages, step["tool"], result)
