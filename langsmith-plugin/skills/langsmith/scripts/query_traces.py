#!/usr/bin/env python3
"""LangSmith Trace Query Tool - Query and export traces and runs.

Two command groups with consistent behavior:

  traces  - Operations on trace trees (root run + all children)
            Filters apply to the ROOT RUN, then full hierarchy is fetched.
            Always returns complete trace trees.

  runs    - Operations on individual runs (flat list)
            Filters apply to ANY MATCHING RUN.
            Returns flat list of runs without hierarchy.

Examples:
  # TRACES - always includes hierarchy
  query_traces.py traces list --limit 5 --min-latency 2.0
  query_traces.py traces get <trace-id>
  query_traces.py traces export ./output --limit 10

  # RUNS - flat list of individual runs
  query_traces.py runs list --run-type llm --limit 20
  query_traces.py runs get <run-id>
  query_traces.py runs export ./output --run-type tool
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click
from dotenv import load_dotenv
from langsmith import Client
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

load_dotenv(override=False)
console = Console()


# ============================================================================
# Helpers
# ============================================================================


def get_client() -> Client:
    """Get LangSmith client with API key from environment."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        console.print("[red]Error: LANGSMITH_API_KEY not set[/red]")
        sys.exit(1)
    return Client(api_key=api_key)


def build_query_params(
    project: str | None,
    trace_ids: str | None,
    limit: int | None,
    last_n_minutes: int | None,
    since: str | None,
    run_type: str | None,
    is_root: bool,
    error: bool | None,
    name: str | None,
    raw_filter: str | None,
    min_latency: float | None = None,
    max_latency: float | None = None,
    min_tokens: int | None = None,
    tags: str | None = None,
) -> dict:
    """Build unified query params for list_runs. All filters AND together.

    Args:
        project: Project name (overrides LANGSMITH_PROJECT env)
        trace_ids: Comma-separated trace IDs to filter
        limit: Max results to return
        last_n_minutes: Only results from last N minutes
        since: Only results since ISO timestamp
        run_type: Filter by run type (llm, chain, tool, retriever, prompt, parser)
        is_root: Only root runs (True for traces commands)
        error: Filter by error status (True=errors only, False=no errors, None=all)
        name: Filter by name pattern (case-insensitive search)
        raw_filter: Raw LangSmith filter query for advanced filtering
        min_latency: Min latency in seconds
        max_latency: Max latency in seconds
        min_tokens: Min total tokens
        tags: Comma-separated tags (matches any)

    Returns:
        Dict of params for client.list_runs()
    """
    params = {}
    filter_parts = []

    # Project (always include if available)
    if project or os.getenv("LANGSMITH_PROJECT"):
        params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")

    # Trace IDs - filter to specific traces
    if trace_ids:
        ids = [t.strip() for t in trace_ids.split(",")]
        if len(ids) == 1:
            params["trace_id"] = ids[0]
        else:
            # Multiple trace IDs - use filter query
            ids_str = ", ".join(f'"{id}"' for id in ids)
            filter_parts.append(f"in(trace_id, [{ids_str}])")

    # Limit
    if limit:
        params["limit"] = limit

    # Time filters
    if last_n_minutes:
        params["start_time"] = datetime.now(UTC) - timedelta(minutes=last_n_minutes)
    elif since:
        params["start_time"] = datetime.fromisoformat(since.replace("Z", "+00:00"))

    # Run type
    if run_type:
        params["run_type"] = run_type

    # Is root
    if is_root:
        params["is_root"] = True

    # Error status
    if error is not None:
        params["error"] = error

    # Name pattern
    if name:
        filter_parts.append(f'search(name, "{name}")')

    # Latency filters (in seconds)
    if min_latency is not None:
        filter_parts.append(f"gte(latency, {min_latency})")
    if max_latency is not None:
        filter_parts.append(f"lte(latency, {max_latency})")

    # Token filter
    if min_tokens is not None:
        filter_parts.append(f"gte(total_tokens, {min_tokens})")

    # Tags filter (comma-separated, any match)
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        if len(tag_list) == 1:
            filter_parts.append(f'has(tags, "{tag_list[0]}")')
        else:
            # Multiple tags - OR them together (has any of these tags)
            tag_filters = [f'has(tags, "{t}")' for t in tag_list]
            filter_parts.append(f"or({', '.join(tag_filters)})")

    # Raw filter query (advanced)
    if raw_filter:
        filter_parts.append(raw_filter)

    # Combine all filter parts with AND
    if filter_parts:
        if len(filter_parts) == 1:
            params["filter"] = filter_parts[0]
        else:
            params["filter"] = f"and({', '.join(filter_parts)})"

    return params


def format_duration(ms: float | None) -> str:
    """Format milliseconds as human-readable duration."""
    return "N/A" if ms is None else f"{ms:.0f}ms" if ms < 1000 else f"{ms / 1000:.2f}s"


def get_trace_id(run) -> str:
    """Extract trace ID from run object."""
    return str(run.trace_id) if hasattr(run, "trace_id") else str(run.id)


def calc_duration(run) -> int | None:
    """Calculate duration in ms from run times."""
    if hasattr(run, "start_time") and hasattr(run, "end_time") and run.start_time and run.end_time:
        return int((run.end_time - run.start_time).total_seconds() * 1000)
    return None


def extract_run(run, include_metadata=False, include_io=False) -> dict:
    """Extract run data with configurable detail level.

    Args:
        run: LangSmith run object
        include_metadata: Include timing, tokens, costs
        include_io: Include inputs/outputs

    Returns:
        Dict with run data
    """
    data = {
        "run_id": str(run.id),
        "trace_id": get_trace_id(run),
        "name": run.name,
        "run_type": run.run_type,
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "start_time": run.start_time.isoformat()
        if hasattr(run, "start_time") and run.start_time
        else None,
        "end_time": run.end_time.isoformat() if hasattr(run, "end_time") and run.end_time else None,
    }

    if include_metadata:
        data.update(
            {
                "status": getattr(run, "status", None),
                "duration_ms": calc_duration(run),
                "custom_metadata": run.extra.get("metadata", {})
                if hasattr(run, "extra") and run.extra
                else {},
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


def output_json(data, file_path=None):
    """Output data as pretty JSON to file or console."""
    json_str = json.dumps(data, indent=2, default=str)
    if file_path:
        with open(file_path, "w") as f:
            f.write(json_str)
        console.print(f"[green]✓[/green] Saved to {file_path}")
    else:
        console.print(Syntax(json_str, "json", theme="monokai", line_numbers=False))


def print_tree(runs, parent_id=None, indent=0, visited=None):
    """Print trace hierarchy tree."""
    if visited is None:
        visited = set()

    for run in sorted(
        [r for r in runs if r.parent_run_id == parent_id],
        key=lambda x: x.start_time if x.start_time else datetime.min,
    ):
        if run.id in visited:
            continue
        visited.add(run.id)

        prefix = "  " * indent
        duration = f" ({calc_duration(run):.0f}ms)" if calc_duration(run) else ""

        console.print(f"{prefix}└── [cyan]{run.name}[/cyan] ({run.run_type}){duration}")
        console.print(f"{prefix}    run_id: [dim]{run.id}[/dim]")
        if run.parent_run_id:
            console.print(f"{prefix}    parent: [dim]{run.parent_run_id}[/dim]")

        print_tree(runs, run.id, indent + 1, visited)


def print_runs_table(runs, include_metadata=False, show_trace_id=True):
    """Print runs as a table."""
    table = Table(show_header=True)
    table.add_column("Time", style="cyan")
    table.add_column("Name", style="yellow")
    table.add_column("Type", style="magenta")
    if show_trace_id:
        table.add_column("Trace ID", style="dim")
    table.add_column("Run ID", style="dim")
    if include_metadata:
        table.add_column("Duration", style="green")
        table.add_column("Status")

    for run in sorted(runs, key=lambda x: x.start_time or datetime.min, reverse=True):
        row = [
            run.start_time.strftime("%H:%M:%S") if run.start_time else "N/A",
            run.name[:40] if run.name else "N/A",
            run.run_type or "N/A",
        ]
        if show_trace_id:
            row.append(get_trace_id(run)[:16] + "...")
        row.append(str(run.id)[:16] + "...")
        if include_metadata:
            row.extend([format_duration(calc_duration(run)), getattr(run, "status", "N/A")])
        table.add_row(*row)

    console.print(table)


# ============================================================================
# Shared filter options (decorator factory)
# ============================================================================


def common_filter_options(include_run_type=True):
    """Add common filter options to a command.

    Args:
        include_run_type: Whether to include --run-type option (False for traces list)
    """

    def decorator(f):
        # Basic filters
        f = click.option("--trace-ids", help="Comma-separated trace IDs to filter")(f)
        f = click.option("--limit", "-n", type=int, help="Max results to return")(f)
        f = click.option("--project", help="Project name (overrides LANGSMITH_PROJECT env)")(f)
        f = click.option("--last-n-minutes", type=int, help="Only from last N minutes")(f)
        f = click.option("--since", help="Only since ISO timestamp")(f)
        if include_run_type:
            f = click.option(
                "--run-type",
                type=click.Choice(["llm", "chain", "tool", "retriever", "prompt", "parser"]),
                help="Filter by run type",
            )(f)
        f = click.option("--error/--no-error", default=None, help="Filter by error status")(f)
        f = click.option("--name", help="Filter by name pattern (case-insensitive search)")(f)
        # Performance filters
        f = click.option(
            "--min-latency", type=float, help="Min latency in seconds (e.g., 5 for >= 5s)"
        )(f)
        f = click.option(
            "--max-latency", type=float, help="Max latency in seconds (e.g., 10 for <= 10s)"
        )(f)
        f = click.option(
            "--min-tokens", type=int, help="Min total tokens (e.g., 1000 for >= 1000)"
        )(f)
        f = click.option("--tags", help="Filter by tags (comma-separated, matches any)")(f)
        # Advanced filter
        f = click.option(
            "--filter",
            "raw_filter",
            help="Raw LangSmith filter query (for feedback, metadata, etc.)",
        )(f)
        return f

    return decorator


# ============================================================================
# Main CLI
# ============================================================================


@click.group()
def cli():
    """LangSmith Trace Query Tool

    \b
    Two command groups with consistent behavior:

    \b
    TRACES - Operations on trace trees (root + all child runs)
      traces list    List traces with hierarchy
      traces get     Get single trace by ID
      traces export  Export traces to JSONL files

    \b
    RUNS - Operations on individual runs (flat)
      runs list      List runs (flat)
      runs get       Get single run by ID
      runs export    Export runs to JSONL files

    \b
    Key difference:
      - traces: Filters apply to ROOT RUN, returns full hierarchy
      - runs: Filters apply to ANY RUN, returns flat list
    """
    pass


# ============================================================================
# TRACES Commands - Always return full hierarchy
# ============================================================================


@cli.group()
def traces():
    """Operations on trace trees (root run + all children).

    Filters apply to the ROOT RUN of each trace. When a trace matches,
    the entire hierarchy (all child runs) is included.

    \b
    Commands:
      list    List traces matching filters (shows hierarchy)
      get     Get single trace by ID (shows hierarchy)
      export  Export traces to JSONL files (includes all runs)
    """
    pass


@traces.command("list")
@common_filter_options(
    include_run_type=False
)  # run_type doesn't make sense for trace-level filtering
@click.option(
    "--format", "fmt", type=click.Choice(["json", "pretty"]), default="pretty", help="Output format"
)
@click.option("--include-metadata", is_flag=True, help="Include timing/tokens/costs")
@click.option("--show-hierarchy", is_flag=True, help="Expand each trace to show run tree")
def traces_list(
    trace_ids,
    limit,
    project,
    last_n_minutes,
    since,
    error,
    name,
    min_latency,
    max_latency,
    min_tokens,
    tags,
    raw_filter,
    fmt,
    include_metadata,
    show_hierarchy,
):
    """List traces matching filters.

    Filters apply to the ROOT RUN of each trace. Returns trace-level view
    by default, or expanded hierarchy with --show-hierarchy.

    \b
    FILTERS (all AND together, applied to root run):
      --trace-ids abc,def   Filter to specific traces
      --limit 20            Max traces (default: 20)
      --error / --no-error  Filter by error status
      --name "agent"        Root name contains "agent"
      --min-latency 5       Root run took >= 5 seconds
      --max-latency 10      Root run took <= 10 seconds
      --min-tokens 1000     Root run used >= 1000 tokens
      --tags prod,test      Root run has any of these tags

    \b
    ADVANCED FILTER (--filter):
    For complex queries like feedback filtering:
      --filter 'and(eq(feedback_key, "correctness"), gte(feedback_score, 0.8))'

    \b
    Examples:
      traces list --limit 5                        # 5 most recent traces
      traces list --min-latency 2.0 --limit 10     # 10 slowest traces (>= 2s)
      traces list --error --last-n-minutes 60      # Failed traces in last hour
      traces list --limit 5 --show-hierarchy       # Show full tree for each trace
    """
    client = get_client()

    # Build params - always query root runs for traces
    params = build_query_params(
        project,
        trace_ids,
        limit or 20,
        last_n_minutes,
        since,
        None,  # run_type not applicable for trace-level filtering
        True,  # is_root=True for traces
        error,
        name,
        raw_filter,
        min_latency,
        max_latency,
        min_tokens,
        tags,
    )

    with console.status("[cyan]Fetching traces..."):
        root_runs = list(client.list_runs(**params))

    if not root_runs:
        console.print("[yellow]No traces found[/yellow]")
        return

    root_runs = sorted(root_runs, key=lambda x: x.start_time or datetime.min, reverse=True)

    if show_hierarchy:
        # Fetch full hierarchy for each trace
        console.print(f"[green]✓[/green] Found {len(root_runs)} trace(s). Fetching hierarchy...\n")

        for root in root_runs:
            tid = get_trace_id(root)
            fetch_params = {"trace_id": tid}
            if project or os.getenv("LANGSMITH_PROJECT"):
                fetch_params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")

            all_runs = list(client.list_runs(**fetch_params))

            console.print(f"[bold]TRACE:[/bold] {tid}")
            console.print(f"  Root: [cyan]{root.name}[/cyan] ({len(all_runs)} runs)")
            if include_metadata:
                console.print(f"  Duration: {format_duration(calc_duration(root))}")
            print_tree(all_runs, root.id, indent=1)
            console.print()
    elif fmt == "json":
        data = [
            extract_run(r, include_metadata=include_metadata, include_io=False) for r in root_runs
        ]
        output_json(data)
    else:
        console.print(f"[green]✓[/green] Found {len(root_runs)} trace(s)\n")
        print_runs_table(root_runs, include_metadata=include_metadata, show_trace_id=True)
        console.print("\n[dim]Tip: Use --show-hierarchy to expand each trace[/dim]")


@traces.command("get")
@click.argument("trace_id")
@click.option("--project", help="Project name")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "jsonl", "pretty"]),
    default="pretty",
    help="Output format (jsonl for dataset-compatible)",
)
@click.option("--output", "-o", help="Output file")
@click.option("--include-metadata", is_flag=True, help="Include timing/tokens/costs")
@click.option("--include-io", is_flag=True, help="Include inputs/outputs")
@click.option("--full", is_flag=True, help="Include everything (metadata + inputs/outputs)")
def traces_get(trace_id, project, fmt, output, include_metadata, include_io, full):
    """Get a specific trace by ID with full hierarchy.

    Returns all runs in the trace tree (root + all children).

    \b
    Examples:
      traces get abc123                              # Display trace tree
      traces get abc123 --format json -o trace.json  # Export to JSON
      traces get abc123 --format jsonl --full        # Export to JSONL (dataset-compatible)
    """
    client = get_client()

    if full:
        include_metadata = include_io = True

    params = {"trace_id": trace_id}
    if project or os.getenv("LANGSMITH_PROJECT"):
        params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")

    with console.status("[cyan]Fetching trace..."):
        runs = list(client.list_runs(**params))

    if not runs:
        console.print(f"[red]No runs found for trace {trace_id}[/red]")
        return

    # Find root run
    root_runs = [r for r in runs if r.parent_run_id is None]

    if fmt == "pretty":
        console.print(f"[green]✓[/green] Found {len(runs)} run(s) in trace\n")
        for root in root_runs:
            console.print(f"[bold]ROOT:[/bold] {root.name} (run_id: {root.id})")
            print_tree(runs, root.id, indent=1)
            console.print()
    elif fmt == "jsonl":
        # JSONL format - one run per line (dataset-compatible)
        lines = [
            json.dumps(extract_run(r, include_metadata, include_io), default=str) for r in runs
        ]
        content = "\n".join(lines)
        if output:
            with open(output, "w") as f:
                f.write(content + "\n")
            console.print(f"[green]✓[/green] Saved {len(runs)} runs to {output}")
        else:
            console.print(content)
    else:
        data = {
            "trace_id": trace_id,
            "run_count": len(runs),
            "runs": [extract_run(r, include_metadata, include_io) for r in runs],
        }
        output_json(data, output)


@traces.command("export")
@click.argument("output_dir", type=click.Path())
@common_filter_options(include_run_type=False)
@click.option("--include-metadata", is_flag=True, help="Include timing/tokens/costs")
@click.option("--include-io", is_flag=True, help="Include inputs/outputs")
@click.option("--full", is_flag=True, help="Include everything (metadata + inputs/outputs)")
@click.option("--filename-pattern", default="{trace_id}.jsonl", help="Filename pattern")
def traces_export(
    output_dir,
    trace_ids,
    limit,
    project,
    last_n_minutes,
    since,
    error,
    name,
    min_latency,
    max_latency,
    min_tokens,
    tags,
    raw_filter,
    include_metadata,
    include_io,
    full,
    filename_pattern,
):
    """Export traces to JSONL files (one file per trace, all runs included).

    Each trace is exported as a separate .jsonl file containing all runs
    in the trace tree (root + all children).

    \b
    FILTERS (all AND together, applied to root run):
      --trace-ids abc,def   Export specific traces
      --limit 20            Export up to 20 traces (default: 10)
      --error / --no-error  Filter by error status
      --name "agent"        Root name contains "agent"
      --min-latency 5       Root run took >= 5 seconds
      --tags production     Root run has this tag

    \b
    Examples:
      traces export ./traces --limit 10 --full           # 10 recent traces
      traces export ./traces --trace-ids abc,def --full  # Specific traces
      traces export ./traces --error --last-n-minutes 60 # Failed traces in last hour
      traces export ./traces --min-latency 5 --full      # Slow traces (>= 5s)
    """
    if full:
        include_metadata = include_io = True

    client = get_client()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    # Get list of trace IDs to export
    if trace_ids:
        trace_id_list = [t.strip() for t in trace_ids.split(",")]
        console.print(f"[cyan]Exporting {len(trace_id_list)} specified trace(s)...[/cyan]")
    else:
        # Query for root traces first
        root_params = build_query_params(
            project,
            None,
            limit or 10,
            last_n_minutes,
            since,
            None,
            True,
            error,
            name,
            raw_filter,  # is_root=True
            min_latency,
            max_latency,
            min_tokens,
            tags,
        )

        with console.status("[cyan]Querying traces..."):
            root_runs = list(client.list_runs(**root_params))
            root_runs = sorted(root_runs, key=lambda x: x.start_time or datetime.min, reverse=True)

        if not root_runs:
            console.print("[yellow]No traces found[/yellow]")
            return

        trace_id_list = [get_trace_id(r) for r in root_runs]
        console.print(
            f"[green]✓[/green] Found {len(trace_id_list)} trace(s). Fetching full hierarchy..."
        )

    # Fetch and export each trace
    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Fetching {task.completed}/{task.total}..."),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("fetch", total=len(trace_id_list))
        for tid in trace_id_list:
            try:
                fetch_params = {"trace_id": tid}
                if project or os.getenv("LANGSMITH_PROJECT"):
                    fetch_params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")
                trace_runs = list(client.list_runs(**fetch_params))
                if trace_runs:
                    results.append((tid, trace_runs))
            except Exception as e:
                console.print(f"[yellow]Warning: Failed {tid}: {e}[/yellow]")
            progress.update(task, advance=1)

    if not results:
        console.print("[yellow]No traces exported[/yellow]")
        return

    console.print(f"[cyan]Saving {len(results)} trace(s) to {output_path}/[/cyan]")

    for idx, (tid, trace_runs) in enumerate(results, 1):
        filename = filename_pattern.format(trace_id=tid, index=idx)
        if not filename.endswith(".jsonl"):
            filename = (
                filename.rsplit(".", 1)[0] + ".jsonl" if "." in filename else filename + ".jsonl"
            )

        with open(output_path / filename, "w") as f:
            for run in trace_runs:
                run_data = extract_run(run, include_metadata, include_io)
                f.write(json.dumps(run_data, default=str) + "\n")

        console.print(f"  [green]✓[/green] {tid[:16]}... → {filename} ({len(trace_runs)} runs)")

    console.print(f"\n[green]✓[/green] Exported {len(results)} trace(s) to {output_path}/")


# ============================================================================
# RUNS Commands - Return flat list of individual runs
# ============================================================================


@cli.group()
def runs():
    """Operations on individual runs (flat list).

    Filters apply to ANY RUN that matches. Returns a flat list of runs
    without hierarchy information.

    \b
    Commands:
      list    List runs matching filters (flat)
      get     Get single run by ID
      export  Export runs to JSONL file (flat)
    """
    pass


@runs.command("list")
@common_filter_options(include_run_type=True)
@click.option(
    "--format", "fmt", type=click.Choice(["json", "pretty"]), default="pretty", help="Output format"
)
@click.option("--include-metadata", is_flag=True, help="Include timing/tokens/costs")
def runs_list(
    trace_ids,
    limit,
    project,
    last_n_minutes,
    since,
    run_type,
    error,
    name,
    min_latency,
    max_latency,
    min_tokens,
    tags,
    raw_filter,
    fmt,
    include_metadata,
):
    """List runs matching filters (flat list).

    Filters apply to ANY RUN that matches, not just root runs.
    Returns a flat list of individual runs.

    \b
    FILTERS (all AND together):
      --trace-ids abc,def   Runs from specific traces
      --limit 50            Max runs (default: 50)
      --run-type llm        Only LLM runs (or: chain, tool, retriever, prompt, parser)
      --error / --no-error  Filter by error status
      --name "model"        Name contains "model"
      --min-latency 5       Runs taking >= 5 seconds
      --max-latency 10      Runs taking <= 10 seconds
      --min-tokens 1000     Runs using >= 1000 tokens
      --tags prod,test      Runs with any of these tags

    \b
    ADVANCED FILTER (--filter):
    For complex queries like feedback filtering:
      --filter 'and(eq(feedback_key, "quality"), gte(feedback_score, 0.8))'

    \b
    Examples:
      runs list --run-type llm --limit 20           # 20 recent LLM calls
      runs list --run-type tool --error             # Failed tool calls
      runs list --name "ChatOpenAI" --min-latency 5 # Slow ChatOpenAI calls
      runs list --trace-ids abc123 --run-type tool  # Tool calls from specific trace
    """
    client = get_client()

    params = build_query_params(
        project,
        trace_ids,
        limit or 50,
        last_n_minutes,
        since,
        run_type,
        False,  # is_root=False for runs
        error,
        name,
        raw_filter,
        min_latency,
        max_latency,
        min_tokens,
        tags,
    )

    with console.status("[cyan]Fetching runs..."):
        all_runs = list(client.list_runs(**params))

    if not all_runs:
        console.print("[yellow]No runs found[/yellow]")
        return

    all_runs = sorted(all_runs, key=lambda x: x.start_time or datetime.min, reverse=True)

    if fmt == "json":
        data = [
            extract_run(r, include_metadata=include_metadata, include_io=False) for r in all_runs
        ]
        output_json(data)
    else:
        console.print(f"[green]✓[/green] Found {len(all_runs)} run(s)\n")
        print_runs_table(all_runs, include_metadata=include_metadata, show_trace_id=True)


@runs.command("get")
@click.argument("run_id")
@click.option("--project", help="Project name")
@click.option(
    "--format", "fmt", type=click.Choice(["json", "pretty"]), default="pretty", help="Output format"
)
@click.option("--output", "-o", help="Output file")
@click.option("--include-metadata", is_flag=True, help="Include timing/tokens/costs")
@click.option("--include-io", is_flag=True, help="Include inputs/outputs")
@click.option("--full", is_flag=True, help="Include everything (metadata + inputs/outputs)")
def runs_get(run_id, project, fmt, output, include_metadata, include_io, full):
    """Get a specific run by ID.

    Returns a single run without hierarchy information.

    \b
    Examples:
      runs get abc123                              # Display run
      runs get abc123 --format json -o run.json   # Export to JSON
      runs get abc123 --full                      # Include all details
    """
    client = get_client()

    if full:
        include_metadata = include_io = True

    try:
        run = client.read_run(run_id)
    except Exception as e:
        console.print(f"[red]Error fetching run {run_id}: {e}[/red]")
        return

    if fmt == "pretty":
        console.print("[green]✓[/green] Found run\n")
        console.print(f"[bold]Run:[/bold] {run.name}")
        console.print(f"  ID: [dim]{run.id}[/dim]")
        console.print(f"  Trace ID: [dim]{get_trace_id(run)}[/dim]")
        console.print(f"  Type: {run.run_type}")
        console.print(f"  Parent: {run.parent_run_id or 'None (root)'}")
        if include_metadata:
            console.print(f"  Duration: {format_duration(calc_duration(run))}")
            console.print(f"  Status: {getattr(run, 'status', 'N/A')}")
        if include_io:
            console.print("\n[bold]Inputs:[/bold]")
            if run.inputs:
                console.print(Syntax(json.dumps(run.inputs, indent=2, default=str), "json"))
            console.print("\n[bold]Outputs:[/bold]")
            if run.outputs:
                console.print(Syntax(json.dumps(run.outputs, indent=2, default=str), "json"))
    else:
        data = extract_run(run, include_metadata, include_io)
        output_json(data, output)


@runs.command("export")
@click.argument("output_file", type=click.Path())
@common_filter_options(include_run_type=True)
@click.option("--include-metadata", is_flag=True, help="Include timing/tokens/costs")
@click.option("--include-io", is_flag=True, help="Include inputs/outputs")
@click.option("--full", is_flag=True, help="Include everything (metadata + inputs/outputs)")
def runs_export(
    output_file,
    trace_ids,
    limit,
    project,
    last_n_minutes,
    since,
    run_type,
    error,
    name,
    min_latency,
    max_latency,
    min_tokens,
    tags,
    raw_filter,
    include_metadata,
    include_io,
    full,
):
    """Export runs to a single JSONL file (flat list).

    Exports matching runs as one JSONL file (one run per line).
    No hierarchy - just a flat list of runs.

    \b
    FILTERS (all AND together):
      --trace-ids abc,def   Runs from specific traces
      --limit 100           Max runs (default: 100)
      --run-type llm        Only LLM runs
      --error / --no-error  Filter by error status
      --name "model"        Name contains "model"
      --min-latency 5       Runs taking >= 5 seconds
      --tags production     Runs with this tag

    \b
    Examples:
      runs export ./llm_runs.jsonl --run-type llm --limit 100    # Export LLM runs
      runs export ./tools.jsonl --run-type tool --full           # Export tool calls
      runs export ./errors.jsonl --error --last-n-minutes 60     # Export errors
      runs export ./slow.jsonl --min-latency 10 --full           # Export slow runs
    """
    if full:
        include_metadata = include_io = True

    client = get_client()
    output_path = Path(output_file).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    params = build_query_params(
        project,
        trace_ids,
        limit or 100,
        last_n_minutes,
        since,
        run_type,
        False,  # is_root=False for runs
        error,
        name,
        raw_filter,
        min_latency,
        max_latency,
        min_tokens,
        tags,
    )

    with console.status("[cyan]Fetching runs..."):
        all_runs = list(client.list_runs(**params))

    if not all_runs:
        console.print("[yellow]No runs found[/yellow]")
        return

    all_runs = sorted(all_runs, key=lambda x: x.start_time or datetime.min, reverse=True)

    # Ensure .jsonl extension
    if not str(output_path).endswith(".jsonl"):
        output_path = output_path.with_suffix(".jsonl")

    with open(output_path, "w") as f:
        for run in all_runs:
            run_data = extract_run(run, include_metadata, include_io)
            f.write(json.dumps(run_data, default=str) + "\n")

    console.print(f"[green]✓[/green] Exported {len(all_runs)} run(s) to {output_path}")


if __name__ == "__main__":
    cli()
