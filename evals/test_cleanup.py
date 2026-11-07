"""Offline checks for temporary LangSmith project cleanup."""

from __future__ import annotations

import json
import tempfile
import unittest
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
            "inspected_at": "2026-11-07T12:00:00+00:00",
        }
        (self.jobs / self.run_id / "report.json").write_text(json.dumps(report))
        cleanup.cleanup_runs([self.run_id], execute=True)
        self.assertEqual(self.ls.deleted, [self.target_id])


if __name__ == "__main__":
    unittest.main()
