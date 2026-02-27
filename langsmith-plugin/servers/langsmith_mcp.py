#!/usr/bin/env python3
"""LangSmith MCP Server - Exposes LangSmith query tools to Claude Code.

Wraps trace, dataset, and experiment queries as MCP tools so Claude
can call them directly without needing to know script paths.

Requirements: mcp, langsmith, python-dotenv
"""

import json
import os
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv
from langsmith import Client
from mcp.server.fastmcp import FastMCP

load_dotenv(override=False)

mcp = FastMCP("langsmith-tools")


# ============================================================================
# Helpers
# ============================================================================


def _get_client() -> Client:
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        raise ValueError(
            "LANGSMITH_API_KEY not set. "
            "Get one at https://smith.langchain.com/settings"
        )
    return Client(api_key=api_key)


def _calc_duration_ms(run) -> int | None:
    if (
        hasattr(run, "start_time")
        and hasattr(run, "end_time")
        and run.start_time
        and run.end_time
    ):
        return int((run.end_time - run.start_time).total_seconds() * 1000)
    return None


def _extract_run(run, include_metadata=False, include_io=False) -> dict:
    trace_id = str(run.trace_id) if hasattr(run, "trace_id") else str(run.id)
    data = {
        "run_id": str(run.id),
        "trace_id": trace_id,
        "name": run.name,
        "run_type": run.run_type,
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "start_time": run.start_time.isoformat()
        if hasattr(run, "start_time") and run.start_time
        else None,
        "end_time": run.end_time.isoformat()
        if hasattr(run, "end_time") and run.end_time
        else None,
    }

    if include_metadata:
        data.update(
            {
                "status": getattr(run, "status", None),
                "duration_ms": _calc_duration_ms(run),
                "token_usage": {
                    "prompt_tokens": getattr(run, "prompt_tokens", None),
                    "completion_tokens": getattr(run, "completion_tokens", None),
                    "total_tokens": getattr(run, "total_tokens", None),
                },
                "costs": {
                    "prompt_cost": getattr(run, "prompt_cost", None),
                    "completion_cost": getattr(run, "completion_cost", None),
                    "total_cost": getattr(run, "total_cost", None),
                },
                "custom_metadata": run.extra.get("metadata", {})
                if hasattr(run, "extra") and run.extra
                else {},
            }
        )

    if include_io:
        data.update(
            {
                "inputs": run.inputs if hasattr(run, "inputs") else None,
                "outputs": run.outputs if hasattr(run, "outputs") else None,
                "error": getattr(run, "error", None),
            }
        )

    return data


def _build_query_params(
    project: str | None = None,
    trace_ids: str | None = None,
    limit: int | None = None,
    last_n_minutes: int | None = None,
    since: str | None = None,
    run_type: str | None = None,
    is_root: bool = False,
    error: bool | None = None,
    name: str | None = None,
    raw_filter: str | None = None,
    min_latency: float | None = None,
    max_latency: float | None = None,
    min_tokens: int | None = None,
    tags: str | None = None,
) -> dict:
    params = {}
    filter_parts = []

    if project or os.getenv("LANGSMITH_PROJECT"):
        params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")

    if trace_ids:
        ids = [t.strip() for t in trace_ids.split(",")]
        if len(ids) == 1:
            params["trace_id"] = ids[0]
        else:
            ids_str = ", ".join(f'"{id}"' for id in ids)
            filter_parts.append(f"in(trace_id, [{ids_str}])")

    if limit:
        params["limit"] = limit

    if last_n_minutes:
        params["start_time"] = datetime.now(UTC) - timedelta(minutes=last_n_minutes)
    elif since:
        params["start_time"] = datetime.fromisoformat(since.replace("Z", "+00:00"))

    if run_type:
        params["run_type"] = run_type
    if is_root:
        params["is_root"] = True
    if error is not None:
        params["error"] = error
    if name:
        filter_parts.append(f'search(name, "{name}")')
    if min_latency is not None:
        filter_parts.append(f"gte(latency, {min_latency})")
    if max_latency is not None:
        filter_parts.append(f"lte(latency, {max_latency})")
    if min_tokens is not None:
        filter_parts.append(f"gte(total_tokens, {min_tokens})")
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        if len(tag_list) == 1:
            filter_parts.append(f'has(tags, "{tag_list[0]}")')
        else:
            tag_filters = [f'has(tags, "{t}")' for t in tag_list]
            filter_parts.append(f"or({', '.join(tag_filters)})")
    if raw_filter:
        filter_parts.append(raw_filter)

    if filter_parts:
        if len(filter_parts) == 1:
            params["filter"] = filter_parts[0]
        else:
            params["filter"] = f"and({', '.join(filter_parts)})"

    return params


def _serialize(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return str(obj)
    return str(obj)


# ============================================================================
# Trace Tools
# ============================================================================


@mcp.tool()
def list_traces(
    project: str | None = None,
    limit: int = 10,
    last_n_minutes: int | None = None,
    since: str | None = None,
    error: bool | None = None,
    name: str | None = None,
    min_latency: float | None = None,
    max_latency: float | None = None,
    min_tokens: int | None = None,
    tags: str | None = None,
    raw_filter: str | None = None,
    include_metadata: bool = True,
    show_hierarchy: bool = False,
) -> str:
    """List LangSmith traces matching filters. Filters apply to the ROOT RUN of each trace.

    Args:
        project: Project name (defaults to LANGSMITH_PROJECT env var)
        limit: Max traces to return (default 10)
        last_n_minutes: Only traces from the last N minutes
        since: Only traces since this ISO timestamp
        error: True=only errors, False=only successes, None=all
        name: Filter root run name (case-insensitive search)
        min_latency: Min root run latency in seconds
        max_latency: Max root run latency in seconds
        min_tokens: Min total tokens on root run
        tags: Comma-separated tags (matches any)
        raw_filter: Raw LangSmith filter query for advanced filtering
        include_metadata: Include timing, tokens, costs (default True)
        show_hierarchy: Expand each trace to show the full run tree
    """
    client = _get_client()
    params = _build_query_params(
        project=project,
        limit=limit,
        last_n_minutes=last_n_minutes,
        since=since,
        is_root=True,
        error=error,
        name=name,
        raw_filter=raw_filter,
        min_latency=min_latency,
        max_latency=max_latency,
        min_tokens=min_tokens,
        tags=tags,
    )

    root_runs = sorted(
        list(client.list_runs(**params)),
        key=lambda x: x.start_time or datetime.min,
        reverse=True,
    )

    if not root_runs:
        return json.dumps({"message": "No traces found", "traces": []})

    if show_hierarchy:
        traces = []
        for root in root_runs:
            trace_id = str(root.trace_id) if hasattr(root, "trace_id") else str(root.id)
            fetch_params = {"trace_id": trace_id}
            if project or os.getenv("LANGSMITH_PROJECT"):
                fetch_params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")
            all_runs = list(client.list_runs(**fetch_params))
            traces.append(
                {
                    "trace_id": trace_id,
                    "root": _extract_run(root, include_metadata, include_io=False),
                    "run_count": len(all_runs),
                    "runs": [
                        _extract_run(r, include_metadata, include_io=False)
                        for r in all_runs
                    ],
                }
            )
        return json.dumps({"count": len(traces), "traces": traces}, default=_serialize)

    data = [
        _extract_run(r, include_metadata=include_metadata, include_io=False)
        for r in root_runs
    ]
    return json.dumps({"count": len(data), "traces": data}, default=_serialize)


@mcp.tool()
def get_trace(
    trace_id: str,
    project: str | None = None,
    include_metadata: bool = True,
    include_io: bool = True,
) -> str:
    """Get a specific trace by ID with its full run hierarchy.

    Args:
        trace_id: The trace ID to fetch
        project: Project name (defaults to LANGSMITH_PROJECT env var)
        include_metadata: Include timing, tokens, costs
        include_io: Include inputs/outputs for each run
    """
    client = _get_client()
    params = {"trace_id": trace_id}
    if project or os.getenv("LANGSMITH_PROJECT"):
        params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")

    runs = list(client.list_runs(**params))

    if not runs:
        return json.dumps({"error": f"No runs found for trace {trace_id}"})

    return json.dumps(
        {
            "trace_id": trace_id,
            "run_count": len(runs),
            "runs": [_extract_run(r, include_metadata, include_io) for r in runs],
        },
        default=_serialize,
    )


@mcp.tool()
def list_runs(
    project: str | None = None,
    trace_ids: str | None = None,
    limit: int = 20,
    last_n_minutes: int | None = None,
    since: str | None = None,
    run_type: str | None = None,
    error: bool | None = None,
    name: str | None = None,
    min_latency: float | None = None,
    max_latency: float | None = None,
    min_tokens: int | None = None,
    tags: str | None = None,
    raw_filter: str | None = None,
    include_metadata: bool = True,
) -> str:
    """List individual runs matching filters (flat list, no hierarchy).

    Unlike list_traces, filters apply to ANY run (not just root runs).

    Args:
        project: Project name (defaults to LANGSMITH_PROJECT env var)
        trace_ids: Comma-separated trace IDs to filter
        limit: Max runs to return (default 20)
        last_n_minutes: Only runs from last N minutes
        since: Only runs since this ISO timestamp
        run_type: Filter by type: llm, chain, tool, retriever, prompt, parser
        error: True=only errors, False=only successes, None=all
        name: Filter by name (case-insensitive search)
        min_latency: Min latency in seconds
        max_latency: Max latency in seconds
        min_tokens: Min total tokens
        tags: Comma-separated tags (matches any)
        raw_filter: Raw LangSmith filter query
        include_metadata: Include timing, tokens, costs (default True)
    """
    client = _get_client()
    params = _build_query_params(
        project=project,
        trace_ids=trace_ids,
        limit=limit,
        last_n_minutes=last_n_minutes,
        since=since,
        run_type=run_type,
        is_root=False,
        error=error,
        name=name,
        raw_filter=raw_filter,
        min_latency=min_latency,
        max_latency=max_latency,
        min_tokens=min_tokens,
        tags=tags,
    )

    all_runs = sorted(
        list(client.list_runs(**params)),
        key=lambda x: x.start_time or datetime.min,
        reverse=True,
    )

    if not all_runs:
        return json.dumps({"message": "No runs found", "runs": []})

    data = [
        _extract_run(r, include_metadata=include_metadata, include_io=False)
        for r in all_runs
    ]
    return json.dumps({"count": len(data), "runs": data}, default=_serialize)


@mcp.tool()
def get_run(
    run_id: str,
    include_metadata: bool = True,
    include_io: bool = True,
) -> str:
    """Get a specific run by its ID.

    Args:
        run_id: The run ID to fetch
        include_metadata: Include timing, tokens, costs
        include_io: Include inputs/outputs
    """
    client = _get_client()
    try:
        run = client.read_run(run_id)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch run {run_id}: {e}"})

    return json.dumps(
        _extract_run(run, include_metadata, include_io), default=_serialize
    )


# ============================================================================
# Dataset Tools
# ============================================================================


@mcp.tool()
def list_datasets() -> str:
    """List all LangSmith datasets in the workspace."""
    client = _get_client()
    datasets = list(client.list_datasets(limit=100))

    if not datasets:
        return json.dumps({"message": "No datasets found", "datasets": []})

    data = [
        {
            "name": ds.name,
            "id": str(ds.id),
            "description": ds.description or "",
            "example_count": ds.example_count or 0,
        }
        for ds in datasets
    ]
    return json.dumps({"count": len(data), "datasets": data}, default=_serialize)


@mcp.tool()
def show_dataset(dataset_name: str, limit: int = 5) -> str:
    """Show examples from a LangSmith dataset.

    Args:
        dataset_name: Name of the dataset
        limit: Number of examples to show (default 5)
    """
    client = _get_client()
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
    except Exception:
        return json.dumps({"error": f"Dataset '{dataset_name}' not found"})

    examples = [
        {"inputs": ex.inputs, "outputs": ex.outputs}
        for ex in client.list_examples(dataset_id=dataset.id, limit=limit)
    ]

    return json.dumps(
        {
            "dataset": dataset_name,
            "total_examples": dataset.example_count,
            "showing": len(examples),
            "examples": examples,
        },
        default=_serialize,
    )


# ============================================================================
# Experiment Tools
# ============================================================================


@mcp.tool()
def list_experiments(
    dataset_name: str,
    limit: int = 20,
    include_stats: bool = True,
) -> str:
    """List experiments for a dataset, with aggregate metrics.

    Args:
        dataset_name: Name of the dataset the experiments ran against
        limit: Max experiments to return (default 20)
        include_stats: Include latency, cost, error rate, feedback (default True)
    """
    client = _get_client()
    experiments = list(
        client.list_projects(
            reference_dataset_name=dataset_name,
            include_stats=include_stats,
            limit=limit,
        )
    )

    if not experiments:
        return json.dumps(
            {"message": f"No experiments found for '{dataset_name}'", "experiments": []}
        )

    experiments.sort(
        key=lambda e: e.start_time if hasattr(e, "start_time") and e.start_time else "",
        reverse=True,
    )

    data = []
    for exp in experiments:
        feedback_stats = getattr(exp, "feedback_stats", None)
        # Normalize feedback_stats to be JSON-serializable
        fb = {}
        if feedback_stats and isinstance(feedback_stats, dict):
            for key, val in feedback_stats.items():
                if isinstance(val, dict):
                    fb[key] = val
                elif isinstance(val, (int, float)):
                    fb[key] = {"avg": val}

        latency_p50 = getattr(exp, "latency_p50", None)
        if hasattr(latency_p50, "total_seconds"):
            latency_p50 = latency_p50.total_seconds()

        latency_p99 = getattr(exp, "latency_p99", None)
        if hasattr(latency_p99, "total_seconds"):
            latency_p99 = latency_p99.total_seconds()

        data.append(
            {
                "name": exp.name,
                "id": str(exp.id),
                "run_count": getattr(exp, "run_count", None),
                "latency_p50_seconds": latency_p50,
                "latency_p99_seconds": latency_p99,
                "total_tokens": getattr(exp, "total_tokens", None),
                "total_cost": getattr(exp, "total_cost", None),
                "error_rate": getattr(exp, "error_rate", None),
                "feedback_stats": fb,
                "start_time": exp.start_time.isoformat()
                if hasattr(exp, "start_time") and exp.start_time
                else None,
            }
        )

    return json.dumps(
        {"count": len(data), "dataset": dataset_name, "experiments": data},
        default=_serialize,
    )


@mcp.tool()
def show_experiment(dataset_name: str, experiment_name: str) -> str:
    """Show detailed stats for a specific experiment.

    Displays latency (p50/p99), token usage, costs, error rate,
    and all feedback keys with aggregate scores.

    Args:
        dataset_name: Name of the dataset
        experiment_name: Name of the experiment
    """
    client = _get_client()
    experiments = list(
        client.list_projects(
            reference_dataset_name=dataset_name,
            include_stats=True,
        )
    )

    match = None
    for exp in experiments:
        if exp.name == experiment_name:
            match = exp
            break

    if not match:
        available = [exp.name for exp in experiments[:10]]
        return json.dumps(
            {
                "error": f"Experiment '{experiment_name}' not found in dataset '{dataset_name}'",
                "available_experiments": available,
            }
        )

    feedback_stats = getattr(match, "feedback_stats", None)
    fb = {}
    if feedback_stats and isinstance(feedback_stats, dict):
        for key, val in sorted(feedback_stats.items()):
            if isinstance(val, dict):
                fb[key] = val
            elif isinstance(val, (int, float)):
                fb[key] = {"avg": val}

    latency_p50 = getattr(match, "latency_p50", None)
    if hasattr(latency_p50, "total_seconds"):
        latency_p50 = latency_p50.total_seconds()

    latency_p99 = getattr(match, "latency_p99", None)
    if hasattr(latency_p99, "total_seconds"):
        latency_p99 = latency_p99.total_seconds()

    return json.dumps(
        {
            "name": match.name,
            "id": str(match.id),
            "run_count": getattr(match, "run_count", None),
            "latency_p50_seconds": latency_p50,
            "latency_p99_seconds": latency_p99,
            "total_tokens": getattr(match, "total_tokens", None),
            "total_cost": getattr(match, "total_cost", None),
            "error_rate": getattr(match, "error_rate", None),
            "feedback_stats": fb,
            "start_time": match.start_time.isoformat()
            if hasattr(match, "start_time") and match.start_time
            else None,
        },
        default=_serialize,
    )


if __name__ == "__main__":
    mcp.run()
