#!/usr/bin/env python3
"""Generate evaluation datasets from LangSmith traces.

Extracts real data from traces to create datasets for:
1. Final Response - Full conversation with expected output
2. Single Step - First decision/classification
3. Trajectory - Tool call sequence
4. RAG - Question/chunks/answer/citations

All datasets are auto-generated from actual trace data.
"""

import csv
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Dict

import click
from dotenv import load_dotenv
from langsmith import Client
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

load_dotenv(override=False)
console = Console()


# ============================================================================
# Helpers
# ============================================================================

def get_client() -> Client:
    """Get LangSmith client."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        console.print("[red]Error: LANGSMITH_API_KEY not set[/red]")
        sys.exit(1)
    return Client(api_key=api_key)


def fetch_traces_with_data(client: Client, project: str, limit: int, last_n_minutes: int | None = None, root_run_name: str | None = None) -> List[tuple]:
    """Fetch traces with full run data."""
    params = {"is_root": True, "limit": limit * 3 if root_run_name else limit, "project_name": project}
    if last_n_minutes:
        params["start_time"] = datetime.now(timezone.utc) - timedelta(minutes=last_n_minutes)

    traces = []
    with Progress(SpinnerColumn(), TextColumn("[cyan]Fetching {task.completed}/{task.total} traces..."), BarColumn()) as p:
        task = p.add_task("fetch", total=limit)
        for root in client.list_runs(**params):
            # Filter by root run name if specified
            if root_run_name and root.name != root_run_name:
                continue
            trace_id = str(getattr(root, "trace_id", root.id))
            traces.append((trace_id, root, list(client.list_runs(trace_id=trace_id, project_name=project, limit=100))))
            p.update(task, advance=1)
            if len(traces) >= limit:
                break
    return traces


def get_first_human_message(inputs: dict) -> str:
    """Extract first human message from inputs."""
    if not inputs:
        return ""
    messages = inputs.get("messages", inputs.get("input", []))
    if isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict) and (msg.get("type") == "human" or msg.get("role") == "user"):
                return msg.get("content", "")
            elif isinstance(msg, str):
                return msg
    return str(messages) if isinstance(messages, str) else ""


def get_final_ai_message(runs: List, output_fields: List[str] = None, messages_only: bool = False) -> str:
    """Extract final response from trace outputs.

    Args:
        runs: List of runs to search
        output_fields: Specific output keys to extract (e.g., ["answer", "result"])
        messages_only: If True, only extract from messages, ignore output fields
    """
    for run in sorted(runs, key=lambda r: r.start_time or datetime.min, reverse=True):
        if not run.outputs:
            continue
        if isinstance(run.outputs, dict):
            # Priority 1: Check messages for final AI content
            if msgs := run.outputs.get("messages"):
                last = msgs[-1] if isinstance(msgs, list) and msgs else msgs
                content = last.get("content", str(last)) if isinstance(last, dict) else str(last)
                if content and content != "None":
                    return content

            # If messages_only, skip output fields
            if messages_only:
                continue

            # Priority 2: Check user-specified output fields
            if output_fields:
                for key in output_fields:
                    if val := run.outputs.get(key):
                        return str(val)

            # Priority 3: Check common output keys
            for key in ["answer", "output"]:
                if val := run.outputs.get(key):
                    return str(val)

            # Priority 4: Return whole output
            return json.dumps(run.outputs)
        return str(run.outputs)
    return ""


def extract_tool_sequence(runs: List, depth: int = None) -> List[str]:
    """Extract ordered tool call names from runs."""
    parent_map = {r.id: r.parent_run_id for r in runs}

    def get_depth(run_id):
        d, current = 0, run_id
        while parent_map.get(current):
            d, current = d + 1, parent_map[current]
        return d

    return [r.name.lower() for r in sorted(runs, key=lambda r: r.start_time or datetime.min)
            if r.run_type == "tool" and (depth is None or get_depth(r.id) <= depth)]


def get_node_io(runs: List, run_name: str = None) -> List[dict]:
    """Extract inputs and outputs from all occurrences of a specific node/run.

    Returns list of I/O pairs, capturing conversation evolution across multiple invocations.
    """
    target = [r for r in runs if r.name == run_name] if run_name else runs
    results = []
    for run in sorted(target, key=lambda r: r.start_time or datetime.min):
        if run.outputs:
            results.append({
                "node_name": run.name,
                "inputs": run.inputs or {},
                "outputs": run.outputs,
                "run_id": str(run.id)
            })
    return results


def find_retrieval_data(runs: List) -> dict:
    """Extract retrieval data (query, chunks, answer) from runs."""
    data = {"query": "", "retrieved_chunks": [], "answer": ""}

    # Find retriever runs (prioritize retriever type, fallback to search tools)
    ret_runs = [r for r in runs if r.run_type == "retriever"] or [
        r for r in runs if r.run_type == "tool" and ("retriev" in r.name.lower() or "search" in r.name.lower())]

    for run in sorted(ret_runs, key=lambda r: r.start_time or datetime.min):
        if run.inputs and isinstance(run.inputs, dict):
            data["query"] = run.inputs.get("query", run.inputs.get("question", ""))

        if run.outputs and isinstance(run.outputs, dict):
            docs = run.outputs.get("documents", run.outputs.get("results", run.outputs.get("chunks")))
            if docs and isinstance(docs, list):
                for doc in docs:
                    if isinstance(doc, dict):
                        if content := doc.get("page_content", doc.get("content", doc.get("text"))):
                            data["retrieved_chunks"].append(content)
                    elif isinstance(doc, str):
                        data["retrieved_chunks"].append(doc)
        if not data["retrieved_chunks"] and run.outputs:
            data["retrieved_chunks"].append(str(run.outputs))

    data["answer"] = get_final_ai_message(runs)
    return data


# ============================================================================
# Dataset Generators
# ============================================================================

def generate_dataset(traces: List[tuple], dataset_type: str, run_name: str = None, depth: int = None,
                     output_fields: List[str] = None, messages_only: bool = False, sample_per_trace: int = None) -> List[dict]:
    """Generate evaluation dataset from traces based on type."""
    dataset = []

    for trace_id, root, runs in traces:
        if dataset_type == "rag":
            rag_data = find_retrieval_data(runs)
            if not (rag_data["query"] and rag_data["answer"]):
                continue
            dataset.append({
                "trace_id": trace_id,
                "question": rag_data["query"],
                "retrieved_chunks": "\n\n".join(rag_data["retrieved_chunks"]),
                "answer": rag_data["answer"],
                "cited_chunks": json.dumps(rag_data["retrieved_chunks"][:3])
            })
        else:
            input_msg = get_first_human_message(root.inputs)
            if not input_msg:
                continue

            # Build outputs based on type
            if dataset_type == "final_response":
                # For final response, check the root run first for messages
                output = get_final_ai_message([root], output_fields=output_fields, messages_only=messages_only)
                if not output:
                    continue
                outputs = {"expected_response": output}
            elif dataset_type == "single_step":
                node_io_list = get_node_io(runs, run_name=run_name)
                if not node_io_list:
                    continue
                # Sample if requested, otherwise use all
                if sample_per_trace and len(node_io_list) > sample_per_trace:
                    sampled = random.sample(node_io_list, sample_per_trace)
                else:
                    sampled = node_io_list
                # Create separate examples for each occurrence
                for idx, node_io in enumerate(sampled):
                    dataset.append({
                        "trace_id": trace_id,
                        "run_id": node_io["run_id"],
                        "occurrence": idx + 1,
                        "inputs": node_io["inputs"],
                        "outputs": {"expected_output": node_io["outputs"], "node_name": node_io["node_name"]}
                    })
                continue
            elif dataset_type == "trajectory":
                tools = extract_tool_sequence(runs, depth=depth)
                if not tools:
                    continue
                outputs = {"expected_trajectory": tools}
            else:
                continue

            # Preserve full inputs from trace for exact ground truth matching
            dataset.append({"trace_id": trace_id, "inputs": root.inputs or {"query": input_msg}, "outputs": outputs})

    return dataset


# ============================================================================
# Export Functions
# ============================================================================

def export_to_file(dataset: List[dict], output_path: Path):
    """Export dataset to JSON or CSV based on file extension."""
    if not dataset:
        console.print("[yellow]No data to export[/yellow]")
        return

    if output_path.suffix == ".csv":
        fieldnames = sorted(set().union(*[ex.keys() for ex in dataset]))
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dataset)
    else:
        with open(output_path, "w") as f:
            json.dump(dataset, f, indent=2, default=str)

    console.print(f"[green]✓[/green] Exported {len(dataset)} examples to {output_path}")


def export_to_langsmith(client: Client, dataset: List[dict], dataset_name: str, dataset_type: str):
    """Upload dataset to LangSmith."""
    try:
        ds = client.create_dataset(dataset_name=dataset_name,
                                   description=f"{dataset_type} evaluation dataset (auto-generated)")
        console.print(f"[green]✓[/green] Created dataset: {dataset_name}")
    except Exception:
        ds = client.read_dataset(dataset_name=dataset_name)
        console.print(f"[yellow]Using existing: {dataset_name}[/yellow]")

    if dataset_type == "rag":
        inputs = [{"question": ex["question"], "retrieved_chunks": ex["retrieved_chunks"]} for ex in dataset]
        outputs = [{"answer": ex["answer"], "cited_chunks": ex["cited_chunks"]} for ex in dataset]
    else:
        inputs, outputs = [ex["inputs"] for ex in dataset], [ex["outputs"] for ex in dataset]

    client.create_examples(inputs=inputs, outputs=outputs, dataset_id=ds.id)
    console.print(f"[green]✓[/green] Added {len(dataset)} examples")


# ============================================================================
# CLI
# ============================================================================

@click.command()
@click.option("--type", "dataset_type",
              type=click.Choice(["final_response", "single_step", "trajectory", "rag"]),
              required=True,
              help="Dataset type to generate")
@click.option("--project", required=True, help="Project name")
@click.option("--limit", default=30, help="Number of traces (default: 30)")
@click.option("--last-n-minutes", type=int, help="Recent traces only")
@click.option("--root-run-name", help="Filter traces by root run name (e.g., 'LangGraph')")
@click.option("--output", "-o", required=True, help="Output file (JSON or CSV)")
@click.option("--upload", help="Upload to LangSmith dataset with this name")
@click.option("--run-name", help="For single_step: specific node/function name to extract inputs/outputs from")
@click.option("--depth", type=int, help="For trajectory: max hierarchy depth (0=root only, omit for all)")
@click.option("--output-fields", help="For final_response: comma-separated output keys (e.g., 'answer,result')")
@click.option("--messages-only", is_flag=True, help="For final_response: only extract from messages, ignore output fields")
@click.option("--sample-per-trace", type=int, help="For single_step: max examples to sample per trace (default: all)")
@click.option("--replace", is_flag=True, help="Replace existing file/dataset (default: skip if exists)")
@click.option("--yes", is_flag=True, help="Skip confirmation prompts for replace operations")
def generate(dataset_type, project, limit, last_n_minutes, root_run_name, output, upload, run_name, depth, output_fields, messages_only, sample_per_trace, replace, yes):
    """Generate evaluation datasets from LangSmith traces.

    Dataset types:
      final_response - Full conversation with expected output
      single_step    - Single node inputs/outputs (use --run-name to target specific node)
      trajectory     - Tool call sequence (use --depth to control subagent inclusion)
      rag            - Question/chunks/answer/citations
    """
    client = get_client()
    output_path = Path(output)

    # Check if output file exists
    if output_path.exists() and not replace:
        console.print(f"[yellow]⚠ File {output_path} already exists. Use --replace to overwrite.[/yellow]")
        return

    # Check if LangSmith dataset exists
    if upload and not replace:
        try:
            client.read_dataset(dataset_name=upload)
            console.print(f"[yellow]⚠ LangSmith dataset '{upload}' already exists. Use --replace to overwrite.[/yellow]")
            return
        except Exception:
            pass  # Dataset doesn't exist, proceed

    console.print(f"[cyan]Generating {dataset_type} dataset from {project}...[/cyan]")
    if root_run_name:
        console.print(f"[cyan]Filtering for root run name: {root_run_name}[/cyan]")
    if dataset_type == "single_step" and run_name:
        console.print(f"[cyan]Targeting run name: {run_name}[/cyan]")
        if sample_per_trace:
            console.print(f"[cyan]Sampling {sample_per_trace} occurrence(s) per trace[/cyan]")
    if dataset_type == "trajectory" and depth is not None:
        console.print(f"[cyan]Max hierarchy depth: {depth}[/cyan]")

    traces = fetch_traces_with_data(client, project, limit, last_n_minutes, root_run_name)
    console.print(f"[green]✓[/green] Fetched {len(traces)} traces")

    # Parse output_fields if provided
    fields_list = output_fields.split(",") if output_fields else None

    dataset = generate_dataset(traces, dataset_type, run_name=run_name, depth=depth,
                               output_fields=fields_list, messages_only=messages_only, sample_per_trace=sample_per_trace)
    if not dataset:
        console.print("[yellow]No valid examples found in traces[/yellow]")
        return

    export_to_file(dataset, output_path)
    if upload:
        if replace:
            try:
                existing = client.read_dataset(dataset_name=upload)
                # Confirm deletion
                if not yes:
                    console.print(f"[yellow]⚠️  About to delete dataset: '{upload}'[/yellow]")
                    response_text = input("Are you sure? (y/n): ").lower().strip()
                    if response_text != 'y':
                        console.print("[yellow]Upload cancelled[/yellow]")
                        return
                client.delete_dataset(dataset_id=existing.id)
                console.print(f"[yellow]Deleted existing dataset: {upload}[/yellow]")
            except Exception:
                pass
        export_to_langsmith(client, dataset, upload, dataset_type)


if __name__ == "__main__":
    generate()
