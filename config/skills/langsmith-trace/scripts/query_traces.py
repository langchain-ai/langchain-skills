#!/usr/bin/env python3
"""LangSmith Trace Query Tool - Query and export traces with metadata support."""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
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


def add_time_filter(params: dict, last_n_minutes: int | None, since: str | None):
    """Add time filtering to filter params."""
    if last_n_minutes:
        params["start_time"] = datetime.now(timezone.utc) - timedelta(minutes=last_n_minutes)
    elif since:
        params["start_time"] = datetime.fromisoformat(since.replace("Z", "+00:00"))


def format_duration(ms: float | None) -> str:
    """Format milliseconds as human-readable duration."""
    return "N/A" if ms is None else f"{ms:.0f}ms" if ms < 1000 else f"{ms/1000:.2f}s"


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
        include_io: Include inputs and outputs
    """
    data = {
        "run_id": str(run.id),
        "trace_id": get_trace_id(run),
        "name": run.name,
        "run_type": run.run_type,
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
    }

    if include_metadata:
        data.update({
            "status": getattr(run, "status", None),
            "start_time": run.start_time.isoformat() if hasattr(run, "start_time") and run.start_time else None,
            "end_time": run.end_time.isoformat() if hasattr(run, "end_time") and run.end_time else None,
            "duration_ms": calc_duration(run),
            "custom_metadata": run.extra.get("metadata", {}) if hasattr(run, "extra") and run.extra else {},
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
        })

    if include_io:
        data.update({
            "inputs": run.inputs if hasattr(run, "inputs") else None,
            "outputs": run.outputs if hasattr(run, "outputs") else None,
            "error": getattr(run, "error", None),
        })

    return data


# Legacy aliases for backwards compatibility
def extract_metadata(run) -> dict:
    """Extract full metadata from run (legacy)."""
    return extract_run(run, include_metadata=True, include_io=False)


def extract_basic(run) -> dict:
    """Extract basic run info (legacy)."""
    return extract_run(run, include_metadata=False, include_io=False)


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

    for run in sorted([r for r in runs if r.parent_run_id == parent_id],
                     key=lambda x: x.start_time if x.start_time else datetime.min):
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


# ============================================================================
# Commands
# ============================================================================

@click.group()
def cli():
    """LangSmith Trace Query Tool"""
    pass


@cli.command()
@click.option("--limit", "-n", default=20, help="Number of traces (default: 20)")
@click.option("--project", help="Project name (overrides env)")
@click.option("--last-n-minutes", type=int, help="Only last N minutes")
@click.option("--since", help="Only since ISO timestamp")
@click.option("--format", "fmt", type=click.Choice(["json", "pretty"]), default="pretty")
@click.option("--include-metadata", is_flag=True, help="Include timing/tokens/costs")
def recent(limit, project, last_n_minutes, since, fmt, include_metadata):
    """Show recent traces."""
    client = get_client()

    params = {"is_root": True, "limit": limit}
    if project or os.getenv("LANGSMITH_PROJECT"):
        params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")
    add_time_filter(params, last_n_minutes, since)

    with console.status("[cyan]Fetching traces..."):
        runs = list(client.list_runs(**params))

    if not runs:
        console.print("[yellow]No traces found[/yellow]")
        return

    if fmt == "json":
        data = [extract_metadata(r) if include_metadata else {
            "trace_id": get_trace_id(r),
            "name": r.name,
            "start_time": r.start_time.isoformat() if r.start_time else None,
        } for r in runs]
        output_json(data)
    else:
        console.print(f"[green]✓[/green] Found {len(runs)} trace(s)\n")

        table = Table(show_header=True)
        table.add_column("Time", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Trace ID", style="dim")
        if include_metadata:
            table.add_column("Duration", style="green")
            table.add_column("Status", style="magenta")

        for run in sorted(runs, key=lambda x: x.start_time or datetime.min, reverse=True):
            row = [
                run.start_time.strftime("%H:%M:%S") if run.start_time else "N/A",
                run.name[:40],
                get_trace_id(run)[:16] + "...",
            ]
            if include_metadata:
                row.extend([format_duration(calc_duration(run)), getattr(run, "status", "N/A")])
            table.add_row(*row)

        console.print(table)


@cli.command()
@click.argument("trace_id")
@click.option("--project", help="Project name")
@click.option("--format", "fmt", type=click.Choice(["json", "pretty"]), default="pretty")
@click.option("--output", "-o", help="Output file")
@click.option("--include-metadata", is_flag=True, help="Include timing/tokens/costs")
@click.option("--include-io", is_flag=True, help="Include inputs/outputs")
@click.option("--full", is_flag=True, help="Include everything (metadata + inputs/outputs)")
@click.option("--show-hierarchy", is_flag=True, help="Show run tree")
def trace(trace_id, project, fmt, output, include_metadata, include_io, full, show_hierarchy):
    """Fetch specific trace by ID."""
    client = get_client()

    # --full enables both metadata and io
    if full:
        include_metadata = include_io = True

    params = {"trace_id": trace_id, "limit": 100}
    if project or os.getenv("LANGSMITH_PROJECT"):
        params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")

    with console.status(f"[cyan]Fetching trace..."):
        runs = list(client.list_runs(**params))

    if not runs:
        console.print(f"[red]No runs found for trace {trace_id}[/red]")
        return

    if show_hierarchy:
        console.print(f"[green]✓[/green] Found {len(runs)} run(s)\n")
        for root in [r for r in runs if r.parent_run_id is None]:
            console.print(f"[bold]ROOT:[/bold] {root.name} (run_id: {root.id})")
            print_tree(runs, root.id, indent=1)
            console.print()
    else:
        data = {
            "trace_id": trace_id,
            "runs": [extract_run(r, include_metadata, include_io) for r in runs],
        }

        if fmt == "json":
            output_json(data, output)
        else:
            if output:
                console.print("[yellow]Warning: --output ignored in pretty format[/yellow]")
            console.print(f"[green]✓[/green] Found {len(runs)} run(s)")
            output_json(data)


@cli.command()
@click.argument("output_dir", type=click.Path())
@click.option("--limit", "-n", default=10, help="Number of traces (default: 10)")
@click.option("--project", help="Project name")
@click.option("--last-n-minutes", type=int, help="Time filter")
@click.option("--since", help="ISO timestamp filter")
@click.option("--include-metadata", is_flag=True, help="Include timing/tokens/costs")
@click.option("--include-io", is_flag=True, help="Include inputs/outputs")
@click.option("--full", is_flag=True, help="Include everything (metadata + inputs/outputs)")
@click.option("--run-type", "run_type_filter", help="Filter by run type (llm, tool, chain, retriever)")
@click.option("--filename-pattern", default="{trace_id}.json", help="Filename pattern")
@click.option("--max-concurrent", default=5, help="Parallel fetches (default: 5)")
def export(output_dir, limit, project, last_n_minutes, since, include_metadata, include_io, full, run_type_filter, filename_pattern, max_concurrent):
    """Export traces to directory (one file per trace)."""
    # --full enables both metadata and io
    if full:
        include_metadata = include_io = True

    client = get_client()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    params = {"is_root": True, "limit": limit}
    if project or os.getenv("LANGSMITH_PROJECT"):
        params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")
    add_time_filter(params, last_n_minutes, since)

    with console.status("[cyan]Querying traces..."):
        runs = list(client.list_runs(**params))

    if not runs:
        console.print("[yellow]No traces found[/yellow]")
        return

    console.print(f"[green]✓[/green] Found {len(runs)} trace(s). Fetching details...")

    def fetch_runs(run):
        trace_id = get_trace_id(run)
        try:
            params = {"trace_id": trace_id, "limit": 100}
            if project or os.getenv("LANGSMITH_PROJECT"):
                params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")
            return trace_id, list(client.list_runs(**params))
        except Exception as e:
            console.print(f"[yellow]Warning: Failed {trace_id}: {e}[/yellow]")
            return trace_id, None

    results = []
    with Progress(SpinnerColumn(), TextColumn("[bold blue]Fetching {task.completed}/{task.total}..."),
                  BarColumn(), TaskProgressColumn()) as progress:
        task = progress.add_task("fetch", total=len(runs))
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            for future in as_completed({executor.submit(fetch_runs, r): r for r in runs}):
                trace_id, trace_runs = future.result()
                if trace_runs:
                    results.append((trace_id, trace_runs))
                progress.update(task, advance=1)

    console.print(f"[cyan]Saving {len(results)} trace(s) to {output_path}/[/cyan]")

    for idx, (trace_id, trace_runs) in enumerate(results, 1):
        filename = filename_pattern.format(trace_id=trace_id, index=idx)
        if not filename.endswith(".json"):
            filename += ".json"

        # Apply run_type filter if specified
        filtered_runs = trace_runs
        if run_type_filter:
            filtered_runs = [r for r in trace_runs if r.run_type == run_type_filter]

        data = {
            "trace_id": trace_id,
            "runs": [extract_run(r, include_metadata, include_io) for r in filtered_runs],
        }

        with open(output_path / filename, "w") as f:
            json.dump(data, f, indent=2, default=str)

        console.print(f"  [green]✓[/green] {trace_id[:16]}... → {filename} ({len(filtered_runs)} runs)")

    console.print(f"\n[green]✓[/green] Exported {len(results)} trace(s) to {output_path}/")


@cli.command()
@click.argument("pattern")
@click.option("--limit", "-n", default=50, help="Max runs to search (default: 50)")
@click.option("--project", help="Project name")
@click.option("--last-n-minutes", type=int, help="Time filter")
@click.option("--format", "fmt", type=click.Choice(["json", "pretty"]), default="pretty")
def search(pattern, limit, project, last_n_minutes, fmt):
    """Search runs by name pattern."""
    client = get_client()

    params = {"limit": limit}
    if project or os.getenv("LANGSMITH_PROJECT"):
        params["project_name"] = project or os.getenv("LANGSMITH_PROJECT")
    add_time_filter(params, last_n_minutes, None)

    with console.status("[cyan]Searching..."):
        runs = list(client.list_runs(**params))

    matching = [r for r in runs if pattern.lower() in (r.name or "").lower()]

    if not matching:
        console.print(f"[yellow]No runs matching '{pattern}'[/yellow]")
        return

    console.print(f"[green]✓[/green] Found {len(matching)} match(es)\n")

    if fmt == "json":
        output_json([{
            "name": r.name,
            "trace_id": get_trace_id(r),
            "run_id": str(r.id),
            "start_time": r.start_time.isoformat() if r.start_time else None,
        } for r in matching[:20]])
    else:
        for run in sorted(matching[:20], key=lambda x: x.start_time or datetime.min, reverse=True):
            console.print(f"[yellow]Name:[/yellow] {run.name}")
            console.print(f"  [dim]Trace ID:[/dim] {get_trace_id(run)}")
            console.print(f"  [dim]Run ID:[/dim] {run.id}")
            if run.start_time:
                console.print(f"  [dim]Time:[/dim] {run.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            console.print()


if __name__ == "__main__":
    cli()
