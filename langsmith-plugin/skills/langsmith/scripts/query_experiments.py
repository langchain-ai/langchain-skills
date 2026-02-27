#!/usr/bin/env python3
"""LangSmith Experiment Query Tool - List and inspect experiments for a dataset.

Experiments in LangSmith are stored as projects with a reference_dataset_id.
This tool uses client.list_projects(reference_dataset_name=...) to find them.

Examples:
  query_experiments.py list "My Agent Tests"
  query_experiments.py list "My Agent Tests" --limit 5 --format json
  query_experiments.py show "My Agent Tests" "experiment-v2"
"""

import json
import os
import sys

import click
from dotenv import load_dotenv
from langsmith import Client
from rich.console import Console
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


def format_duration(seconds) -> str:
    """Format seconds (float or timedelta) as human-readable duration."""
    if seconds is None:
        return "N/A"
    # Handle timedelta objects from some API versions
    if hasattr(seconds, "total_seconds"):
        seconds = seconds.total_seconds()
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"


def format_cost(cost: float | None) -> str:
    """Format cost as dollar amount."""
    if cost is None:
        return "N/A"
    return f"${cost:.4f}"


def format_pct(value: float | None) -> str:
    """Format a ratio as percentage."""
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def extract_experiment_summary(exp) -> dict:
    """Extract key fields from a TracerSessionResult (experiment)."""
    data = {
        "name": exp.name,
        "id": str(exp.id),
        "run_count": getattr(exp, "run_count", None),
        "latency_p50": getattr(exp, "latency_p50", None),
        "latency_p99": getattr(exp, "latency_p99", None),
        "total_tokens": getattr(exp, "total_tokens", None),
        "total_cost": getattr(exp, "total_cost", None),
        "error_rate": getattr(exp, "error_rate", None),
        "feedback_stats": getattr(exp, "feedback_stats", None),
        "start_time": exp.start_time.isoformat() if hasattr(exp, "start_time") and exp.start_time else None,
    }
    return data


# ============================================================================
# CLI
# ============================================================================


@click.group()
def cli():
    """LangSmith Experiment Query Tool

    \b
    Commands:
      list   List experiments for a dataset
      show   Show detailed stats for one experiment
    """
    pass


@cli.command("list")
@click.argument("dataset_name")
@click.option("--limit", "-n", type=int, default=20, help="Max experiments to return")
@click.option(
    "--format", "fmt", type=click.Choice(["json", "pretty"]), default="pretty", help="Output format"
)
@click.option("--include-stats/--no-stats", default=True, help="Include aggregate stats (default: yes)")
def list_experiments(dataset_name, limit, fmt, include_stats):
    """List experiments for a dataset.

    Shows a table of experiments with aggregate metrics: run count, latency,
    cost, error rate, and feedback scores.

    \b
    Examples:
      list "My Agent Tests"                    # All experiments for dataset
      list "My Agent Tests" --limit 5          # Last 5 experiments
      list "My Agent Tests" --format json      # JSON output
      list "My Agent Tests" --no-stats         # Skip stats (faster)
    """
    client = get_client()

    with console.status(f"[cyan]Fetching experiments for '{dataset_name}'..."):
        experiments = list(
            client.list_projects(
                reference_dataset_name=dataset_name,
                include_stats=include_stats,
                limit=limit,
            )
        )

    if not experiments:
        console.print(f"[yellow]No experiments found for dataset '{dataset_name}'[/yellow]")
        return

    # Sort by start_time descending (most recent first)
    experiments.sort(
        key=lambda e: e.start_time if hasattr(e, "start_time") and e.start_time else "",
        reverse=True,
    )

    if fmt == "json":
        data = [extract_experiment_summary(e) for e in experiments]
        console.print(Syntax(json.dumps(data, indent=2, default=str), "json", theme="monokai"))
    else:
        console.print(f"[green]✓[/green] Found {len(experiments)} experiment(s) for '{dataset_name}'\n")

        table = Table(show_header=True)
        table.add_column("Name", style="cyan", max_width=40)
        table.add_column("Runs", style="green")
        table.add_column("Latency p50", style="yellow")
        table.add_column("Cost", style="magenta")
        table.add_column("Error Rate", style="red")
        table.add_column("Feedback", style="blue")
        table.add_column("Created", style="dim")

        for exp in experiments:
            # Summarize feedback stats
            feedback_str = ""
            feedback_stats = getattr(exp, "feedback_stats", None)
            if feedback_stats and isinstance(feedback_stats, dict):
                parts = []
                for key, val in feedback_stats.items():
                    if isinstance(val, dict) and "avg" in val:
                        parts.append(f"{key}={val['avg']:.2f}")
                    elif isinstance(val, (int, float)):
                        parts.append(f"{key}={val:.2f}")
                feedback_str = ", ".join(parts[:3])  # Show up to 3 feedback keys
                if len(feedback_stats) > 3:
                    feedback_str += f" +{len(feedback_stats) - 3}"

            created = ""
            if hasattr(exp, "start_time") and exp.start_time:
                created = exp.start_time.strftime("%Y-%m-%d %H:%M")

            table.add_row(
                (exp.name or "N/A")[:40],
                str(getattr(exp, "run_count", "N/A")),
                format_duration(getattr(exp, "latency_p50", None)),
                format_cost(getattr(exp, "total_cost", None)),
                format_pct(getattr(exp, "error_rate", None)),
                feedback_str or "N/A",
                created,
            )

        console.print(table)
        console.print(
            "\n[dim]Tip: Use 'show <dataset> <experiment>' for detailed stats[/dim]"
        )


@cli.command("show")
@click.argument("dataset_name")
@click.argument("experiment_name")
@click.option(
    "--format", "fmt", type=click.Choice(["json", "pretty"]), default="pretty", help="Output format"
)
def show_experiment(dataset_name, experiment_name, fmt):
    """Show detailed stats for one experiment.

    Displays latency (p50/p99), token usage, costs, error rate, and all
    feedback keys with their aggregate scores.

    \b
    Examples:
      show "My Agent Tests" "experiment-v2"
      show "My Agent Tests" "experiment-v2" --format json
    """
    client = get_client()

    with console.status(f"[cyan]Fetching experiment '{experiment_name}'..."):
        experiments = list(
            client.list_projects(
                reference_dataset_name=dataset_name,
                include_stats=True,
            )
        )

    # Find the matching experiment
    match = None
    for exp in experiments:
        if exp.name == experiment_name:
            match = exp
            break

    if not match:
        console.print(f"[red]Experiment '{experiment_name}' not found in dataset '{dataset_name}'[/red]")
        if experiments:
            console.print("\n[dim]Available experiments:[/dim]")
            for exp in experiments[:10]:
                console.print(f"  - {exp.name}")
        return

    if fmt == "json":
        data = extract_experiment_summary(match)
        console.print(Syntax(json.dumps(data, indent=2, default=str), "json", theme="monokai"))
    else:
        console.print(f"[green]✓[/green] Experiment: [bold]{match.name}[/bold]\n")
        console.print(f"  [cyan]ID:[/cyan]         {match.id}")

        created = ""
        if hasattr(match, "start_time") and match.start_time:
            created = match.start_time.strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"  [cyan]Created:[/cyan]    {created}")
        console.print(f"  [cyan]Run count:[/cyan]  {getattr(match, 'run_count', 'N/A')}")

        console.print(f"\n[bold]Performance:[/bold]")
        console.print(f"  Latency p50:  {format_duration(getattr(match, 'latency_p50', None))}")
        console.print(f"  Latency p99:  {format_duration(getattr(match, 'latency_p99', None))}")
        console.print(f"  Total tokens: {getattr(match, 'total_tokens', 'N/A')}")
        console.print(f"  Total cost:   {format_cost(getattr(match, 'total_cost', None))}")
        console.print(f"  Error rate:   {format_pct(getattr(match, 'error_rate', None))}")

        feedback_stats = getattr(match, "feedback_stats", None)
        if feedback_stats and isinstance(feedback_stats, dict):
            console.print(f"\n[bold]Feedback:[/bold]")
            for key, val in sorted(feedback_stats.items()):
                if isinstance(val, dict):
                    avg = val.get("avg", "N/A")
                    count = val.get("count", "N/A")
                    avg_str = f"{avg:.3f}" if isinstance(avg, (int, float)) else str(avg)
                    console.print(f"  {key}: avg={avg_str}, n={count}")
                else:
                    console.print(f"  {key}: {val}")
        else:
            console.print(f"\n[dim]No feedback stats available[/dim]")

        console.print(
            f"\n[dim]Tip: Drill into traces with 'query_traces.py traces list --project \"{match.name}\"'[/dim]"
        )


if __name__ == "__main__":
    cli()
