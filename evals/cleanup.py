#!/usr/bin/env python3
"""Delete only recorded temporary task projects from Harbor eval runs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

from harness import JOBS, client, load_manifest, manifest_path, save_manifest


def canonical_uuid(value: str) -> str:
    parsed = str(UUID(value))
    if parsed != value:
        raise ValueError(f"noncanonical UUID: {value}")
    return parsed


def selected_run_ids(run_ids: list[str], all_runs: bool) -> list[str]:
    if all_runs == bool(run_ids):
        raise ValueError("select run IDs or --all")
    if all_runs:
        return sorted(path.parent.name for path in JOBS.glob("*/manifest.json"))
    return list(dict.fromkeys(run_ids))


def validate_manifest(run_id: str, data: dict) -> None:
    canonical_uuid(run_id)
    target_id = canonical_uuid(data["target_project_id"])
    trace_id = canonical_uuid(data["trace_project_id"])
    canonical_uuid(data["workspace_id"])
    if target_id == trace_id:
        raise ValueError(f"{run_id}: target and shared trace project IDs are identical")
    expected_name = f"lcskills-eval-{data['task']}-{data['profile']}-{run_id[:8]}"
    if data["target_project_name"] != expected_name:
        raise ValueError(f"{run_id}: target project name does not match run identity")
    if data["status"] == "running":
        raise ValueError(f"{run_id}: trial is still running")
    if data.get("held_out_run_ids"):
        report_path = manifest_path(run_id).with_name("report.json")
        report = json.loads(report_path.read_text())
        if (
            report.get("run_id") != run_id
            or report.get("target_project_id") != target_id
            or report.get("trace_project_id") != trace_id
            or report.get("held_out_count") != len(data["held_out_run_ids"])
            or not isinstance(report.get("live"), dict)
            or not report.get("inspected_at")
        ):
            raise ValueError(f"{run_id}: a matching live report is required before cleanup")
        replayed_at = data.get("replayed_at")
        if replayed_at and datetime.fromisoformat(report["inspected_at"]) < datetime.fromisoformat(replayed_at):
            raise ValueError(f"{run_id}: live report predates the fresh cases")


def cleanup_runs(run_ids: list[str], all_runs: bool = False, execute: bool = False) -> None:
    selected = selected_run_ids(run_ids, all_runs)
    pending = []
    for run_id in selected:
        data = load_manifest(run_id)
        validate_manifest(run_id, data)
        if not data.get("target_project_deleted"):
            pending.append(data)
    if not pending:
        print("no temporary target projects to delete")
        return
    for data in pending:
        print(f"{data['run_id']}: {data['target_project_name']} ({data['target_project_id']})")
    if not execute:
        print("dry run; pass --execute to delete these exact target projects")
        return
    ls = client()
    for data in pending:
        run_id = data["run_id"]
        if data["workspace_id"] != str(UUID(ls.workspace_id)):
            raise RuntimeError(f"{run_id}: workspace does not match manifest")
        project = ls.read_project(project_id=data["target_project_id"])
        if (
            str(project.id) != data["target_project_id"]
            or project.name != data["target_project_name"]
            or project.description != f"Isolated Harbor task target for {run_id}"
        ):
            raise RuntimeError(f"{run_id}: live target project identity mismatch")
        ls.delete_project(project_id=data["target_project_id"])
        data["target_project_deleted"] = True
        save_manifest(data)
        print(f"{run_id}: deleted target project; shared traces and local artifacts preserved")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--run-id", action="append", dest="run_ids")
    selection.add_argument("--all", action="store_true", dest="all_runs")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        cleanup_runs(args.run_ids or [], args.all_runs, args.execute)
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
