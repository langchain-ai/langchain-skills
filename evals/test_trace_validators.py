"""Offline checks for the tracing tasks' validators and harness settings."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import harness
import validators
from validators import validate_traces

T0 = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
THREADS = ["conv-1001", "conv-1001", "conv-1001", "conv-1002", "conv-1002", "conv-1003", "conv-1003"]
CALLS_SERVICE = [True, True, False, True, True, True, True]
EXPECTED = json.loads((harness.SHARED / "trace-support" / "expected.json").read_text())
NAMES = {"rule": "names", "names": ["handle_search_request", "handle_ticket_request"]}
PROCESS = {"rule": "process"}


def run(run_id, trace_id, parent, name, start, thread, process):
    return {"id": run_id, "trace_id": trace_id, "parent_run_id": parent, "name": name, "run_type": "chain",
            "start_time": start.isoformat(), "thread": thread, "process": process}


def execution(offset=0, prefix="a", linked=True, root_thread=True, service_thread=True, processes=(None, None)):
    runs = []
    for index, (thread, calls_service) in enumerate(zip(THREADS, CALLS_SERVICE)):
        start = T0 + timedelta(seconds=offset + index * 0.5)
        trace_id = f"{prefix}{index}"
        runs.append(run(f"{trace_id}-root", trace_id, None, "support_turn", start,
                        thread if root_thread else None, processes[0]))
        if not calls_service:
            continue
        runs.append(run(f"{trace_id}-call", trace_id, f"{trace_id}-root", "call_tool", start, thread, processes[0]))
        if linked:
            runs.append(run(f"{trace_id}-svc", trace_id, f"{trace_id}-call", "handle_search_request", start,
                            thread if service_thread else None, processes[1]))
        else:
            runs.append(run(f"{trace_id}-svc", f"{trace_id}-svc", None, "handle_search_request", start,
                            None, processes[1]))
    return runs


def evidence(runs, environment="DEVELOPMENT", stray=0, target_runs=0):
    environments = {name: {"runs": 0, "roots": 0} for name in ("DEVELOPMENT", "STAGING", "LOCAL", "PRODUCTION")}
    environments[environment] = {"runs": len(runs), "roots": sum(r["parent_run_id"] is None for r in runs)}
    if stray:
        environments["LOCAL"] = {"runs": stray, "roots": stray}
    return {"environments": environments, "target_project_runs": target_runs, "runs": {environment: runs}}


def passed(result):
    return {name: result[name]["passed"] for name in ("destination", "turns_arrived", "threads", "distributed_tracing")}


class TraceValidatorTests(unittest.TestCase):
    def test_sdk_reference_shape_passes_with_names_rule(self):
        result = validate_traces(evidence(execution()), EXPECTED, NAMES)
        self.assertTrue(all(passed(result).values()), passed(result))
        self.assertEqual(result["threads"]["child_coverage"], 1.0)

    def test_otel_reference_shape_passes_with_process_rule(self):
        result = validate_traces(evidence(execution(processes=("assistant", "tools"))), EXPECTED, PROCESS)
        self.assertTrue(all(passed(result).values()), passed(result))
        self.assertEqual(result["distributed_tracing"]["linked_traces"], 6)

    def test_unlinked_service_fails_only_distributed_tracing(self):
        for rule, processes in ((NAMES, (None, None)), (PROCESS, ("assistant", "tools"))):
            result = validate_traces(evidence(execution(linked=False, processes=processes)), EXPECTED, rule)
            self.assertEqual(passed(result), {"destination": True, "turns_arrived": True,
                                              "threads": True, "distributed_tracing": False})
            self.assertEqual(result["distributed_tracing"]["service_roots"], 6)

    def test_latest_execution_is_evaluated(self):
        runs = execution(prefix="old", linked=False) + execution(offset=120, prefix="new")
        result = validate_traces(evidence(runs), EXPECTED, NAMES)
        self.assertTrue(all(passed(result).values()), passed(result))
        self.assertEqual(result["turns_arrived"]["executions_observed"], 2)

    def test_missing_root_thread_fails_threads(self):
        result = validate_traces(evidence(execution(root_thread=False)), EXPECTED, NAMES)
        self.assertFalse(result["threads"]["passed"])

    def test_missing_service_thread_is_reported_not_failed(self):
        result = validate_traces(evidence(execution(service_thread=False)), EXPECTED, NAMES)
        self.assertTrue(result["threads"]["passed"])
        self.assertEqual(result["threads"]["service_coverage"], 0.0)

    def test_wrong_environment_or_strays_fail_destination(self):
        wrong = validate_traces(evidence(execution(), environment="LOCAL"), EXPECTED, NAMES)
        self.assertFalse(wrong["destination"]["passed"])
        self.assertFalse(wrong["turns_arrived"]["passed"])
        stray = validate_traces(evidence(execution(), stray=3), EXPECTED, NAMES)
        self.assertFalse(stray["destination"]["passed"])
        target = validate_traces(evidence(execution(), target_runs=1), EXPECTED, NAMES)
        self.assertFalse(target["destination"]["passed"])

    def test_lost_turns_fail_turns_arrived(self):
        runs = [r for r in execution() if r["trace_id"] not in {"a5", "a6"}]
        result = validate_traces(evidence(runs), EXPECTED, NAMES)
        self.assertFalse(result["turns_arrived"]["passed"])
        self.assertFalse(result["distributed_tracing"]["passed"])

    def test_collect_refuses_agent_with_different_uuid(self):
        class Response:
            def json(self):
                return {"id": "lcskills-eval-trace-sdk-full-12345678", "agent_uuid": str(uuid4()), "environments": []}

        class Client:
            def request_with_retries(self, method, path, **kwargs):
                return Response()

        data = {"target_agent_id": "lcskills-eval-trace-sdk-full-12345678", "target_agent_uuid": str(uuid4()),
                "target_project_id": str(uuid4())}
        with self.assertRaisesRegex(RuntimeError, "identity"):
            validators.collect_traces(data, Client())


class TraceHarnessTests(unittest.TestCase):
    def test_tracing_tasks_validate(self):
        for task in ("trace-sdk", "trace-otel", "trace-strands"):
            path = harness.task_dir(task)
            harness.validate_task(path)
            self.assertEqual(harness.task_settings(path)["target"], "agent")
            self.assertIn(harness.SHARED / "trace-support", harness.digest_paths(path))

    def test_existing_tasks_default_to_project_targets(self):
        for task in ("chained-eval", "thread-llm-judge"):
            self.assertEqual(harness.task_settings(harness.task_dir(task))["target"], "project")

    def test_rejects_unsafe_shared_names_and_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            base = {"fixture_type": "none", "linux_cli_required": False, "verifier_enabled": False,
                    "target": "agent", "service_runs": PROCESS}
            for shared in ("../skills", "a/b", ".."):
                (path / "harness.json").write_text(json.dumps({**base, "shared": shared}))
                with self.assertRaisesRegex(ValueError, "shared"):
                    harness.task_settings(path)
            for rule in ("process", {"rule": "names", "names": []}, {"rule": "other"}):
                (path / "harness.json").write_text(json.dumps({**base, "shared": "trace-support", "service_runs": rule}))
                with self.assertRaisesRegex(ValueError, "service_runs"):
                    harness.task_settings(path)

    def test_agent_ids_fit_api_limits(self):
        run_id = str(uuid4())
        for task in ("trace-sdk", "trace-otel", "trace-strands"):
            for profile in harness.profiles():
                agent_id = harness.target_agent_id(task, profile, run_id)
                self.assertLessEqual(len(agent_id), 63)
        with self.assertRaises(ValueError):
            harness.target_agent_id("Trace_SDK", "full", run_id)

    def test_shared_app_does_not_replace_task_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "app"
            destination.mkdir()
            (destination / "assistant.py").write_text("override")
            harness.stage_shared_app(harness.SHARED / "trace-support" / "app", destination)
            self.assertEqual((destination / "assistant.py").read_text(), "override")
            self.assertTrue((destination / "tools_service.py").is_file())
            self.assertTrue((destination / "conversations.json").is_file())


if __name__ == "__main__":
    unittest.main()
