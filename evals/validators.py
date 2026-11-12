"""Read-only checks for the online evaluation and tracing tasks."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from uuid import UUID

from langsmith.utils import LangSmithNotFoundError


def _api(ls, path: str):
    return ls.request_with_retries("GET", path).json()


def _cli_json(*args: str, workspace_id: str):
    cli = shutil.which("langsmith")
    if not cli:
        raise RuntimeError("langsmith CLI is required to inspect Insights resources")
    result = subprocess.run(
        [cli, *args, "--workspace", str(UUID(workspace_id)), "--format", "json"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"LangSmith Insights query failed ({args[0]} {args[1]})")
    return json.loads(result.stdout)


def _items(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("items", "configs", "jobs", "insights", "results"):
            if isinstance(value.get(key), list):
                return value[key]
    raise ValueError("unexpected LangSmith resource list shape")


def _feedback_key_filter(expression: str, key: str) -> bool:
    return bool(re.search(r"\beq\(\s*feedback_key\s*,\s*(['\"])" + re.escape(key) + r"\1\s*\)", expression))


def _score_one_filter(expression: str) -> bool:
    return bool(re.search(r"\beq\(\s*feedback_score\s*,\s*1(?:\.0)?\s*\)", expression))


def _decision_model_marker(rule: dict, ls) -> tuple[bool, str]:
    if rule.get("evaluator_type") == "decision_model":
        return True, "rule.evaluator_type"
    for evaluator in rule.get("evaluators") or []:
        structured = evaluator.get("structured") or {}
        model = structured.get("model") or {}
        for settings in (model, model.get("settings") or {}):
            if (settings.get("kwargs") or {}).get("decision_model") is True:
                return True, "rule.structured.model.decision_model"
        preset_id = structured.get("playground_settings_id")
        if preset_id:
            try:
                preset = _api(ls, f"/playground-settings/{UUID(preset_id)}")
            except LangSmithNotFoundError:
                continue
            if ((preset.get("settings") or {}).get("kwargs") or {}).get("decision_model") is True:
                return True, "playground_settings.decision_model"
    return False, "no decision-model marker"


def collect(data: dict, ls) -> dict:
    """Collect only IDs and relevant configuration; never persist prompts or secrets."""
    project_id = str(UUID(data["target_project_id"]))
    workspace_id = str(UUID(data["workspace_id"]))
    rules = _items(_api(ls, f"/runs/rules?session_id={project_id}"))
    rule_evidence = []
    for rule in rules:
        if rule.get("session_id") != project_id or rule.get("is_enabled") is not True:
            continue
        evaluator_id = rule.get("evaluator_id")
        if not evaluator_id:
            continue
        try:
            evaluator = _api(ls, f"/v1/platform/evaluators/{UUID(evaluator_id)}")
        except LangSmithNotFoundError:
            evaluator = None
        decision_model, marker = _decision_model_marker(rule, ls)
        rule_evidence.append({
            "rule_id": rule.get("id"),
            "evaluator_id": evaluator_id,
            "evaluator_type": rule.get("evaluator_type"),
            "evaluator_exists": evaluator is not None,
            "decision_model": decision_model,
            "type_evidence": marker,
            "feedback_keys": (evaluator or {}).get("feedback_keys") or [],
            "filter": rule.get("filter") or "",
            "trace_filter": rule.get("trace_filter") or "",
        })
    configs = _items(_cli_json("insights", "config", "list", "--project-id", project_id, workspace_id=workspace_id))
    jobs = _items(_cli_json("insights", "list", "--project-id", project_id, workspace_id=workspace_id))
    return {
        "rules": rule_evidence,
        "insights_configs": [
            {"id": c.get("id"), "project_id": c.get("project_id") or c.get("session_id"),
             "name": c.get("name"), "job_id": c.get("online_taxonomy_job_id"),
             "filter": (c.get("config") or {}).get("filter") or c.get("filter") or ""}
            for c in configs if isinstance(c, dict)
        ],
        "insights_jobs": [
            {"id": j.get("id"), "project_id": j.get("project_id") or j.get("session_id"),
             "config_id": j.get("config_id") or j.get("insights_config_id"),
             "name": j.get("name"), "status": j.get("status")}
            for j in jobs if isinstance(j, dict)
        ],
    }


def validate(evidence: dict, project_id: str) -> dict:
    rules = evidence["rules"]
    stage_ones = [r for r in rules if r["decision_model"] and r.get("evaluator_exists", True)]
    judges = [r for r in rules if not r["decision_model"] and r["evaluator_type"] == "llm" and r.get("evaluator_exists", True)]
    paired = len(stage_ones) == len(judges) == 1 and stage_ones[0]["evaluator_id"] != judges[0]["evaluator_id"]
    first_key = stage_ones[0]["feedback_keys"][0] if paired and len(stage_ones[0]["feedback_keys"]) == 1 else None
    judge_keys = judges[0]["feedback_keys"] if paired else []
    distinct_judge_keys = [key for key in judge_keys if key != first_key]
    chain = bool(paired and first_key and distinct_judge_keys and _feedback_key_filter(judges[0]["filter"], first_key))
    configs = [c for c in evidence["insights_configs"] if c["project_id"] in (None, project_id)]
    jobs = [j for j in evidence["insights_jobs"] if j["project_id"] in (None, project_id) and j["id"]]
    matches = [
        (c, j, key) for c in configs for j in jobs for key in distinct_judge_keys
        if c["id"] and (
            (c.get("job_id") and c["job_id"] == j["id"])
            or (j["config_id"] and j["config_id"] == c["id"])
            or (not c.get("job_id") and not j["config_id"] and c.get("name") and c["name"] == j.get("name"))
        )
        and chain and c["filter"].strip().startswith("and(")
        and _feedback_key_filter(c["filter"], key) and _score_one_filter(c["filter"])
    ]
    judge_key = matches[0][2] if matches else next(iter(distinct_judge_keys), None)
    return {
        "evaluator_pair": {"passed": paired, "decision_rule_id": stage_ones[0]["rule_id"] if paired else None,
                           "judge_rule_id": judges[0]["rule_id"] if paired else None},
        "chain_configuration": {"passed": chain, "decision_feedback_key": first_key, "judge_feedback_key": judge_key},
        "insights_job": {"passed": bool(matches), "config_id": matches[0][0]["id"] if matches else None,
                         "job_id": matches[0][1]["id"] if matches else None},
        "evidence": evidence,
    }


def collect_rules(data: dict, ls) -> dict:
    """Record online rule shape on the target project without prompts, models, or secrets."""
    project_id = str(UUID(data["target_project_id"]))
    rules = []
    for rule in _items(_api(ls, f"/runs/rules?session_id={project_id}")):
        if rule.get("session_id") != project_id:
            continue
        evaluator_id = rule.get("evaluator_id")
        try:
            evaluator = _api(ls, f"/v1/platform/evaluators/{UUID(evaluator_id)}") if evaluator_id else None
        except LangSmithNotFoundError:
            evaluator = None
        structured = [(e.get("structured") or {}) for e in rule.get("evaluators") or []]
        rules.append({
            "rule_id": rule.get("id"),
            "display_name": rule.get("display_name"),
            "is_enabled": rule.get("is_enabled"),
            "evaluator_id": evaluator_id,
            "evaluator_type": rule.get("evaluator_type"),
            "decision_model": _decision_model_marker(rule, ls)[0],
            "group_by": rule.get("group_by"),
            "thread_fields": {k: v for k, v in rule.items() if ("thread" in k or "group" in k) and not isinstance(v, (dict, list))},
            "sampling_rate": rule.get("sampling_rate"),
            "filter": rule.get("filter") or "",
            "trace_filter": rule.get("trace_filter") or "",
            "variable_mapping": [s.get("variable_mapping") for s in structured],
            "schema_keys": [sorted(((s.get("schema") or {}).get("properties") or {}).keys()) for s in structured],
            "feedback_keys": (evaluator or {}).get("feedback_keys") or [],
            "code_evaluators": len(rule.get("code_evaluators") or []),
        })
    session = _api(ls, f"/sessions/{project_id}")
    return {"rules": rules, "project_idle_fields": {k: v for k, v in session.items() if "idle" in k}}


EXECUTION_GAP_SECONDS = 10


def _digest(value) -> str | None:
    if value in (None, ""):
        return None
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


def _run_record(run) -> dict:
    metadata = (run.extra or {}).get("metadata") or {}
    return {
        "id": str(run.id),
        "trace_id": str(run.trace_id),
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "name": run.name,
        "run_type": run.run_type,
        "start_time": run.start_time.isoformat() if run.start_time else None,
        "thread": _digest(metadata.get("thread_id", metadata.get("session_id"))),
        "process": _digest(metadata.get("otel.resource.service.instance.id")),
    }


def collect_traces(data: dict, ls) -> dict:
    """Record run structure in the target agent's environments; never inputs, outputs, or raw metadata values."""
    agent_id = data["target_agent_id"]
    agent = _api(ls, f"/api/v1/agents/{agent_id}")
    if agent.get("id") != agent_id or str(UUID(agent["agent_uuid"])) != data["target_agent_uuid"]:
        raise RuntimeError("target agent identity does not match the manifest")
    environments, runs = {}, {}
    for environment in agent.get("environments") or []:
        name = environment["environment"]
        records = [_run_record(run) for run in ls.list_runs(project_id=str(UUID(environment["tracer_session_id"])))]
        runs[name] = records
        environments[name] = {"runs": len(records), "roots": sum(r["parent_run_id"] is None for r in records)}
    target_runs = sum(1 for _ in ls.list_runs(project_id=str(UUID(data["target_project_id"])), limit=100))
    return {"agent_id": agent_id, "environments": environments, "target_project_runs": target_runs, "runs": runs}


def _executions(roots: list[dict]) -> list[list[dict]]:
    ordered = sorted(roots, key=lambda r: r["start_time"] or "")
    groups: list[list[dict]] = []
    previous = None
    for root in ordered:
        started = datetime.fromisoformat(root["start_time"]) if root["start_time"] else None
        if not groups or started is None or previous is None or (started - previous).total_seconds() > EXECUTION_GAP_SECONDS:
            groups.append([])
        groups[-1].append(root)
        previous = started
    return groups


def validate_traces(evidence: dict, expected: dict, rule: dict) -> dict:
    environment = expected["agent_environment"]
    runs = evidence["runs"].get(environment, [])
    others = {name: env["runs"] for name, env in evidence["environments"].items() if name != environment}
    destination = bool(runs) and not any(others.values()) and evidence["target_project_runs"] == 0

    run_ids = {r["id"] for r in runs}
    orphans = [r for r in runs if r["parent_run_id"] and r["parent_run_id"] not in run_ids]
    executions = _executions([r for r in runs if r["parent_run_id"] is None])
    latest = executions[-1] if executions else []
    assistant = Counter(r["process"] for r in latest).most_common(1)[0][0] if latest else None

    def from_service(run: dict) -> bool:
        if rule["rule"] == "names":
            return run["name"] in rule["names"]
        return run["process"] is not None and assistant is not None and run["process"] != assistant

    turn_roots = [r for r in latest if not from_service(r)]
    service_roots = [r for r in latest if from_service(r)]
    traces = {r["trace_id"] for r in turn_roots}
    children = [r for r in runs if r["trace_id"] in traces and r["parent_run_id"] is not None]
    service_children = [r for r in children if from_service(r)]
    linked_traces = {r["trace_id"] for r in service_children}

    per_thread = Counter(r["thread"] for r in turn_roots)
    threads = (
        all(r["thread"] for r in turn_roots)
        and sorted(per_thread.values()) == sorted(expected["turns_per_thread"])
    )

    def coverage(items: list[dict]) -> float | None:
        return round(sum(bool(r["thread"]) for r in items) / len(items), 3) if items else None

    return {
        "destination": {"passed": destination, "environment_runs": len(runs), "other_environment_runs": others,
                        "target_project_runs": evidence["target_project_runs"]},
        "turns_arrived": {"passed": len(turn_roots) == expected["turns"], "turn_roots": len(turn_roots),
                          "expected": expected["turns"], "executions_observed": len(executions)},
        "threads": {"passed": threads, "distinct_threads": len(per_thread), "turns_per_thread": sorted(per_thread.values()),
                    "child_coverage": coverage([r for r in children if not from_service(r)]),
                    "service_coverage": coverage(service_children)},
        "distributed_tracing": {"passed": len(linked_traces) == expected["service_turns"] and not service_roots and not orphans,
                                "linked_traces": len(linked_traces), "expected": expected["service_turns"],
                                "service_roots": len(service_roots), "orphan_runs": len(orphans),
                                "rule": rule["rule"]},
        "run_names": sorted({r["name"] for r in runs}),
        "evidence": evidence,
    }
