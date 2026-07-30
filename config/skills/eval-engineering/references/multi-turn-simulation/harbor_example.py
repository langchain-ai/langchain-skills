"""Reusable Harbor adapter for scripted or LLM-user conversations."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Protocol

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
        self.events.append({"role": "user", "content": user_message})
        try:
            reply = await self.harness.send(user_message)
            if not isinstance(reply, HarnessReply):
                raise TypeError("Harness session must return HarnessReply")
        except Exception as error:
            self.exchanges.append(
                {"user_message": user_message, "error": type(error).__name__}
            )
            raise
        evidence = json.loads(json.dumps(dict(reply.evidence)))
        self.events.append(
            {"role": "assistant", "content": reply.message, "evidence": evidence}
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
    SIMULATOR_MODEL: str | None = None

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

    def scripted_followups(self) -> tuple[str, ...] | None:
        return None

    def user_contract(self) -> str | None:
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
        result: ConversationResult | None = None
        model_user: ModelUser | None = None
        session: RecordingSession | None = None
        error_type: str | None = None
        contract: str | None = None

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
            raise
        except Exception as error:
            error_type = type(error).__name__
            raise
        finally:
            interaction = self._interaction(
                instruction, session, result, model_user, contract, error_type
            )
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            interaction_path = self.logs_dir / "interaction.json"
            interaction_path.write_text(
                json.dumps(interaction, indent=2), encoding="utf-8"
            )
            trajectory_path = self.logs_dir / "trajectory.json"
            trajectory_path.write_text(
                json.dumps(self._trajectory(interaction).to_json_dict(), indent=2),
                encoding="utf-8",
            )
            await environment.upload_file(interaction_path, "/app/interaction.json")
            await environment.upload_file(
                interaction_path, "/logs/artifacts/interaction.json"
            )

    def _interaction(
        self,
        instruction: str,
        session: RecordingSession | None,
        result: ConversationResult | None,
        model_user: ModelUser | None,
        contract: str | None,
        error_type: str | None,
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
        last_at: datetime | None = None
        steps: list[Step] = []
        for index, turn in enumerate(turns, 1):
            now = datetime.now(timezone.utc)
            if last_at is not None and now <= last_at:
                now = last_at + timedelta(microseconds=1)
            last_at = now
            role = turn["role"]
            extra = {
                key: value
                for key, value in turn.items()
                if key not in {"role", "content"} and value is not None
            }
            steps.append(
                Step(
                    step_id=index,
                    timestamp=now.isoformat().replace("+00:00", "Z"),
                    source="agent" if role == "assistant" else "user",
                    message=turn["content"],
                    extra=extra or None,
                )
            )
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
