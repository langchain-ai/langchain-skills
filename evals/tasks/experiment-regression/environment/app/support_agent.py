"""Acme customer-support agent.

The model is scripted so answers are deterministic and need no provider
credentials: it picks a reply from the customer's question and the tool
results already in the conversation.
"""

import hashlib
import sys

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

POLICIES = {
    "returns": "Unopened items can be returned within 30 days of delivery.",
    "shipping": "Standard shipping takes 3-5 business days.",
    "warranty": "Electronics carry a 12-month limited warranty.",
    "address_change": "You can change the delivery address until the order ships.",
    "subscription": "You can cancel any time under Account > Subscription.",
}


@tool
def lookup_policy(topic: str) -> str:
    """Look up Acme's customer policy for a topic."""
    return POLICIES.get(topic, "No policy on file for that topic.")


@tool
def open_ticket(summary: str) -> str:
    """Open a support ticket for a human agent to follow up."""
    return f"Opened ticket T-{hashlib.sha256(summary.encode()).hexdigest()[:6].upper()}."


ROUTES = [
    ("damaged", None, "I'm sorry your order arrived damaged! Please reply with a photo of the damage and we'll refund you right away."),
    ("return", "returns", "{policy} You can start a return from https://acme.example/orders."),
    ("shipping", "shipping", "{policy}"),
    ("warranty", "warranty", "{policy} You can file a claim at https://acme.example/warranty."),
    ("address", "address_change", "{policy} Update it at https://acme.example/orders."),
    ("cancel", "subscription", "{policy}"),
]


class ScriptedSupportModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "scripted-support"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        last_human = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
        question = str(messages[last_human].content).lower()
        tool_results = [m for m in messages[last_human:] if isinstance(m, ToolMessage)]
        return ChatResult(generations=[ChatGeneration(message=self._reply(question, tool_results))])

    def _reply(self, question: str, tool_results: list[ToolMessage]) -> AIMessage:
        for keyword, topic, template in ROUTES:
            if keyword not in question:
                continue
            if topic is None:
                return AIMessage(content=template)
            if not tool_results:
                return _call("lookup_policy", {"topic": topic})
            return AIMessage(content=template.format(policy=tool_results[-1].content))
        if not tool_results:
            return _call("open_ticket", {"summary": question})
        return AIMessage(content=f"{tool_results[-1].content} A teammate will follow up by email.")


def _call(name: str, args: dict) -> AIMessage:
    call_id = "call_" + hashlib.sha256(f"{name}{sorted(args.items())}".encode()).hexdigest()[:12]
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


agent = create_agent(
    model=ScriptedSupportModel(),
    tools=[lookup_policy, open_ticket],
    system_prompt="You are Acme's customer-support agent.",
    name="acme_support",
)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "How long does standard shipping take?"
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    print(result["messages"][-1].content)
