#!/usr/bin/env python3
"""Query and view LangSmith datasets and local dataset files."""

import json
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from langsmith import Client
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

load_dotenv(override=False)
console = Console()


def get_client() -> Client:
    """Get LangSmith client."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        console.print("[red]Error: LANGSMITH_API_KEY not set[/red]")
        sys.exit(1)
    return Client(api_key=api_key)


def display_examples(examples: list, fmt: str, limit: int):
    """Display examples in pretty or JSON format."""
    if fmt == "json":
        console.print(Syntax(json.dumps(examples[:limit], indent=2, default=str), "json", theme="monokai"))
    else:
        for i, ex in enumerate(examples[:limit], 1):
            console.print(f"[bold]Example {i}:[/bold]")
            if isinstance(ex, dict) and "inputs" in ex and "outputs" in ex:
                # LangSmith format with inputs/outputs
                console.print(Panel(Syntax(json.dumps(ex["inputs"], indent=2, default=str), "json",
                            theme="monokai", line_numbers=False), title="[blue]Inputs[/blue]", border_style="blue"))
                if ex.get("outputs"):
                    console.print(Panel(Syntax(json.dumps(ex["outputs"], indent=2, default=str), "json",
                                theme="monokai", line_numbers=False), title="[green]Outputs[/green]", border_style="green"))
            else:
                # Regular JSON format
                console.print(Syntax(json.dumps(ex, indent=2, default=str), "json", theme="monokai"))
            console.print()


@click.group()
def cli():
    """Query and view datasets"""
    pass


@cli.command()
def list_datasets():
    """List all LangSmith datasets."""
    client = get_client()
    datasets = list(client.list_datasets(limit=100))

    if not datasets:
        console.print("[yellow]No datasets found[/yellow]")
        return

    table = Table(title="LangSmith Datasets", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Description", style="yellow")
    table.add_column("Examples", style="green")

    for ds in datasets:
        table.add_row(
            ds.name,
            str(ds.id)[:16] + "...",
            (ds.description or "")[:50],
            str(ds.example_count or 0)
        )

    console.print(table)


@cli.command()
@click.argument("dataset_name")
@click.option("--limit", default=5, help="Number of examples to show")
@click.option("--format", "fmt", type=click.Choice(["pretty", "json"]), default="pretty")
def show(dataset_name, limit, fmt):
    """Show examples from a LangSmith dataset."""
    client = get_client()
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
    except Exception:
        console.print(f"[red]Error: Dataset '{dataset_name}' not found[/red]")
        return

    examples = [{"inputs": ex.inputs, "outputs": ex.outputs}
                for ex in client.list_examples(dataset_id=dataset.id, limit=limit)]
    if not examples:
        console.print(f"[yellow]No examples in dataset '{dataset_name}'[/yellow]")
        return

    console.print(f"[cyan]Dataset:[/cyan] {dataset.name}")
    console.print(f"[dim]Total examples: {dataset.example_count}[/dim]\n")
    display_examples(examples, fmt, limit)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--limit", default=5, help="Number of examples to show")
@click.option("--format", "fmt", type=click.Choice(["pretty", "json"]), default="pretty")
def view_file(file_path, limit, fmt):
    """View examples from a local dataset file (JSON or CSV)."""
    path = Path(file_path)

    if path.suffix == ".json":
        with open(path) as f:
            content = f.read()
        data = json.loads(content) if content.strip() else []
        data = data if isinstance(data, list) else [data]
        console.print(f"[cyan]File:[/cyan] {path.name}\n[dim]Total: {len(data)}[/dim]\n")
        display_examples(data, fmt, limit)
    elif path.suffix == ".csv":
        import csv
        with open(path) as f:
            rows = list(csv.DictReader(f))
        console.print(f"[cyan]File:[/cyan] {path.name}\n[dim]Total: {len(rows)}[/dim]\n")
        if fmt == "json":
            console.print(Syntax(json.dumps(rows[:limit], indent=2), "json", theme="monokai"))
        else:
            table = Table(show_header=True)
            if rows:
                for col in rows[0].keys():
                    table.add_column(col, style="cyan")
                for row in rows[:limit]:
                    table.add_row(*[str(v)[:100] for v in row.values()])
            console.print(table)
    else:
        console.print(f"[red]Error: Unsupported file type '{path.suffix}'[/red]")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def structure(file_path):
    """Analyze and show the structure of a dataset file."""
    path = Path(file_path)
    console.print(f"[cyan]File:[/cyan] {path.name}")

    if path.suffix == ".json":
        with open(path) as f:
            content = f.read()
        data = json.loads(content) if content.strip() else []
        data = data if isinstance(data, list) else [data]
        console.print(f"[cyan]Format:[/cyan] JSON\n[cyan]Examples:[/cyan] {len(data)}\n")

        if data:
            console.print(f"[bold]Structure:[/bold]\n{json.dumps(data[0], indent=2, default=str)[:500]}\n")
            all_keys = set().union(*[ex.keys() for ex in data if isinstance(ex, dict)])
            console.print("[bold]Fields:[/bold]")
            for key in sorted(all_keys):
                count = sum(1 for ex in data if isinstance(ex, dict) and key in ex)
                console.print(f"  {key}: {count}/{len(data)} ({count/len(data)*100:.0f}%)")
    elif path.suffix == ".csv":
        import csv
        with open(path) as f:
            rows = list(csv.DictReader(f))
        console.print(f"[cyan]Format:[/cyan] CSV\n[cyan]Rows:[/cyan] {len(rows)}\n")

        if rows:
            console.print("[bold]Columns:[/bold]")
            for col in rows[0].keys():
                non_empty = sum(1 for row in rows if row[col])
                console.print(f"  {col}: {non_empty}/{len(rows)} ({non_empty/len(rows)*100:.0f}%)")


@cli.command()
@click.argument("dataset_name")
@click.argument("output_file", type=click.Path())
@click.option("--limit", default=100, help="Number of examples to export")
def export(dataset_name, output_file, limit):
    """Export LangSmith dataset to local file."""
    client = get_client()
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
    except Exception:
        console.print(f"[red]Error: Dataset '{dataset_name}' not found[/red]")
        return

    examples = [{"inputs": ex.inputs, "outputs": ex.outputs}
                for ex in client.list_examples(dataset_id=dataset.id, limit=limit)]
    if not examples:
        console.print(f"[yellow]No examples in dataset '{dataset_name}'[/yellow]")
        return

    with open(Path(output_file), "w") as f:
        json.dump(examples, f, indent=2, default=str)
    console.print(f"[green]✓[/green] Exported {len(examples)} examples to {output_file}")


if __name__ == "__main__":
    cli()
