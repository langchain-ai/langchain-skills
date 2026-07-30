"""LLM user with bounded JSON-format retries."""

from __future__ import annotations

import json
from typing import Awaitable, Callable, Mapping

if __package__:
    from .runner import SimulatorProtocolError, Turn, UserTurn, parse_user_turn
else:
    from runner import SimulatorProtocolError, Turn, UserTurn, parse_user_turn


ModelCall = Callable[[str, str], Awaitable[str]]
ReadObservation = Callable[[], Awaitable[Mapping[str, object]]]

SIMULATOR_SYSTEM = """Act as the user in this conversation, not the assistant.
Follow the supplied user contract and respond to the assistant's latest message.
Use only facts visible in the contract, transcript, and user observation.
Return only one of these JSON objects:
{"message":"next user reply","stop":false}
{"stop":true}"""


class ModelUser:
    """Generate the next user message or stop decision with any LLM client."""

    def __init__(
        self,
        *,
        contract: str,
        call_model: ModelCall,
        read_observation: ReadObservation,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.contract = contract
        self._call_model = call_model
        self._read_observation = read_observation
        self._max_attempts = max_attempts
        self.records: list[dict[str, object]] = []

    async def reply(self, transcript: tuple[Turn, ...]) -> UserTurn:
        decision_id = f"sim-{len(self.records) + 1:03d}"
        try:
            observation = dict(await self._read_observation())
        except Exception as error:
            message = f"user observation failed: {type(error).__name__}"
            record = {"decision_id": decision_id, "attempts": [], "error": message}
            self.records.append(record)
            raise SimulatorProtocolError(message, evidence=record) from error

        attempts: list[dict[str, object]] = []
        format_error = ""
        for attempt in range(1, self._max_attempts + 1):
            payload = json.dumps(
                {
                    "user_contract": self.contract,
                    "visible_transcript": [
                        {"role": turn.role, "content": turn.content}
                        for turn in transcript
                    ],
                    "user_observation": observation,
                    "format_error": format_error,
                }
            )
            try:
                raw = await self._call_model(SIMULATOR_SYSTEM, payload)
            except Exception as error:
                message = f"simulator model call failed: {type(error).__name__}"
                record = {
                    "decision_id": decision_id,
                    "observation": observation,
                    "attempts": attempts,
                    "error": message,
                }
                self.records.append(record)
                raise SimulatorProtocolError(message, evidence=record) from error

            try:
                turn = parse_user_turn(raw)
            except SimulatorProtocolError as error:
                format_error = str(error)
                attempts.append(
                    {"attempt": attempt, "raw": raw, "error": format_error}
                )
                continue

            attempts.append({"attempt": attempt, "raw": raw, "error": None})
            record = {
                "decision_id": decision_id,
                "message": turn.message,
                "stop": turn.stop,
                "observation": observation,
                "attempts": attempts,
            }
            self.records.append(record)
            return turn

        record = {
            "decision_id": decision_id,
            "observation": observation,
            "attempts": attempts,
            "error": "simulator exhausted format retries",
        }
        self.records.append(record)
        raise SimulatorProtocolError(
            "simulator exhausted format retries", evidence=record
        )
