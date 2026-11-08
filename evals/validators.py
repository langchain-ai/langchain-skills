"""Read-only configuration checks for the chained online evaluation task."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
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
