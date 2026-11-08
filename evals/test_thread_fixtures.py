"""Thread fixture invariants and safe rule evidence collection."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import harness
import validators


class ThreadFixtureTests(unittest.TestCase):
    def test_emission_groups_turns_and_returns_last_run_ids(self) -> None:
        class FakeClient:
            def __init__(self):
                self.runs = []
                self.flushed = False

            def create_run(self, **kwargs):
                self.runs.append(kwargs)

            def flush(self):
                self.flushed = True

        client = FakeClient()
        ids = harness.emit_threads(
            client, "target",
            [{"turns": [["q1", "a1"], ["q2", "a2"]]},
             {"turns": [["q3", "a3"]]}],
            "held-out", "eval-run",
        )
        self.assertEqual(ids, [str(client.runs[1]["id"]), str(client.runs[2]["id"])])
        self.assertEqual(client.runs[0]["extra"]["metadata"]["thread_id"],
                         client.runs[1]["extra"]["metadata"]["thread_id"])
        self.assertNotEqual(client.runs[1]["extra"]["metadata"]["thread_id"],
                            client.runs[2]["extra"]["metadata"]["thread_id"])
        self.assertEqual(client.runs[1]["inputs"]["messages"], [
            {"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
        ])
        self.assertEqual(client.runs[1]["outputs"]["messages"][-1],
                         {"role": "assistant", "content": "a2"})
        self.assertTrue(client.flushed)

    def test_rejects_missing_held_out_label_before_prepare(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "thread-llm-judge"
            (path / "environment").mkdir(parents=True)
            for name in ("Task.md", "instruction.md"):
                (path / name).write_text("test\n")
            (path / "task.toml").write_text('schema_version = "1.3"\n')
            (path / "environment" / "Dockerfile").write_text("FROM scratch\n")
            (path / "harness.json").write_text(json.dumps({
                "fixture_type": "synthetic_threads", "verifier_enabled": False,
                "linux_cli_required": False,
            }))
            (path / "fixtures.json").write_text(json.dumps({
                "seed": [{"turns": [["q", "a"]]}],
                "held_out": [{"turns": [["q", "a"]]}],
            }))
            with self.assertRaisesRegex(ValueError, "invalid held_out thread"):
                harness.validate_task(path)

    def test_rule_collector_omits_prompt_model_and_other_projects(self) -> None:
        project_id = str(uuid4())
        evaluator_id = str(uuid4())
        responses = {
            f"/runs/rules?session_id={project_id}": [
                {"id": str(uuid4()), "session_id": project_id, "evaluator_id": evaluator_id,
                 "evaluator_type": "llm", "group_by": "thread_id", "sampling_rate": 1,
                 "evaluators": [{"structured": {
                     "prompt": "SENSITIVE PROMPT", "model": {"secret": "SENSITIVE MODEL"},
                     "variable_mapping": {"conversation": "human_ai_pairs"},
                 }}]},
                {"id": str(uuid4()), "session_id": str(uuid4())},
            ],
            f"/v1/platform/evaluators/{evaluator_id}": {
                "feedback_keys": ["issue_resolved"], "prompt": "SENSITIVE PROMPT",
            },
            f"/sessions/{project_id}": {"thread_idle_time": 600},
        }

        class FakeClient:
            def request_with_retries(self, method, path):
                return SimpleNamespace(json=lambda: responses[path])

        evidence = validators.collect_rules({"target_project_id": project_id}, FakeClient())
        self.assertEqual(len(evidence["rules"]), 1)
        self.assertEqual(evidence["rules"][0]["group_by"], "thread_id")
        self.assertEqual(evidence["rules"][0]["variable_mapping"],
                         [{"conversation": "human_ai_pairs"}])
        self.assertEqual(evidence["project_idle_fields"], {"thread_idle_time": 600})
        self.assertNotIn("SENSITIVE", json.dumps(evidence))


if __name__ == "__main__":
    unittest.main()
