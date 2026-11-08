#!/usr/bin/env python3
"""Prepare, run, inspect, and clean up Harbor skill evaluations.

Run with the Python from the pinned Harbor tool environment. Credentials must
already be present in the process environment; this module never opens .env.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic, sleep
from uuid import UUID, uuid4

from langsmith import Client


EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
TASKS = EVALS / "tasks"
JOBS = EVALS / "jobs"
STAGE = EVALS / ".stage"
MCP_SERVERS = [
    {"name": "langchain-docs", "transport": "streamable-http", "url": "https://docs.langchain.com/mcp"},
    {"name": "langchain-reference", "transport": "streamable-http", "url": "https://reference.langchain.com/mcp"},
]


def linux_cli_path(value: str | None) -> Path:
    candidate = value or os.environ.get("LANGSMITH_LINUX_CLI")
    if not candidate:
        raise RuntimeError("set LANGSMITH_LINUX_CLI or pass --cli-bin with a Linux LangSmith CLI binary")
    return Path(candidate).expanduser().resolve()


def profiles() -> dict:
    configs = json.loads((EVALS / "profiles.json").read_text())
    if not isinstance(configs, dict):
        raise ValueError("profiles.json must be an object")
    return configs


def profile_config(name: str) -> dict:
    config = profiles().get(name)
    if not isinstance(config, dict):
        raise ValueError(f"unknown profile: {name}")
    skills = config.get("skills")
    if skills != "*" and (not isinstance(skills, list) or any(not isinstance(x, str) or not x or "/" in x or "\\" in x for x in skills)):
        raise ValueError(f"invalid skills for profile: {name}")
    for key in ("agent", "model", "agent_version", "max_budget_usd"):
        if not isinstance(config.get(key), str) or not config[key]:
            raise ValueError(f"profile {name} requires {key}")
    if not isinstance(config.get("documentation_mcp"), bool):
        raise ValueError(f"profile {name} requires documentation_mcp boolean")
    return config


def task_dir(name: str) -> Path:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("task must be a single directory name")
    path = TASKS / name
    if not (path / "task.toml").is_file():
        raise FileNotFoundError(f"task.toml missing for {name}")
    return path


def validate_task(path: Path) -> None:
    for rel in ("Task.md", "instruction.md", "task.toml", "harness.json"):
        if not (path / rel).is_file():
            raise FileNotFoundError(path / rel)
    if not (path / "environment" / "Dockerfile").is_file() and not (path / "environment" / "docker-compose.yaml").is_file():
        raise FileNotFoundError("task requires an environment Dockerfile or docker-compose.yaml")
    config = tomllib.loads((path / "task.toml").read_text())
    if config.get("schema_version") != "1.3":
        raise ValueError("expected Harbor task schema 1.3")
    settings = task_settings(path)
    if settings["verifier_enabled"] and not (path / "tests" / "test.sh").is_file():
        raise FileNotFoundError("scored task requires tests/test.sh")
    if settings["fixture_type"] == "none":
        return
    cases = json.loads((path / "fixtures.json").read_text())
    for phase in ("seed", "held_out"):
        items = cases.get(phase)
        if not isinstance(items, list) or not items:
            raise ValueError(f"fixtures.json requires nonempty {phase}")
        if settings["fixture_type"] == "synthetic_threads":
            if any(
                not isinstance(thread, dict)
                or not isinstance(thread.get("turns"), list)
                or not thread["turns"]
                or (phase == "held_out" and path.name == "thread-llm-judge"
                    and type(thread.get("expected_resolved")) is not bool)
                for thread in items
            ):
                raise ValueError(f"invalid {phase} thread")
            items = [turn for thread in items for turn in thread["turns"]]
        if any(not isinstance(x, list) or len(x) != 2 or not all(isinstance(v, str) for v in x) for x in items):
            raise ValueError(f"invalid {phase} conversation")


def task_settings(path: Path) -> dict:
    settings = json.loads((path / "harness.json").read_text())
    if settings.get("fixture_type") not in {"none", "synthetic_conversations", "synthetic_threads"}:
        raise ValueError("unsupported fixture_type")
    if not isinstance(settings.get("verifier_enabled"), bool):
        raise ValueError("verifier_enabled must be a boolean")
    if not isinstance(settings.get("linux_cli_required"), bool):
        raise ValueError("linux_cli_required must be a boolean")
    return settings


def client() -> Client:
    key = os.environ.get("LANGSMITH_API_KEY")
    workspace = os.environ.get("WORKSPACE_ID")
    if not key or not workspace:
        raise RuntimeError("LANGSMITH_API_KEY and WORKSPACE_ID must be set in the environment")
    return Client(api_key=key, workspace_id=workspace)


def git_sha() -> str:
    result = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def content_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for root in paths:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            digest.update(str(path.relative_to(REPO)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def manifest_path(run_id: str) -> Path:
    UUID(run_id)
    return JOBS / run_id / "manifest.json"


def load_manifest(run_id: str) -> dict:
    path = manifest_path(run_id)
    data = json.loads(path.read_text())
    if data.get("run_id") != run_id or data.get("schema_version") != 1:
        raise ValueError("invalid run manifest")
    return data


def save_manifest(data: dict) -> None:
    path = manifest_path(data["run_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def emit_cases(ls: Client, project_name: str, items: list[list[str]], phase: str, run_id: str) -> list[str]:
    now = datetime.now(timezone.utc)
    ids: list[str] = []
    for index, (question, answer) in enumerate(items, start=1):
        run_id_for_case = uuid4()
        ls.create_run(
            name="support_conversation",
            run_type="chain",
            id=run_id_for_case,
            project_name=project_name,
            start_time=now,
            end_time=now,
            inputs={"messages": [{"role": "user", "content": question}]},
            outputs={"messages": [{"role": "assistant", "content": answer}]},
            extra={"metadata": {"thread_id": str(uuid4()), "fixture_phase": phase, "case_index": index, "eval_run_id": run_id}},
        )
        ids.append(str(run_id_for_case))
    ls.flush()
    return ids


def emit_threads(ls: Client, project_name: str, threads: list[dict], phase: str, run_id: str) -> list[str]:
    """Emit one root run per turn sharing a thread_id; return each thread's last-turn run ID."""
    now = datetime.now(timezone.utc)
    last_ids: list[str] = []
    for index, thread in enumerate(threads, start=1):
        thread_id = str(uuid4())
        turns = thread["turns"]
        history: list[dict] = []
        for turn_index, (question, answer) in enumerate(turns):
            started = now - timedelta(seconds=20 * (len(turns) - 1 - turn_index))
            history.append({"role": "user", "content": question})
            inputs = {"messages": list(history)}
            history.append({"role": "assistant", "content": answer})
            turn_run_id = uuid4()
            ls.create_run(
                name="support_conversation",
                run_type="chain",
                id=turn_run_id,
                project_name=project_name,
                start_time=started,
                end_time=started + timedelta(seconds=2),
                inputs=inputs,
                outputs={"messages": list(history)},
                extra={"metadata": {"thread_id": thread_id, "fixture_phase": phase, "case_index": index,
                                    "turn_index": turn_index, "eval_run_id": run_id}},
            )
        last_ids.append(str(turn_run_id))
    ls.flush()
    return last_ids


def emit_fixtures(ls: Client, task: str, project_name: str, phase: str, run_id: str) -> list[str]:
    path = task_dir(task)
    fixture_type = task_settings(path)["fixture_type"]
    items = json.loads((path / "fixtures.json").read_text())[phase]
    label = phase.replace("_", "-")
    if fixture_type == "synthetic_threads":
        return emit_threads(ls, project_name, items, label, run_id)
    return emit_cases(ls, project_name, items, label, run_id)


def prepare(args: argparse.Namespace) -> None:
    path = task_dir(args.task)
    validate_task(path)
    profile_config(args.profile)
    shared_project_id = str(UUID(args.trace_project_id))
    run_id = str(uuid4())
    ls = client()
    shared = ls.read_project(project_id=shared_project_id)
    if getattr(shared, "reference_dataset_id", None) is None:
        raise RuntimeError("shared project must be linked to a LangSmith dataset")
    dataset = ls.read_dataset(dataset_id=shared.reference_dataset_id)
    target_name = f"lcskills-eval-{args.task}-{args.profile}-{run_id[:8]}"
    target = ls.create_project(
        target_name,
        description=f"Isolated Harbor task target for {run_id}",
        reference_dataset_id=shared.reference_dataset_id,
    )
    data = {
        "schema_version": 1,
        "run_id": run_id,
        "task": args.task,
        "profile": args.profile,
        "profile_config": profile_config(args.profile),
        "source_sha": git_sha(),
        "content_digest": content_digest([REPO / "skills", path]),
        "trace_project_id": shared_project_id,
        "trace_project_name": shared.name,
        "dataset_id": str(shared.reference_dataset_id),
        "dataset_name": dataset.name,
        "target_project_id": str(target.id),
        "target_project_name": target_name,
        "workspace_id": os.environ["WORKSPACE_ID"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed_run_ids": [],
        "held_out_run_ids": [],
        "harbor_job_dir": None,
        "status": "preparing",
    }
    save_manifest(data)
    if task_settings(path)["fixture_type"] != "none":
        data["seed_run_ids"] = emit_fixtures(ls, args.task, target_name, "seed", run_id)
    data["status"] = "prepared"
    save_manifest(data)
    print(json.dumps({"run_id": run_id, "task": args.task, "profile": args.profile, "target_project_id": str(target.id)}))


def stage_run(data: dict, cli_bin: Path) -> Path:
    settings = task_settings(task_dir(data["task"]))
    if settings["linux_cli_required"] and not cli_bin.is_file():
        raise FileNotFoundError(f"Linux LangSmith CLI binary missing: {cli_bin}")
    root = STAGE / data["run_id"]
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    staged_task = root / "task"
    shutil.copytree(task_dir(data["task"]), staged_task)
    if settings["linux_cli_required"]:
        shutil.copy2(cli_bin, staged_task / "environment" / "langsmith")
    profile = profile_config(data["profile"])
    selected = profile["skills"]
    if selected == "*":
        selected = [p.name for p in (REPO / "skills").iterdir() if p.is_dir()]
    if selected:
        skills_root = root / "skills"
        skills_root.mkdir()
        for name in selected:
            if name in {".", ".."}:
                raise ValueError(f"invalid skill name: {name}")
            source = REPO / "skills" / name
            if not source.is_dir():
                raise FileNotFoundError(source)
            shutil.copytree(source, skills_root / name)
        for skill in skills_root.iterdir():
            if skill.is_dir() and not (skill / "SKILL.md").is_file():
                raise RuntimeError(f"incomplete skill directory: {skill.name}")
    agent = {
        "name": profile["agent"],
        "model_name": profile["model"],
        "extra_allowed_hosts": ["gateway.smith.langchain.com", "api.smith.langchain.com", "docs.langchain.com", "reference.langchain.com"],
        "kwargs": {"version": profile["agent_version"], "max_budget_usd": profile["max_budget_usd"]},
        "env": {"TARGET_PROJECT_ID": data["target_project_id"], "LANGSMITH_WORKSPACE_ID": data["workspace_id"]},
    }
    if selected:
        agent["skills"] = [str(root / "skills")]
    if profile["documentation_mcp"]:
        agent["mcp_servers"] = MCP_SERVERS
    config = {
        "job_name": f"lcskills-{data['task']}-{data['profile']}-{data['run_id'][:8]}",
        "jobs_dir": str(JOBS / data["run_id"] / "harbor"),
        "n_attempts": 1,
        "n_concurrent_trials": 1,
        "environment": {"import_path": "allowlist:AllowlistedLangSmithEnvironment"},
        "verifier": {"disable": not settings["verifier_enabled"]},
        "agents": [agent],
        "tasks": [{"path": str(staged_task)}],
    }
    config_path = root / "job.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    return config_path


def run(args: argparse.Namespace) -> None:
    data = load_manifest(args.run_id)
    if data["status"] not in {"prepared", "failed"}:
        raise RuntimeError(f"run status is {data['status']}; refusing duplicate Harbor run")
    if data["source_sha"] != git_sha():
        raise RuntimeError("source commit changed since prepare; create a new run")
    if data["content_digest"] != content_digest([REPO / "skills", task_dir(data["task"])]):
        raise RuntimeError("task or skill content changed since prepare; create a new run")
    if data["profile_config"] != profile_config(data["profile"]):
        raise RuntimeError("profile changed since prepare; create a new run")
    plugin_dir = Path(args.tracing_plugin_dir).expanduser().resolve()
    for rel in (".claude-plugin/plugin.json", "hooks/hooks.json"):
        if not (plugin_dir / rel).is_file():
            raise FileNotFoundError(plugin_dir / rel)
    config_path = stage_run(data, linux_cli_path(args.cli_bin))
    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = str(EVALS) + os.pathsep + child_env.get("PYTHONPATH", "")
    child_env["LANGSMITH_WORKSPACE_ID"] = data["workspace_id"]
    child_env["EVAL_TRACE_PROJECT_ID"] = data["trace_project_id"]
    child_env["EVAL_RUN_ID"] = data["run_id"]
    child_env["EVAL_TASK"] = data["task"]
    child_env["EVAL_PROFILE"] = data["profile"]
    child_env["EVAL_SKILL_SHA"] = data["source_sha"]
    child_env["EVAL_ROOT_RUNS_FILE"] = str(JOBS / data["run_id"] / "root_runs.jsonl")
    child_env["CC_LANGSMITH_PLUGIN_DIR"] = str(plugin_dir)
    child_env["CC_LANGSMITH_DEBUG"] = "true"
    argv = [
        "harbor", "run", "--config", str(config_path),
        "--yes", "--agent-setup-timeout-multiplier", "3",
        "--environment-build-timeout-multiplier", "5",
        "--plugin", "shared_project_plugin:SharedProjectPlugin",
        "--pk", f"dataset_name={data['dataset_name']}",
        "--pk", "fail_fast=true",
    ]
    if args.env_file:
        argv += ["--env-file", str(Path(args.env_file).expanduser().resolve())]
    if args.print_config:
        argv.append("--print-config")
    else:
        data["status"] = "running"
        save_manifest(data)
    completed = subprocess.run(argv, env=child_env, cwd=REPO)
    if args.print_config:
        print(f"config check exit: {completed.returncode}")
        return
    job_dirs = sorted((JOBS / data["run_id"] / "harbor").glob("*/"), key=lambda p: p.stat().st_mtime)
    data["harbor_job_dir"] = str(job_dirs[-1]) if job_dirs else None
    data["harbor_exit_code"] = completed.returncode
    data["status"] = "completed" if completed.returncode == 0 else "failed"
    save_manifest(data)
    print(json.dumps({"run_id": data["run_id"], "status": data["status"], "harbor_job_dir": data["harbor_job_dir"]}))
    if completed.returncode:
        raise SystemExit(completed.returncode)


def replay(args: argparse.Namespace) -> None:
    data = load_manifest(args.run_id)
    if data["status"] != "completed" or data["held_out_run_ids"]:
        raise RuntimeError("replay requires a completed run with no prior held-out emission")
    if task_settings(task_dir(data["task"]))["fixture_type"] == "none":
        raise RuntimeError("this task has no held-out synthetic conversations")
    data["held_out_run_ids"] = emit_fixtures(client(), data["task"], data["target_project_name"], "held_out", data["run_id"])
    data["replayed_at"] = datetime.now(timezone.utc).isoformat()
    save_manifest(data)
    print(f"emitted {len(data['held_out_run_ids'])} held-out conversations for {data['run_id']}")


def _seconds_between(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    return round((datetime.fromisoformat(end.replace("Z", "+00:00")) - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds(), 3)


def local_result(data: dict) -> dict:
    job_dir = data.get("harbor_job_dir")
    if not job_dir:
        return {"available": False}
    trials = sorted(Path(job_dir).glob("*/result.json"))
    if not trials:
        return {"available": False}
    trial_dir = trials[0].parent
    result = json.loads(trials[0].read_text())
    agent_result = result.get("agent_result") or {}
    execution = result.get("agent_execution") or {}
    out = {
        "available": True,
        "trial_dir": str(trial_dir),
        "agent_seconds": _seconds_between(execution.get("started_at"), execution.get("finished_at")),
        "total_seconds": _seconds_between(result.get("started_at"), result.get("finished_at")),
        "agent_cost_usd": agent_result.get("cost_usd"),
        "input_tokens": agent_result.get("n_input_tokens"),
        "output_tokens": agent_result.get("n_output_tokens"),
        "cache_tokens": agent_result.get("n_cache_tokens"),
        "tool_calls": {},
        "skills_invoked": [],
    }
    trajectory = trial_dir / "agent" / "trajectory.json"
    if trajectory.is_file():
        metrics = json.loads(trajectory.read_text()).get("final_metrics") or {}
        out["steps"] = metrics.get("total_steps")
    transcript = trial_dir / "agent" / "claude-code.txt"
    if transcript.is_file():
        for line in transcript.read_text(errors="replace").splitlines():
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("type") != "assistant":
                continue
            for item in (message.get("message") or {}).get("content", []):
                if not isinstance(item, dict) or item.get("type") != "tool_use":
                    continue
                name = item.get("name")
                if not isinstance(name, str):
                    continue
                out["tool_calls"][name] = out["tool_calls"].get(name, 0) + 1
                if name == "Skill":
                    skill = (item.get("input") or {}).get("skill")
                    if isinstance(skill, str) and skill not in out["skills_invoked"]:
                        out["skills_invoked"].append(skill)
    return out


def live_result(data: dict, ls: Client) -> dict:
    feedback_by_case: list[dict] = []
    for index, run_id in enumerate(data["held_out_run_ids"], start=1):
        feedback = []
        for item in ls.list_feedback(run_ids=[run_id]):
            feedback.append({
                "key": item.key,
                "score": item.score,
                "value": str(item.value)[:200] if item.value is not None else None,
                "created_at": str(item.created_at) if item.created_at else None,
            })
        feedback_by_case.append({"case_index": index, "run_id": run_id, "feedback": feedback})

    roots = []
    root_file = manifest_path(data["run_id"]).with_name("root_runs.jsonl")
    if root_file.is_file():
        for line in root_file.read_text().splitlines():
            root_id = json.loads(line)["run_id"]
            run = ls.read_run(root_id)
            metadata = (run.extra or {}).get("metadata") or {}
            if metadata.get("eval_run_id") != data["run_id"]:
                raise RuntimeError("shared project root metadata mismatch")
            roots.append(run)
    traces = []
    for root in roots:
        descendants = list(ls.list_runs(project_id=data["trace_project_id"], trace_id=root.id))
        by_id = {str(run.id): run for run in descendants}
        turn_ids = [str(run.id) for run in descendants if run.name == "Claude Code Turn"]
        agent_ids = {str(run.id) for run in descendants if run.name in {"agent-start", "agent_start"}}
        def under_agent(run_id: str) -> bool:
            seen: set[str] = set()
            while run_id in by_id and run_id not in seen:
                seen.add(run_id)
                parent = by_id[run_id].parent_run_id
                if parent is None:
                    return False
                run_id = str(parent)
                if run_id in agent_ids:
                    return True
            return False
        traces.append({
            "root_run_id": str(root.id),
            "child_count": len(descendants) - 1,
            "claude_turn_count": len(turn_ids),
            "turns_nested_under_agent_start": all(under_agent(run_id) for run_id in turn_ids) if turn_ids else False,
            "llm_span_count": sum(run.run_type == "llm" for run in descendants),
            "tool_span_count": sum(run.run_type == "tool" for run in descendants),
        })
    return {"feedback_by_case": feedback_by_case, "traces": traces}


def report(args: argparse.Namespace) -> None:
    data = load_manifest(args.run_id)
    summary = {
        "run_id": data["run_id"],
        "task": data["task"],
        "profile": data["profile"],
        "source_sha": data["source_sha"],
        "content_digest": data.get("content_digest"),
        "status": data["status"],
        "target_project_id": data["target_project_id"],
        "trace_project_id": data["trace_project_id"],
        "seed_count": len(data["seed_run_ids"]),
        "held_out_count": len(data["held_out_run_ids"]),
        "local": local_result(data),
    }
    if args.live:
        ls = client()
        deadline = monotonic() + args.wait_seconds
        while True:
            summary["live"] = live_result(data, ls)
            if monotonic() >= deadline:
                break
            sleep(min(args.poll_seconds, max(0, deadline - monotonic())))
        if data["task"] == "chained-eval":
            from validators import collect, validate

            summary["validators"] = validate(collect(data, ls), data["target_project_id"])
        if data["task"] == "thread-llm-judge":
            from validators import collect_rules

            summary["validators"] = {"evidence": collect_rules(data, ls)}
            expected = [t["expected_resolved"] for t in json.loads((task_dir(data["task"]) / "fixtures.json").read_text())["held_out"]]
            for case in summary["live"]["feedback_by_case"]:
                case["expected_resolved"] = expected[case["case_index"] - 1]
        summary["inspected_at"] = datetime.now(timezone.utc).isoformat()
    report_path = manifest_path(args.run_id).with_name("report.json")
    report_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


def cleanup(args: argparse.Namespace) -> None:
    from cleanup import cleanup_runs

    cleanup_runs([args.run_id], execute=args.execute)


def check(args: argparse.Namespace) -> None:
    path = task_dir(args.task)
    validate_task(path)
    from importlib.metadata import version
    if version("harbor") != "0.18.0" or version("harbor-langsmith") != "0.2.0":
        raise RuntimeError("this harness requires Harbor 0.18.0 and harbor-langsmith 0.2.0")
    import harbor.agents.installed.claude_code as claude_adapter
    adapter_source = Path(claude_adapter.__file__).read_text()
    for marker in ("CC_LANGSMITH_PLUGIN_DIR", "CC_LANGSMITH_PARENT_DOTTED_ORDER", "CC_LANGSMITH_PROJECT"):
        if marker not in adapter_source:
            raise RuntimeError(f"installed Harbor Claude adapter lacks {marker}; apply the maintained patch")
    placeholder = str(UUID(int=0))
    data = {
        "run_id": placeholder, "task": args.task, "profile": args.profile,
        "target_project_id": placeholder, "workspace_id": placeholder,
    }
    config_path = stage_run(data, linux_cli_path(args.cli_bin))
    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = str(EVALS) + os.pathsep + child_env.get("PYTHONPATH", "")
    completed = subprocess.run(["harbor", "run", "--config", str(config_path), "--print-config"], cwd=REPO, env=child_env)
    if completed.returncode:
        raise RuntimeError("Harbor rejected the resolved job config")
    print(f"preflight passed: {args.task}/{args.profile}")


def bootstrap(args: argparse.Namespace) -> None:
    ls = client()
    if ls.has_dataset(dataset_name=args.dataset_name):
        dataset = ls.read_dataset(dataset_name=args.dataset_name)
    else:
        dataset = ls.create_dataset(args.dataset_name, description="Harbor skill evaluation task examples")
    if ls.has_project(args.project_name):
        project = ls.read_project(project_name=args.project_name)
    else:
        project = ls.create_project(
            args.project_name,
            description="Shared Harbor and granular agent traces for skill evaluations",
            reference_dataset_id=dataset.id,
            metadata={"ls_runner": "harbor", "suite": "langchain-skills"},
        )
    if str(project.reference_dataset_id) != str(dataset.id):
        raise RuntimeError("project already exists but references a different dataset")
    print(json.dumps({"project_id": str(project.id), "project_name": project.name, "dataset_id": str(dataset.id), "dataset_name": dataset.name}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--task", required=True)
    p.add_argument("--profile", choices=sorted(profiles()), required=True)
    p.add_argument("--trace-project-id", required=True)
    p.set_defaults(action=prepare)
    p = sub.add_parser("check")
    p.add_argument("--task", required=True)
    p.add_argument("--profile", choices=sorted(profiles()), required=True)
    p.add_argument("--cli-bin")
    p.set_defaults(action=check)
    p = sub.add_parser("bootstrap")
    p.add_argument("--project-name", required=True)
    p.add_argument("--dataset-name", required=True)
    p.set_defaults(action=bootstrap)
    p = sub.add_parser("run")
    p.add_argument("run_id")
    p.add_argument("--tracing-plugin-dir", required=True)
    p.add_argument("--cli-bin")
    p.add_argument("--env-file")
    p.add_argument("--print-config", action="store_true")
    p.set_defaults(action=run)
    p = sub.add_parser("replay")
    p.add_argument("run_id")
    p.set_defaults(action=replay)
    p = sub.add_parser("cleanup")
    p.add_argument("run_id")
    p.add_argument("--execute", action="store_true")
    p.set_defaults(action=cleanup)
    p = sub.add_parser("report")
    p.add_argument("run_id")
    p.add_argument("--live", action="store_true")
    p.add_argument("--wait-seconds", type=int, default=0)
    p.add_argument("--poll-seconds", type=int, default=20)
    p.set_defaults(action=report)
    args = parser.parse_args()
    try:
        args.action(args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
