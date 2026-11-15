#!/usr/bin/env python3
"""Run the public skill eval profiles without publishing raw trial artifacts."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
HARNESS = EVALS / "harness.py"
CLEANUP = EVALS / "cleanup.py"


def _run(log_path: Path, script: Path, *args: str) -> int:
    with log_path.open("w") as stream:
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=REPO,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        ).returncode


def _summarize_report(report: dict) -> dict:
    """Keep only aggregate metrics safe to attach to a public CI run."""
    def metric(value: object) -> int | float | None:
        return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None

    local = report.get("local") or {}
    live = report.get("live") or {}
    validators = report.get("validators") or {}
    if report.get("task", "chained-eval") == "chained-eval":
        names = ("evaluator_pair", "chain_configuration", "insights_job")
    else:
        names = [name for name, result in validators.items() if isinstance(result, dict) and "passed" in result]
    checks = {name: bool((validators.get(name) or {}).get("passed")) for name in names}
    traces = live.get("traces") or []
    feedback = live.get("feedback_by_case") or []
    source_sha = report.get("source_sha")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", source_sha):
        source_sha = None
    return {
        "profile": report["profile"],
        "run_id": str(UUID(report["run_id"])),
        "source_sha": source_sha,
        "agent_cost_usd": metric(local.get("agent_cost_usd")),
        "agent_seconds": metric(local.get("agent_seconds")),
        "total_seconds": metric(local.get("total_seconds")),
        "tool_call_count": sum(metric(count) or 0 for count in (local.get("tool_calls") or {}).values()),
        "feedback_count": sum(len(case.get("feedback") or []) for case in feedback),
        "trace_count": len(traces),
        "claude_turn_count": sum(trace.get("claude_turn_count") or 0 for trace in traces),
        "trace_parentage_ok": bool(traces) and all(
            trace.get("claude_turn_count", 0) > 0 and trace.get("turns_nested_under_agent_start") is True
            for trace in traces
        ),
        "validators": checks,
    }


def _has_held_out_fixtures(task: str) -> bool:
    if not task or task in {".", ".."} or "/" in task or "\\" in task:
        raise ValueError("task must be a single directory name")
    settings = json.loads((EVALS / "tasks" / task / "harness.json").read_text())
    return settings.get("fixture_type") != "none"


def _write_summary(path: Path, task: str, results: list[dict]) -> None:
    document = {
        "schema_version": 1,
        "task": task,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "profiles": results,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="chained-eval")
    parser.add_argument("--profiles", nargs="+", default=["none", "full", "mcp-only"])
    parser.add_argument("--trace-project-id", required=True)
    parser.add_argument("--cli-bin", required=True)
    parser.add_argument("--tracing-plugin-dir", required=True)
    parser.add_argument("--wait-seconds", type=int, default=900)
    parser.add_argument("--summary-path", type=Path, required=True)
    args = parser.parse_args()

    log_dir = Path(tempfile.mkdtemp(prefix="harbor-skill-evals-", dir=os.environ.get("RUNNER_TEMP")))
    replay_needed = _has_held_out_fixtures(args.task)
    results: list[dict] = []
    failed = False
    required_checks = ("evaluator_pair", "chain_configuration", "insights_job")
    for profile in args.profiles:
        item: dict = {"profile": profile, "status": "preflight"}
        results.append(item)
        _write_summary(args.summary_path, args.task, results)
        print(f"{profile}: checking runner")
        base = ["--task", args.task, "--profile", profile]
        if _run(log_dir / f"{profile}-check.log", HARNESS, "check", *base, "--cli-bin", args.cli_bin):
            item["status"] = "preflight_failed"
            failed = True
            _write_summary(args.summary_path, args.task, results)
            continue

        print(f"{profile}: preparing isolated target")
        prepare_log = log_dir / f"{profile}-prepare.log"
        if _run(prepare_log, HARNESS, "prepare", *base, "--trace-project-id", args.trace_project_id):
            item["status"] = "prepare_failed"
            failed = True
            _write_summary(args.summary_path, args.task, results)
            continue
        try:
            prepared = json.loads(prepare_log.read_text().splitlines()[-1])
            run_id = str(UUID(prepared["run_id"]))
            target_project_id = str(UUID(prepared["target_project_id"]))
        except (IndexError, KeyError, ValueError, json.JSONDecodeError):
            item["status"] = "prepare_response_invalid"
            failed = True
            _write_summary(args.summary_path, args.task, results)
            continue
        item["run_id"] = run_id
        item["target_project_id"] = target_project_id
        _write_summary(args.summary_path, args.task, results)

        print(f"{profile}: running Harbor trial {run_id}")
        if _run(
            log_dir / f"{profile}-run.log", HARNESS, "run", run_id,
            "--cli-bin", args.cli_bin, "--tracing-plugin-dir", args.tracing_plugin_dir,
        ):
            item["status"] = "run_failed"
            failed = True
            _write_summary(args.summary_path, args.task, results)
            continue
        if replay_needed:
            print(f"{profile}: replaying held-out cases")
        if replay_needed and _run(log_dir / f"{profile}-replay.log", HARNESS, "replay", run_id):
            item["status"] = "replay_failed"
            failed = True
            _write_summary(args.summary_path, args.task, results)
            continue
        print(f"{profile}: collecting live report")
        if _run(
            log_dir / f"{profile}-report.log", HARNESS, "report", run_id,
            "--live", "--wait-seconds", str(args.wait_seconds),
        ):
            item["status"] = "report_failed"
            failed = True
            _write_summary(args.summary_path, args.task, results)
            continue
        try:
            report = json.loads((EVALS / "jobs" / run_id / "report.json").read_text())
            if report["run_id"] != run_id or report["profile"] != profile:
                raise ValueError("report identity mismatch")
            item.update(_summarize_report(report))
        except (FileNotFoundError, KeyError, ValueError, TypeError, json.JSONDecodeError):
            item["status"] = "report_invalid"
            failed = True
            _write_summary(args.summary_path, args.task, results)
            continue

        print(f"{profile}: removing recorded temporary target")
        if _run(log_dir / f"{profile}-cleanup.log", CLEANUP, "--run-id", run_id, "--execute"):
            item["status"] = "cleanup_failed"
            failed = True
        else:
            item["status"] = "completed"
        checks_ok = args.task != "chained-eval" or profile != "full" or all(
            item["validators"].get(name) is True for name in required_checks
        )
        if not item["trace_parentage_ok"] or not checks_ok:
            failed = True
            if item["status"] == "completed":
                item["status"] = "validation_failed"
        _write_summary(args.summary_path, args.task, results)
        print(f"{profile}: finished")

    _write_summary(args.summary_path, args.task, results)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
