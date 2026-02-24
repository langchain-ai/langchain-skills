#!/usr/bin/env python3
"""Upload evaluators to LangSmith."""

import inspect
import os
from collections.abc import Callable
from dataclasses import dataclass

import click
import requests
from dotenv import load_dotenv
from langsmith import Client
from rich.console import Console
from rich.table import Table

load_dotenv()

console = Console()

# Configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_API_URL = os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com")
LANGSMITH_WORKSPACE_ID = os.getenv("LANGSMITH_WORKSPACE_ID")

if not LANGSMITH_API_KEY:
    raise ValueError("LANGSMITH_API_KEY environment variable is required")


@dataclass
class CodeEvaluator:
    """Code-based evaluator configuration."""

    code: str
    language: str = "python"


@dataclass
class EvaluatorPayload:
    """Evaluator upload payload."""

    display_name: str
    evaluators: list[CodeEvaluator]
    sampling_rate: float
    target_dataset_ids: list[str] | None = None
    target_project_ids: list[str] | None = None


def get_headers() -> dict:
    """Get API headers with authentication."""
    headers = {"x-api-key": LANGSMITH_API_KEY, "Content-Type": "application/json"}
    if LANGSMITH_WORKSPACE_ID:
        headers["x-tenant-id"] = LANGSMITH_WORKSPACE_ID
    return headers


def find_evaluator(
    name: str, dataset_id: str | None = None, project_id: str | None = None
) -> dict | None:
    """Find evaluator by name and target.

    Returns the matching rule if found, None otherwise.
    Matches by name AND target (dataset_id or project_id).
    """
    url = f"{LANGSMITH_API_URL}/runs/rules"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()

    rules = response.json()
    for rule in rules:
        if rule.get("display_name") != name:
            continue
        # Check target matches
        rule_dataset = rule.get("dataset_id")
        rule_project = rule.get("session_id")  # API uses session_id for project
        if dataset_id and rule_dataset == dataset_id:
            return rule
        if project_id and rule_project == project_id:
            return rule
    return None


def evaluator_exists(name: str) -> bool:
    """Check if evaluator with this name exists (any target)."""
    url = f"{LANGSMITH_API_URL}/runs/rules"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()

    rules = response.json()
    return any(rule.get("display_name") == name for rule in rules)


def resolve_dataset_id(dataset_name: str) -> str | None:
    """Get dataset ID from name."""
    try:
        client = Client()
        dataset = client.read_dataset(dataset_name=dataset_name)
        return str(dataset.id)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not find dataset '{dataset_name}': {e}[/yellow]")
        return None


def resolve_project_id(project_name: str) -> str | None:
    """Get project ID from name."""
    try:
        client = Client()
        # List projects and find matching name
        for project in client.list_projects():
            if project.name == project_name:
                return str(project.id)
        console.print(f"[yellow]Warning: Could not find project '{project_name}'[/yellow]")
        return None
    except Exception as e:
        console.print(f"[yellow]Warning: Error finding project '{project_name}': {e}[/yellow]")
        return None


def create_code_payload(
    name: str,
    func: Callable,
    sample_rate: float = 1.0,
    target_dataset: str | None = None,
    target_project: str | None = None,
    replace: bool = False,
    skip_confirm: bool = False,
) -> EvaluatorPayload | None:
    """Create payload for code-based evaluator.

    Args:
        name: Display name for evaluator
        func: Python function with any name - will be renamed to perform_eval for LangSmith
        sample_rate: Sampling rate (0.0-1.0)
        target_dataset: Optional dataset name to attach to
        target_project: Optional project name to attach to
        replace: If True, delete existing evaluator with same name AND target
    """
    # Resolve targets first (needed for existence check)
    dataset_id = None
    project_id = None

    if target_dataset:
        dataset_id = resolve_dataset_id(target_dataset)
        if not dataset_id:
            return None  # Dataset not found, warning already printed

    if target_project:
        project_id = resolve_project_id(target_project)
        if not project_id:
            return None  # Project not found, warning already printed

    # Check if evaluator exists with same name AND target
    existing = find_evaluator(name, dataset_id=dataset_id, project_id=project_id)

    if existing:
        if not replace:
            target_desc = (
                f"dataset '{target_dataset}'" if target_dataset else f"project '{target_project}'"
            )
            console.print(
                f"[yellow]Evaluator '{name}' already exists for {target_desc}. "
                f"Use --replace to overwrite.[/yellow]"
            )
            return None
        else:
            if not skip_confirm:
                console.print(
                    f"[yellow]⚠️  Evaluator '{name}' already exists with same target.[/yellow]"
                )
                response_text = input("Replace existing evaluator? (y/n): ").lower().strip()
                if response_text != "y":
                    console.print("[yellow]Upload cancelled[/yellow]")
                    return None
            delete_evaluator_by_id(existing.get("id"), name)

    # Get function source code
    source = inspect.getsource(func)

    # LangSmith API requires function to be named 'perform_eval'
    # Replace the function name in the source code
    func_name = func.__name__
    import re

    # Replace "def function_name(" with "def perform_eval("
    source = re.sub(rf"\bdef\s+{re.escape(func_name)}\s*\(", "def perform_eval(", source)

    # Create evaluator
    code_evaluator = CodeEvaluator(code=source, language="python")

    return EvaluatorPayload(
        display_name=name,
        evaluators=[code_evaluator],
        sampling_rate=sample_rate,
        target_dataset_ids=[dataset_id] if dataset_id else None,
        target_project_ids=[project_id] if project_id else None,
    )


def delete_evaluator_by_id(rule_id: str, name: str) -> bool:
    """Delete an evaluator by its ID."""
    delete_url = f"{LANGSMITH_API_URL}/runs/rules/{rule_id}"
    response = requests.delete(delete_url, headers=get_headers())
    response.raise_for_status()
    console.print(f"[green]✓ Deleted evaluator '{name}'[/green]")
    return True


def delete_evaluator(name: str, confirm: bool = True) -> bool:
    """Delete an evaluator by name (for CLI delete command).

    Args:
        name: Evaluator name
        confirm: If True, prompt for confirmation before deleting
    """
    # Get all rules
    url = f"{LANGSMITH_API_URL}/runs/rules"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()

    rules = response.json()
    rule = next((r for r in rules if r.get("display_name") == name), None)

    if not rule:
        console.print(f"[yellow]Evaluator '{name}' not found[/yellow]")
        return False

    # Confirm deletion
    if confirm:
        console.print(f"[yellow]⚠️  About to delete evaluator: '{name}'[/yellow]")
        response_text = input("Are you sure? (y/n): ").lower().strip()
        if response_text != "y":
            console.print("[yellow]Deletion cancelled[/yellow]")
            return False

    return delete_evaluator_by_id(rule.get("id"), name)


def create_evaluator(payload: EvaluatorPayload) -> bool:
    """Upload evaluator to LangSmith."""
    url = f"{LANGSMITH_API_URL}/runs/rules"

    # Convert payload to dict - use code_evaluators for code-based evaluators
    data = {
        "display_name": payload.display_name,
        "sampling_rate": payload.sampling_rate,
        "code_evaluators": [{"code": e.code, "language": e.language} for e in payload.evaluators],
    }

    if payload.target_dataset_ids:
        data["dataset_id"] = (
            payload.target_dataset_ids[0] if len(payload.target_dataset_ids) == 1 else None
        )
    if payload.target_project_ids:
        data["session_id"] = (
            payload.target_project_ids[0] if len(payload.target_project_ids) == 1 else None
        )

    # Upload
    response = requests.post(url, json=data, headers=get_headers())

    if response.status_code == 200:
        console.print(f"[green]✓ Uploaded evaluator '{payload.display_name}'[/green]")
        return True
    else:
        console.print(f"[red]✗ Failed to upload '{payload.display_name}': {response.text}[/red]")
        return False


@click.group()
def cli():
    """Upload and manage LangSmith evaluators."""
    pass


@cli.command()
def list():
    """List all evaluators."""
    url = f"{LANGSMITH_API_URL}/runs/rules"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()

    rules = response.json()

    if not rules:
        console.print("[yellow]No evaluators found[/yellow]")
        return

    table = Table(title="LangSmith Evaluators")
    table.add_column("Name", style="cyan")
    table.add_column("Sampling Rate", style="green")
    table.add_column("Targets", style="yellow")

    for rule in rules:
        name = rule.get("display_name", "")
        rate = rule.get("sampling_rate", 1.0)

        # API returns dataset_id/session_id for individual rule targets
        targets = []
        if rule.get("dataset_id"):
            targets.append("1 dataset")
        if rule.get("session_id"):
            targets.append("1 project")

        table.add_row(name, f"{rate:.1%}", ", ".join(targets) if targets else "All runs")

    console.print(table)


@cli.command()
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
def delete(name: str, yes: bool):
    """Delete an evaluator by name."""
    delete_evaluator(name, confirm=not yes)


@cli.command()
@click.argument("evaluator_file")
@click.option("--name", required=True, help="Display name for evaluator")
@click.option("--function", required=True, help="Function name to extract from file")
@click.option("--dataset", help="Target dataset name (offline evaluator - receives run, example)")
@click.option("--project", help="Target project name (online evaluator - receives run only)")
@click.option("--sample-rate", default=1.0, type=float, help="Sampling rate (0.0-1.0)")
@click.option("--replace", is_flag=True, help="Replace if exists")
@click.option("--yes", is_flag=True, help="Skip confirmation prompts")
def upload(
    evaluator_file: str,
    name: str,
    function: str,
    dataset: str | None,
    project: str | None,
    sample_rate: float,
    replace: bool,
    yes: bool,
):
    """Upload an evaluator from a Python file.

    IMPORTANT: You must specify either --dataset or --project.
    - --dataset: Offline evaluator. Function signature: (run, example)
    - --project: Online evaluator. Function signature: (run)

    Global evaluators (no target) are not supported to prevent signature mismatches.

    Example:
        python upload_evaluators.py upload my_evaluators.py \\
            --name "Trajectory Match" \\
            --function trajectory_match_evaluator \\
            --dataset "Skills: Trajectory" \\
            --replace
    """
    # Require either dataset or project to prevent global evaluators
    if not dataset and not project:
        console.print(
            "[red]Error: You must specify either --dataset or --project.[/red]\n"
            "[yellow]  --dataset: Offline evaluator with (run, example) signature[/yellow]\n"
            "[yellow]  --project: Online evaluator with (run) signature[/yellow]\n"
            "[dim]Global evaluators are not supported to prevent signature mismatches.[/dim]"
        )
        return
    # Load the Python file
    import importlib.util

    spec = importlib.util.spec_from_file_location("evaluators", evaluator_file)
    if not spec or not spec.loader:
        console.print(f"[red]Failed to load {evaluator_file}[/red]")
        return

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Get the function
    if not hasattr(module, function):
        console.print(f"[red]Function '{function}' not found in {evaluator_file}[/red]")
        return

    func = getattr(module, function)

    # Create payload
    payload = create_code_payload(
        name=name,
        func=func,
        sample_rate=sample_rate,
        target_dataset=dataset,
        target_project=project,
        replace=replace,
        skip_confirm=yes,
    )

    if payload:
        create_evaluator(payload)


if __name__ == "__main__":
    cli()
