"""Reusable Harbor adapter for scripted or LLM-user conversations."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping, Optional, Protocol, Tuple

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import Agent, FinalMetrics, Step, Trajectory

from .model_user import ModelUser
from .runner import (
    ConversationResult,
    ConversationRunError,
    run_llm_user_conversation,
    run_scripted_conversation,
)


MAX_EVIDENCE_CHARS = 1_000_000


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class HarnessReply:
    """One visible response and directly observed evidence for a Harness turn."""

    message: str
    evidence: Mapping[str, object]


class HarnessSession(Protocol):
    session_id: str
    public_config: Mapping[str, object]

    async def send(self, user_message: str) -> HarnessReply: ...


class RecordingSession:
    """Adapt a repository Harness session to the conversation runner."""

    def __init__(self, harness: HarnessSession) -> None:
        self.harness = harness
        self.events: list[dict[str, object]] = []
        self.exchanges: list[dict[str, object]] = []

    async def send(self, user_message: str) -> str:
        self.events.append(
            {"role": "user", "content": user_message, "timestamp": _timestamp()}
        )
        try:
            reply = await self.harness.send(user_message)
            if not isinstance(reply, HarnessReply):
                raise TypeError("Harness session must return HarnessReply")
        except Exception as error:
            self.exchanges.append(
                {"user_message": user_message, "error": type(error).__name__}
            )
            raise
        encoded_evidence = json.dumps(dict(reply.evidence))
        if len(encoded_evidence) > MAX_EVIDENCE_CHARS:
            raise ValueError("Harness evidence is too large")
        evidence = json.loads(encoded_evidence)
        self.events.append(
            {
                "role": "assistant",
                "content": reply.message,
                "evidence": evidence,
                "timestamp": _timestamp(),
            }
        )
        self.exchanges.append(
            {
                "user_message": user_message,
                "assistant_message": reply.message,
                "evidence": evidence,
            }
        )
        return reply.message


class MultiTurnHarborAgent(BaseAgent):
    """Subclass this adapter and implement the repository-specific bindings."""

    SUPPORTS_ATIF = True
    MAX_TURNS = 8
    SIMULATOR_MODEL: Optional[str] = None

    @staticmethod
    def name() -> str:
        return "multi-turn-harness"

    def version(self) -> str:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def create_harness_session(
        self, environment: BaseEnvironment, context: AgentContext
    ) -> HarnessSession:
        raise NotImplementedError

    def scripted_followups(self) -> Optional[Tuple[str, ...]]:
        return None

    def user_contract(self) -> Optional[str]:
        return None

    async def call_user_model(self, system: str, payload: str) -> str:
        raise NotImplementedError

    async def read_user_observation(
        self, environment: BaseEnvironment
    ) -> Mapping[str, object]:
        return {}

    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        result: Optional[ConversationResult] = None
        model_user: Optional[ModelUser] = None
        session: Optional[RecordingSession] = None
        error_type: Optional[str] = None
        contract: Optional[str] = None
        run_error: Optional[BaseException] = None

        try:
            session = RecordingSession(
                await self.create_harness_session(environment, context)
            )
            followups = self.scripted_followups()
            contract = self.user_contract()
            if (followups is None) == (contract is None):
                raise ValueError("choose exactly one of scripted_followups or user_contract")
            if followups is not None:
                result = await run_scripted_conversation(
                    first_message=instruction,
                    followups=followups,
                    session=session,
                )
            else:
                if not self.SIMULATOR_MODEL:
                    raise ValueError("set SIMULATOR_MODEL for an LLM user")
                model_user = ModelUser(
                    contract=contract or "",
                    call_model=self.call_user_model,
                    read_observation=lambda: self.read_user_observation(environment),
                )
                result = await run_llm_user_conversation(
                    first_message=instruction,
                    session=session,
                    simulated_user=model_user,
                    max_turns=self.MAX_TURNS,
                )
        except ConversationRunError as error:
            result = error.result
            error_type = type(error).__name__
            run_error = error
        except asyncio.CancelledError as error:
            error_type = type(error).__name__
            run_error = error
        except Exception as error:
            error_type = type(error).__name__
            run_error = error

        interaction = self._interaction(
            instruction, session, result, model_user, contract, error_type
        )
        artifact_errors: list[dict[str, str]] = []
        interaction_path = self.logs_dir / "interaction.json"
        trajectory_path = self.logs_dir / "trajectory.json"

        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            interaction_path.write_text(
                json.dumps(interaction, indent=2), encoding="utf-8"
            )
        except Exception as error:
            artifact_errors.append(
                {"operation": "write interaction", "error": type(error).__name__}
            )

        try:
            trajectory_path.write_text(
                json.dumps(self._trajectory(interaction).to_json_dict(), indent=2),
                encoding="utf-8",
            )
        except Exception as error:
            artifact_errors.append(
                {"operation": "write trajectory", "error": type(error).__name__}
            )

        if artifact_errors and interaction_path.is_file():
            interaction["artifact_errors"] = artifact_errors
            try:
                interaction_path.write_text(
                    json.dumps(interaction, indent=2), encoding="utf-8"
                )
            except Exception:
                pass

        if run_error is not None:
            raise run_error.with_traceback(run_error.__traceback__)
        if artifact_errors:
            operations = ", ".join(item["operation"] for item in artifact_errors)
            raise RuntimeError(f"artifact handling failed: {operations}")

    def _interaction(
        self,
        instruction: str,
        session: Optional[RecordingSession],
        result: Optional[ConversationResult],
        model_user: Optional[ModelUser],
        contract: Optional[str],
        error_type: Optional[str],
    ) -> dict[str, object]:
        harness = session.harness if session else None
        turns = [asdict(turn) for turn in result.turns] if result else []
        if turns and session:
            exchanges = iter(session.exchanges)
            for turn in turns:
                if turn["role"] != "assistant":
                    continue
                exchange = next(exchanges, {})
                if "evidence" in exchange:
                    turn["evidence"] = exchange["evidence"]
        return {
            "instruction": instruction,
            "session_id": harness.session_id if harness else None,
            "harness_config": json.loads(json.dumps(dict(harness.public_config)))
            if harness
            else None,
            "turns": turns or (session.events if session else []),
            "harness_exchanges": session.exchanges if session else [],
            "simulation": {
                "mode": "llm_user" if contract is not None else "scripted",
                "model": self.SIMULATOR_MODEL if contract is not None else None,
                "user_contract": contract,
            },
            "simulator_decisions": model_user.records if model_user else [],
            "termination": result.termination if result else "error",
            "error": {"type": error_type} if error_type else None,
        }

    def _trajectory(self, interaction: Mapping[str, object]) -> Trajectory:
        raw_turns = interaction["turns"]
        turns = raw_turns if isinstance(raw_turns, list) else []
        steps: list[Step] = []
        for index, turn in enumerate(turns, 1):
            role = turn["role"]
            extra = {
                key: value
                for key, value in turn.items()
                if key not in {"role", "content", "timestamp"} and value is not None
            }
            values = {
                "step_id": index,
                "source": "agent" if role == "assistant" else "user",
                "message": turn["content"],
                "extra": extra or None,
            }
            if turn.get("timestamp"):
                values["timestamp"] = turn["timestamp"]
            steps.append(Step(**values))
        if not steps:
            steps.append(Step(step_id=1, source="user", message=interaction["instruction"]))
        return Trajectory(
            schema_version="ATIF-v1.7",
            session_id=interaction.get("session_id"),
            agent=Agent(name=self.name(), version=self.version()),
            steps=steps,
            final_metrics=FinalMetrics(total_steps=len(steps)),
            extra={"termination": interaction["termination"], "error": interaction["error"]},
        )
