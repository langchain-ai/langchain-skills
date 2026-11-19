"""Offline checks for temporary LangSmith project cleanup."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import cleanup
import harness


class FakeClient:
    def __init__(self, workspace_id: str, project: SimpleNamespace):
        self.workspace_id = workspace_id
        self.project = project
        self.deleted: list[str] = []

    def read_project(self, project_id: str) -> SimpleNamespace:
        return self.project

    def delete_project(self, project_id: str) -> None:
        self.deleted.append(project_id)


class CleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.jobs = Path(self.temporary.name)
        self.run_id = str(uuid4())
        self.target_id = str(uuid4())
        self.trace_id = str(uuid4())
        self.workspace_id = str(uuid4())
        self.data = {
            "schema_version": 1,
            "run_id": self.run_id,
            "task": "chained-eval",
            "profile": "full",
            "status": "completed",
            "workspace_id": self.workspace_id,
            "target_project_id": self.target_id,
            "target_project_name": f"lcskills-eval-chained-eval-full-{self.run_id[:8]}",
            "trace_project_id": self.trace_id,
            "held_out_run_ids": [],
        }
        self.project = SimpleNamespace(
            id=self.target_id,
            name=self.data["target_project_name"],
            description=f"Isolated Harbor task target for {self.run_id}",
        )
        self.ls = FakeClient(self.workspace_id, self.project)
        self.addCleanup(patch.stopall)
        patch.object(harness, "JOBS", self.jobs).start()
        patch.object(cleanup, "JOBS", self.jobs).start()
        patch.object(cleanup, "client", return_value=self.ls).start()
        harness.save_manifest(self.data)

    def test_dry_run_does_not_delete(self) -> None:
        cleanup.cleanup_runs([self.run_id])
        self.assertEqual(self.ls.deleted, [])
        self.assertFalse(harness.load_manifest(self.run_id).get("target_project_deleted"))

    def test_execute_deletes_only_recorded_target(self) -> None:
        cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted, [self.target_id])
        self.assertTrue(harness.load_manifest(self.run_id)["target_project_deleted"])

    def test_rejects_shared_trace_project(self) -> None:
        self.data["target_project_id"] = self.trace_id
        harness.save_manifest(self.data)
        with self.assertRaisesRegex(ValueError, "identical"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted, [])

    def test_rejects_workspace_mismatch(self) -> None:
        self.ls.workspace_id = str(uuid4())
        with self.assertRaisesRegex(RuntimeError, "workspace"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted, [])

    def test_rejects_live_project_mismatch(self) -> None:
        self.project.description = "unrelated project"
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted, [])

    def test_requires_live_report_after_fresh_cases(self) -> None:
        self.data["held_out_run_ids"] = [str(uuid4())]
        harness.save_manifest(self.data)
        with self.assertRaises(FileNotFoundError):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted, [])

    def test_accepts_matching_live_report(self) -> None:
        self.data["held_out_run_ids"] = [str(uuid4())]
        harness.save_manifest(self.data)
        report = {
            "run_id": self.run_id,
            "target_project_id": self.target_id,
            "trace_project_id": self.trace_id,
            "held_out_count": 1,
            "live": {"traces": []},
            "validators": {"evidence": {"rules": [], "insights_configs": [], "insights_jobs": []}},
            "inspected_at": "2026-11-07T12:00:00+00:00",
        }
        (self.jobs / self.run_id / "report.json").write_text(json.dumps(report))
        cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted, [self.target_id])

    def test_requires_configuration_evidence_before_cleanup(self) -> None:
        self.data["held_out_run_ids"] = [str(uuid4())]
        harness.save_manifest(self.data)
        report = {
            "run_id": self.run_id,
            "target_project_id": self.target_id,
            "trace_project_id": self.trace_id,
            "held_out_count": 1,
            "live": {"traces": []},
            "inspected_at": "2026-11-07T12:00:00+00:00",
        }
        (self.jobs / self.run_id / "report.json").write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "matching live report"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted, [])


class FakeResponse:
    def __init__(self, body: dict):
        self.body = body

    def json(self) -> dict:
        return self.body


class FakeAgentClient(FakeClient):
    def __init__(self, workspace_id: str, project: SimpleNamespace, agent: dict | None):
        super().__init__(workspace_id, project)
        self.agent = agent
        self.deleted_agents: list[str] = []

    def request_with_retries(self, method: str, path: str, **kwargs) -> FakeResponse:
        agent_id = path.rsplit("/", 1)[-1]
        if method == "GET":
            if self.agent is None:
                raise cleanup.LangSmithNotFoundError("missing")
            return FakeResponse(self.agent)
        if method == "DELETE":
            self.deleted_agents.append(agent_id)
            return FakeResponse({})
        raise AssertionError(method)


class AgentCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.jobs = Path(self.temporary.name)
        self.run_id = str(uuid4())
        self.target_id = str(uuid4())
        self.workspace_id = str(uuid4())
        self.agent_uuid = str(uuid4())
        self.agent_id = f"lcskills-eval-trace-sdk-full-{self.run_id[:8]}"
        self.data = {
            "schema_version": 1,
            "run_id": self.run_id,
            "task": "trace-sdk",
            "profile": "full",
            "status": "completed",
            "workspace_id": self.workspace_id,
            "target_project_id": self.target_id,
            "target_project_name": f"lcskills-eval-trace-sdk-full-{self.run_id[:8]}",
            "trace_project_id": str(uuid4()),
            "held_out_run_ids": [],
            "target_agent_id": self.agent_id,
            "target_agent_uuid": self.agent_uuid,
        }
        project = SimpleNamespace(
            id=self.target_id,
            name=self.data["target_project_name"],
            description=f"Isolated Harbor task target for {self.run_id}",
        )
        self.ls = FakeAgentClient(self.workspace_id, project, {"id": self.agent_id, "agent_uuid": self.agent_uuid})
        self.addCleanup(patch.stopall)
        patch.object(harness, "JOBS", self.jobs).start()
        patch.object(cleanup, "JOBS", self.jobs).start()
        patch.object(cleanup, "client", return_value=self.ls).start()
        harness.save_manifest(self.data)

    def write_report(self, evidence: bool = True) -> None:
        report = {"run_id": self.run_id, "inspected_at": "2026-11-12T12:00:00+00:00",
                  "validators": {"evidence": {"runs": {}}} if evidence else {}}
        (self.jobs / self.run_id / "report.json").write_text(json.dumps(report))

    def test_requires_trace_evidence_before_cleanup(self) -> None:
        self.write_report(evidence=False)
        with self.assertRaisesRegex(ValueError, "trace evidence"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual((self.ls.deleted, self.ls.deleted_agents), ([], []))

    def test_deletes_project_and_matching_agent(self) -> None:
        self.write_report()
        cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted, [self.target_id])
        self.assertEqual(self.ls.deleted_agents, [self.agent_id])
        self.assertTrue(harness.load_manifest(self.run_id)["target_agent_deleted"])

    def test_refuses_agent_with_different_uuid(self) -> None:
        self.write_report()
        self.ls.agent = {"id": self.agent_id, "agent_uuid": str(uuid4())}
        with self.assertRaisesRegex(RuntimeError, "agent identity mismatch"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted_agents, [])
        self.assertFalse(harness.load_manifest(self.run_id).get("target_agent_deleted"))

    def test_rejects_agent_id_outside_run_identity(self) -> None:
        self.data["target_agent_id"] = "production-support-agent"
        harness.save_manifest(self.data)
        self.write_report()
        with self.assertRaisesRegex(ValueError, "agent ID does not match"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual((self.ls.deleted, self.ls.deleted_agents), ([], []))

    def test_already_deleted_agent_is_marked_done(self) -> None:
        self.write_report()
        self.ls.agent = None
        cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted_agents, [])
        self.assertTrue(harness.load_manifest(self.run_id)["target_agent_deleted"])



class FakeDatasetClient(FakeClient):
    def __init__(self, workspace_id: str, project: SimpleNamespace, dataset: SimpleNamespace | None):
        super().__init__(workspace_id, project)
        self.dataset = dataset
        self.deleted_datasets: list[str] = []
        self.deleted_rules: list[str] = []
        self.rules: list[dict] = []

    def read_dataset(self, dataset_name: str) -> SimpleNamespace:
        if self.dataset is None:
            raise cleanup.LangSmithNotFoundError("missing")
        return self.dataset

    def delete_dataset(self, dataset_id: str) -> None:
        self.deleted_datasets.append(dataset_id)

    def request_with_retries(self, method: str, path: str, **kwargs) -> FakeResponse:
        if method == "GET":
            return FakeResponse(self.rules)
        self.deleted_rules.append(path.rsplit("/", 1)[-1])
        return FakeResponse({})


class DatasetCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.jobs = Path(self.temporary.name)
        self.run_id = str(uuid4())
        self.target_id = str(uuid4())
        self.workspace_id = str(uuid4())
        self.dataset_id = str(uuid4())
        name = f"lcskills-eval-experiment-regression-full-{self.run_id[:8]}"
        self.data = {
            "schema_version": 1,
            "run_id": self.run_id,
            "task": "experiment-regression",
            "profile": "full",
            "status": "completed",
            "workspace_id": self.workspace_id,
            "target_project_id": self.target_id,
            "target_project_name": name,
            "target_dataset_name": name,
            "trace_project_id": str(uuid4()),
            "held_out_run_ids": [],
            "created_at": "2026-11-19T12:00:00+00:00",
        }
        project = SimpleNamespace(id=self.target_id, name=name,
                                  description=f"Isolated Harbor task target for {self.run_id}")
        self.dataset = SimpleNamespace(id=self.dataset_id, name=name,
                                       created_at=datetime(2026, 11, 19, 12, 5, tzinfo=timezone.utc))
        self.ls = FakeDatasetClient(self.workspace_id, project, self.dataset)
        self.addCleanup(patch.stopall)
        patch.object(harness, "JOBS", self.jobs).start()
        patch.object(cleanup, "JOBS", self.jobs).start()
        patch.object(cleanup, "client", return_value=self.ls).start()
        harness.save_manifest(self.data)

    def write_report(self, dataset_id: str | None = None) -> None:
        evidence = {"dataset_id": dataset_id or self.dataset_id, "dataset_name": self.data["target_dataset_name"]}
        report = {"run_id": self.run_id, "inspected_at": "2026-11-19T12:30:00+00:00",
                  "validators": {"evidence": evidence}}
        (self.jobs / self.run_id / "report.json").write_text(json.dumps(report))

    def test_requires_dataset_evidence_before_cleanup(self) -> None:
        with self.assertRaisesRegex(ValueError, "dataset evidence"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted_datasets, [])

    def test_deletes_recorded_dataset_and_its_rules(self) -> None:
        self.write_report()
        rule_id = str(uuid4())
        self.ls.rules = [{"id": rule_id, "dataset_id": self.dataset_id}, {"id": str(uuid4()), "dataset_id": str(uuid4())}]
        cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted_rules, [rule_id])
        self.assertEqual(self.ls.deleted_datasets, [self.dataset_id])
        self.assertTrue(harness.load_manifest(self.run_id)["target_dataset_deleted"])

    def test_refuses_dataset_created_before_the_trial(self) -> None:
        self.write_report()
        self.dataset.created_at = datetime(2026, 11, 1, tzinfo=timezone.utc)
        with self.assertRaisesRegex(RuntimeError, "dataset identity mismatch"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted_datasets, [])

    def test_refuses_dataset_id_other_than_reported(self) -> None:
        self.write_report(dataset_id=str(uuid4()))
        with self.assertRaisesRegex(RuntimeError, "dataset identity mismatch"):
            cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted_datasets, [])

    def test_missing_dataset_is_marked_deleted(self) -> None:
        self.write_report()
        self.ls.dataset = None
        cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted_datasets, [])
        self.assertTrue(harness.load_manifest(self.run_id)["target_dataset_deleted"])

    def test_rejects_dataset_name_outside_run_identity(self) -> None:
        self.data["target_dataset_name"] = "customer-regression-suite"
        harness.save_manifest(self.data)
        with self.assertRaisesRegex(ValueError, "dataset name"):
            cleanup.cleanup_runs([self.run_id], execute=True)


if __name__ == "__main__":
    unittest.main()
