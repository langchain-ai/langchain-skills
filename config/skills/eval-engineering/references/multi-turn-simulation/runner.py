"""Conversation loops for scripted and LLM-user Harbor tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, Protocol


class SimulatorProtocolError(RuntimeError):
    """The simulator failed; do not score this as Harness failure."""

    def __init__(self, message: str, *, evidence: object | None = None) -> None:
        super().__init__(message)
        self.evidence = evidence


@dataclass(frozen=True)
class Turn:
    role: Literal["user", "assistant"]
    content: str
    origin: Literal["instruction", "scripted", "harness", "simulator"]
    decision_id: str | None = None


@dataclass(frozen=True)
class UserTurn:
    message: str | None
    stop: bool


@dataclass(frozen=True)
class ConversationResult:
    turns: tuple[Turn, ...]
    termination: Literal[
        "script_finished", "user_stop", "turn_limit", "simulator_error"
    ]
    harness_calls: int
    simulator_calls: int
    error: str | None = None


class ConversationRunError(RuntimeError):
    """A simulator failure with delivered turns retained for audit."""

    def __init__(
        self,
        message: str,
        *,
        result: ConversationResult,
        simulator_evidence: object | None = None,
    ) -> None:
        super().__init__(message)
        self.result = result
        self.simulator_evidence = simulator_evidence


class AgentSession(Protocol):
    async def send(self, user_message: str) -> str: ...


class SimulatedUser(Protocol):
    async def reply(self, transcript: tuple[Turn, ...]) -> UserTurn: ...


def parse_user_turn(raw: str) -> UserTurn:
    """Parse either a delivered reply or a message-free stop decision."""
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise SimulatorProtocolError("simulator output is not valid JSON") from error
    if not isinstance(value, dict) or type(value.get("stop")) is not bool:
        raise SimulatorProtocolError("simulator output must contain a boolean stop")
    if value["stop"] is True:
        if set(value) != {"stop"}:
            raise SimulatorProtocolError("a stop decision must not contain a message")
        return UserTurn(message=None, stop=True)
    if set(value) != {"message", "stop"}:
        raise SimulatorProtocolError("a reply must contain only message and stop")
    message = value["message"]
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= 2_000:
        raise SimulatorProtocolError("simulator message is invalid")
    return UserTurn(message=message, stop=False)


def _message(value: object, source: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100_000:
        raise ValueError(f"{source} message is invalid")
    return value


async def run_scripted_conversation(
    *,
    first_message: str,
    followups: tuple[str, ...],
    session: AgentSession,
) -> ConversationResult:
    """Send known user turns sequentially through one Harness session."""
    turns: list[Turn] = []
    for index, raw_message in enumerate((first_message, *followups)):
        message = _message(raw_message, "user")
        turns.append(
            Turn("user", message, "instruction" if index == 0 else "scripted")
        )
        reply = _message(await session.send(message), "assistant")
        turns.append(Turn("assistant", reply, "harness"))
    return ConversationResult(
        tuple(turns), "script_finished", len(followups) + 1, 0
    )


async def run_llm_user_conversation(
    *,
    first_message: str,
    session: AgentSession,
    simulated_user: SimulatedUser,
    max_turns: int = 8,
) -> ConversationResult:
    """Alternate one Harness session with an external LLM user."""
    if max_turns < 1:
        raise ValueError("max_turns must be positive")

    user_message = _message(first_message, "first user")
    turns = [Turn("user", user_message, "instruction")]
    simulator_calls = 0

    for harness_calls in range(1, max_turns + 1):
        assistant_message = _message(await session.send(user_message), "assistant")
        turns.append(Turn("assistant", assistant_message, "harness"))

        if harness_calls == max_turns:
            return ConversationResult(
                tuple(turns), "turn_limit", harness_calls, simulator_calls
            )

        simulator_calls += 1
        try:
            reply = await simulated_user.reply(tuple(turns))
        except SimulatorProtocolError as error:
            result = ConversationResult(
                tuple(turns),
                "simulator_error",
                harness_calls,
                simulator_calls,
                str(error),
            )
            raise ConversationRunError(
                str(error), result=result, simulator_evidence=error.evidence
            ) from error
        if not isinstance(reply, UserTurn):
            message = "simulator did not return UserTurn"
            result = ConversationResult(
                tuple(turns),
                "simulator_error",
                harness_calls,
                simulator_calls,
                message,
            )
            raise ConversationRunError(message, result=result)

        if reply.stop:
            return ConversationResult(
                tuple(turns), "user_stop", harness_calls, simulator_calls
            )

        user_message = _message(reply.message, "simulator")
        turns.append(
            Turn("user", user_message, "simulator", f"sim-{simulator_calls:03d}")
        )

    raise AssertionError("conversation loop terminated unexpectedly")
