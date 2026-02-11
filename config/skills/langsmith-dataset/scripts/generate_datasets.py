#!/usr/bin/env python3
"""Generate evaluation datasets from exported trace files.

Workflow:
  1. Export traces using langsmith-trace skill: query_traces.py export ./traces
  2. Generate datasets from those traces: generate_datasets.py --input ./traces --type final_response

Dataset types:
  - final_response: Full conversation with expected output
  - single_step: Single node inputs/outputs
  - trajectory: Tool/node call sequence
  - rag: Question/chunks/answer/citations
"""

import csv
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import List

import click
from dotenv import load_dotenv
from langsmith import Client
from rich.console import Console

load_dotenv(override=False)
console = Console()


# ============================================================================
# Trace Loading
# ============================================================================

def dict_to_obj(d: dict) -> SimpleNamespace:
    """Convert dict to object with attribute access."""
    obj = SimpleNamespace(**d)
    # Parse datetime strings
    if hasattr(obj, 'start_time') and isinstance(obj.start_time, str):
        try:
            obj.start_time = datetime.fromisoformat(obj.start_time.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            obj.start_time = None
    return obj


def load_traces_from_dir(input_dir: Path) -> List[tuple]:
    """Load trace data from exported JSONL or JSON files.

    Returns list of (trace_id, root_run, all_runs) tuples.
    """
    from collections import defaultdict

    traces = []
    # Support both .jsonl (preferred) and .json (legacy)
    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    json_files = sorted(input_dir.glob("*.json"))

    if not jsonl_files and not json_files:
        console.print(f"[yellow]No JSONL/JSON files found in {input_dir}[/yellow]")
        return traces

    # Process JSONL files (one run per line, group by trace_id)
    for file_path in jsonl_files:
        try:
            runs_by_trace = defaultdict(list)
            with open(file_path) as f:
                for line in f:
                    if line.strip():
                        run_data = json.loads(line)
                        trace_id = run_data.get("trace_id", file_path.stem)
                        runs_by_trace[trace_id].append(dict_to_obj(run_data))

            for trace_id, runs in runs_by_trace.items():
                if runs:
                    root = next((r for r in runs if not getattr(r, 'parent_run_id', None)), runs[0])
                    traces.append((trace_id, root, runs))
        except (json.JSONDecodeError, KeyError) as e:
            console.print(f"[yellow]Warning: Skipping {file_path.name}: {e}[/yellow]")

    # Process legacy JSON files (backwards compatibility)
    for file_path in json_files:
        try:
            with open(file_path) as f:
                data = json.load(f)

            trace_id = data.get("trace_id", file_path.stem)
            runs_data = data.get("runs", [])

            if not runs_data:
                continue

            runs = [dict_to_obj(r) for r in runs_data]
            root = next((r for r in runs if not getattr(r, 'parent_run_id', None)), runs[0])
            traces.append((trace_id, root, runs))
        except (json.JSONDecodeError, KeyError) as e:
            console.print(f"[yellow]Warning: Skipping {file_path.name}: {e}[/yellow]")

    return traces


def load_traces_from_file(input_file: Path) -> List[tuple]:
    """Load traces from a single JSONL or JSON file."""
    from collections import defaultdict

    traces = []

    # JSONL format (one run per line)
    if input_file.suffix == ".jsonl":
        runs_by_trace = defaultdict(list)
        with open(input_file) as f:
            for line in f:
                if line.strip():
                    run_data = json.loads(line)
                    trace_id = run_data.get("trace_id", "unknown")
                    runs_by_trace[trace_id].append(dict_to_obj(run_data))

        for trace_id, runs in runs_by_trace.items():
            if runs:
                root = next((r for r in runs if not getattr(r, 'parent_run_id', None)), runs[0])
                traces.append((trace_id, root, runs))
        return traces

    # Legacy JSON format
    with open(input_file) as f:
        data = json.load(f)

    # Handle array of traces or single trace
    if isinstance(data, list):
        items = data
    else:
        items = [data]

    for item in items:
        trace_id = item.get("trace_id", "unknown")
        runs_data = item.get("runs", [])

        if not runs_data:
            continue

        runs = [dict_to_obj(r) for r in runs_data]
        root = next((r for r in runs if not getattr(r, 'parent_run_id', None)), runs[0])
        traces.append((trace_id, root, runs))

    return traces


# ============================================================================
# Extraction Helpers
# ============================================================================

# Common field names for inputs and outputs
COMMON_INPUT_FIELDS = ["query", "input", "question", "message", "prompt", "text"]
COMMON_OUTPUT_FIELDS = ["answer", "output", "response", "result"]


def extract_from_messages(messages: list, role: str = None) -> str:
    """Extract content from a messages array.

    Args:
        messages: List of message dicts
        role: Target role - "human"/"user" for inputs, "ai"/"assistant" for outputs, None for last
    """
    if not messages or not isinstance(messages, list):
        return None

    if role in ("human", "user"):
        # Find first human/user message
        for msg in messages:
            if isinstance(msg, dict) and (msg.get("type") == "human" or msg.get("role") == "user"):
                return msg.get("content", "")
            elif isinstance(msg, str):
                return msg
    elif role in ("ai", "assistant"):
        # Find last AI/assistant message
        for msg in reversed(messages):
            if isinstance(msg, dict) and (msg.get("type") == "ai" or msg.get("role") == "assistant"):
                content = msg.get("content", "")
                if content and content != "None":
                    return content
    else:
        # Return last message content
        last = messages[-1] if messages else None
        if isinstance(last, dict):
            return last.get("content", str(last))
        elif isinstance(last, str):
            return last

    return None


def extract_value(data: dict, fields: List[str] = None, common_fields: List[str] = None,
                  message_role: str = None, fallback_to_raw: bool = True) -> any:
    """Extract a value from a dict with configurable priority.

    Priority order:
    1. User-specified fields (if provided)
    2. Messages array (if present)
    3. Common fields
    4. Raw dict/first string value (if fallback_to_raw=True)

    Args:
        data: Dict to extract from
        fields: User-specified field names to try first
        common_fields: Common field names to try as fallback
        message_role: Role for message extraction ("human"/"user" or "ai"/"assistant")
        fallback_to_raw: Whether to return raw data if nothing else matches
    """
    if not data:
        return None

    # Priority 1: User-specified fields
    if fields:
        for field in fields:
            if val := data.get(field):
                return val

    # Priority 2: Messages array
    if messages := data.get("messages"):
        if content := extract_from_messages(messages, role=message_role):
            return content

    # Priority 3: Common fields
    if common_fields:
        for field in common_fields:
            if val := data.get(field):
                return val

    # Priority 4: Fallback to raw
    if fallback_to_raw:
        # Single string value
        if len(data) == 1:
            val = list(data.values())[0]
            if isinstance(val, str):
                return val
        # First string value found
        for val in data.values():
            if isinstance(val, str) and val:
                return val
        # Return whole dict
        return data

    return None


def extract_trace_inputs(root, input_fields: List[str] = None, as_dict: bool = True) -> any:
    """Extract inputs from a trace's root run.

    Args:
        root: Root run object
        input_fields: Specific fields to extract (takes priority)
        as_dict: If True, return raw dict when no input_fields specified.
                 If False, extract a value using the priority system.

    Returns:
        Raw inputs dict, or extracted value if input_fields provided
    """
    inputs = getattr(root, 'inputs', None) or {}

    if not inputs:
        return {} if as_dict else None

    # If input_fields specified, extract specific value
    if input_fields:
        result = extract_value(
            inputs,
            fields=input_fields,
            common_fields=COMMON_INPUT_FIELDS,
            message_role="human",
            fallback_to_raw=True
        )
        return result

    # Return raw dict or extract value based on as_dict flag
    if as_dict:
        return inputs

    return extract_value(
        inputs,
        fields=None,
        common_fields=COMMON_INPUT_FIELDS,
        message_role="human",
        fallback_to_raw=True
    )


def extract_trace_output(root, output_fields: List[str] = None, messages_only: bool = False) -> any:
    """Extract output from a trace's root run.

    Args:
        root: Root run object
        output_fields: Specific fields to extract (takes priority)
        messages_only: Only extract from messages, skip other fields
    """
    outputs = getattr(root, 'outputs', None) or {}

    if not outputs:
        return None

    result = extract_value(
        outputs,
        fields=output_fields,
        common_fields=None if messages_only else COMMON_OUTPUT_FIELDS,
        message_role="ai",
        fallback_to_raw=not messages_only
    )

    # Convert dict to JSON string for final response
    if isinstance(result, dict):
        return json.dumps(result)

    return result


def extract_final_output(runs: List, output_fields: List[str] = None) -> str:
    """Extract the final output from a list of runs (searches latest first).

    Used for RAG and other cases where the answer may come from any run.
    """
    for run in sorted(runs, key=lambda r: getattr(r, 'start_time', None) or datetime.min, reverse=True):
        outputs = getattr(run, 'outputs', None)
        if not outputs:
            continue

        result = extract_value(
            outputs if isinstance(outputs, dict) else {"output": outputs},
            fields=output_fields,
            common_fields=COMMON_OUTPUT_FIELDS,
            message_role="ai",
            fallback_to_raw=True
        )

        if result:
            if isinstance(result, dict):
                return json.dumps(result)
            return str(result)

    return ""


def extract_tool_sequence(runs: List, depth: int = None) -> List[str]:
    """Extract ordered tool call names from runs."""
    parent_map = {getattr(r, 'run_id', getattr(r, 'id', None)): getattr(r, 'parent_run_id', None) for r in runs}

    def get_depth(run_id):
        d, current = 0, run_id
        while parent_map.get(current):
            d, current = d + 1, parent_map[current]
        return d

    result = []
    for r in sorted(runs, key=lambda r: getattr(r, 'start_time', None) or datetime.min):
        run_type = getattr(r, 'run_type', None)
        run_id = getattr(r, 'run_id', getattr(r, 'id', None))
        if run_type == "tool" and (depth is None or get_depth(run_id) <= depth):
            result.append(getattr(r, 'name', 'unknown').lower())
    return result


def get_node_io(runs: List, run_name: str = None) -> List[dict]:
    """Extract inputs and outputs from all occurrences of a specific node/run."""
    target = [r for r in runs if getattr(r, 'name', None) == run_name] if run_name else runs
    results = []
    for run in sorted(target, key=lambda r: getattr(r, 'start_time', None) or datetime.min):
        outputs = getattr(run, 'outputs', None)
        if outputs:
            results.append({
                "node_name": getattr(run, 'name', 'unknown'),
                "inputs": getattr(run, 'inputs', {}) or {},
                "outputs": outputs,
                "run_id": str(getattr(run, 'run_id', getattr(run, 'id', '')))
            })
    return results


def extract_documents(outputs: any) -> List[str]:
    """Extract document contents from retriever outputs.

    Handles LangChain Document format (list of dicts with page_content).
    Returns raw output as string if not in Document format.
    """
    if not outputs:
        return []

    # If outputs is a dict, look for common document list keys
    if isinstance(outputs, dict):
        docs = outputs.get("documents") or outputs.get("output") or outputs
        if isinstance(docs, dict):
            docs = [docs]
    else:
        docs = outputs if isinstance(outputs, list) else [outputs]

    if not isinstance(docs, list):
        return [str(outputs)]

    results = []
    for doc in docs:
        if isinstance(doc, dict):
            # LangChain Document format: {"page_content": "...", "metadata": {...}}
            if page_content := doc.get("page_content"):
                results.append(page_content)
            # Fallback to other content fields
            elif content := doc.get("content") or doc.get("text"):
                results.append(content)
            else:
                # Return raw doc as JSON
                results.append(json.dumps(doc))
        elif isinstance(doc, str):
            results.append(doc)
        else:
            results.append(str(doc))

    return results


def find_retrieval_data(runs: List) -> dict:
    """Extract retrieval data (query, chunks, answer) from runs.

    Looks for runs with run_type="retriever" and extracts:
    - query: from inputs (using common field extraction)
    - retrieved_chunks: LangChain Documents if present, otherwise raw outputs
    - answer: final output from the trace
    """
    data = {"query": "", "retrieved_chunks": [], "answer": ""}

    # Find retriever runs by run_type only
    ret_runs = [r for r in runs if getattr(r, 'run_type', None) == "retriever"]

    for run in sorted(ret_runs, key=lambda r: getattr(r, 'start_time', None) or datetime.min):
        # Extract query from inputs
        inputs = getattr(run, 'inputs', None)
        if inputs and isinstance(inputs, dict) and not data["query"]:
            data["query"] = extract_value(
                inputs,
                fields=None,
                common_fields=COMMON_INPUT_FIELDS,
                message_role="human",
                fallback_to_raw=False
            ) or ""

        # Extract documents from outputs
        outputs = getattr(run, 'outputs', None)
        if outputs:
            data["retrieved_chunks"].extend(extract_documents(outputs))

    data["answer"] = extract_final_output(runs)
    return data


# ============================================================================
# Dataset Generation
# ============================================================================

def generate_dataset(traces: List[tuple], dataset_type: str, run_name: str = None, depth: int = None,
                     input_fields: List[str] = None, output_fields: List[str] = None,
                     messages_only: bool = False, sample_per_trace: int = None) -> List[dict]:
    """Generate evaluation dataset from traces based on type.

    Args:
        traces: List of (trace_id, root_run, all_runs) tuples
        dataset_type: One of "final_response", "single_step", "trajectory", "rag"
        run_name: For single_step - target specific node name
        depth: For trajectory - max hierarchy depth
        input_fields: Specific input fields to extract (e.g., ["query", "question"])
        output_fields: Specific output fields to extract (e.g., ["answer", "response"])
        messages_only: Only extract from messages, skip other fields
        sample_per_trace: For single_step - max examples per trace
    """
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
            # Extract inputs - use input_fields if specified, otherwise raw dict
            root_inputs = extract_trace_inputs(root, input_fields=input_fields, as_dict=(input_fields is None))

            # Skip traces with no inputs at all
            if not root_inputs:
                continue

            # Format inputs for dataset
            if input_fields and not isinstance(root_inputs, dict):
                # If specific fields extracted, wrap in expected_input
                inputs = {"expected_input": root_inputs}
            else:
                inputs = root_inputs

            if dataset_type == "final_response":
                output = extract_trace_output(root, output_fields=output_fields, messages_only=messages_only)
                if not output:
                    continue
                outputs = {"expected_response": output}
            elif dataset_type == "single_step":
                node_io_list = get_node_io(runs, run_name=run_name)
                if not node_io_list:
                    continue
                if sample_per_trace and len(node_io_list) > sample_per_trace:
                    sampled = random.sample(node_io_list, sample_per_trace)
                else:
                    sampled = node_io_list
                for idx, node_io in enumerate(sampled):
                    dataset.append({
                        "trace_id": trace_id,
                        "run_id": node_io["run_id"],
                        "node_name": node_io["node_name"],
                        "occurrence": idx + 1,
                        "inputs": node_io["inputs"],
                        "outputs": {"expected_output": node_io["outputs"]}
                    })
                continue
            elif dataset_type == "trajectory":
                tools = extract_tool_sequence(runs, depth=depth)
                if not tools:
                    continue
                outputs = {"expected_trajectory": tools}
            else:
                continue

            dataset.append({"trace_id": trace_id, "inputs": inputs, "outputs": outputs})

    return dataset


# ============================================================================
# Export Functions
# ============================================================================

def get_client() -> Client:
    """Get LangSmith client for upload."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        console.print("[red]Error: LANGSMITH_API_KEY not set[/red]")
        sys.exit(1)
    return Client(api_key=api_key)


def export_to_file(dataset: List[dict], output_path: Path):
    """Export dataset to JSON or CSV."""
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
@click.option("--input", "-i", "input_path", required=True,
              help="Input traces: directory of JSONL files or single JSONL file (from query_traces.py export)")
@click.option("--type", "dataset_type",
              type=click.Choice(["final_response", "single_step", "trajectory", "rag"]),
              required=True, help="Dataset type to generate")
@click.option("--output", "-o", required=True, help="Output file (JSON or CSV)")
@click.option("--upload", help="Upload to LangSmith dataset with this name")
@click.option("--run-name", help="For single_step: target specific node name")
@click.option("--depth", type=int, help="For trajectory: max hierarchy depth")
@click.option("--input-fields", help="Comma-separated input keys to extract (e.g., 'query,question')")
@click.option("--output-fields", help="Comma-separated output keys to extract (e.g., 'answer,response')")
@click.option("--messages-only", is_flag=True, help="For final_response: only extract from messages")
@click.option("--sample-per-trace", type=int, help="For single_step: max examples per trace")
@click.option("--replace", is_flag=True, help="Replace existing file/dataset")
@click.option("--yes", is_flag=True, help="Skip confirmation prompts")
def generate(input_path, dataset_type, output, upload, run_name, depth, input_fields, output_fields, messages_only, sample_per_trace, replace, yes):
    """Generate evaluation datasets from exported JSONL trace files.

    \b
    Workflow:
      1. Export traces: query_traces.py export ./traces --project myproject --include-io
      2. Generate dataset: generate_datasets.py --input ./traces --type final_response -o dataset.json

    \b
    Dataset types:
      final_response - Full conversation with expected output
      single_step    - Single node inputs/outputs (use --run-name)
      trajectory     - Tool call sequence (use --depth)
      rag            - Question/chunks/answer/citations
    """
    input_path = Path(input_path)
    output_path = Path(output)

    # Check output exists
    if output_path.exists() and not replace:
        console.print(f"[yellow]File {output_path} exists. Use --replace to overwrite.[/yellow]")
        return

    # Load traces
    if input_path.is_dir():
        traces = load_traces_from_dir(input_path)
    elif input_path.is_file():
        traces = load_traces_from_file(input_path)
    else:
        console.print(f"[red]Error: {input_path} not found[/red]")
        return

    if not traces:
        console.print("[yellow]No valid traces found[/yellow]")
        return

    console.print(f"[green]✓[/green] Loaded {len(traces)} traces from {input_path}")

    # Generate dataset
    input_fields_list = input_fields.split(",") if input_fields else None
    output_fields_list = output_fields.split(",") if output_fields else None
    dataset = generate_dataset(traces, dataset_type, run_name=run_name, depth=depth,
                               input_fields=input_fields_list, output_fields=output_fields_list,
                               messages_only=messages_only, sample_per_trace=sample_per_trace)

    if not dataset:
        console.print("[yellow]No valid examples found in traces[/yellow]")
        return

    # Export
    export_to_file(dataset, output_path)

    # Upload to LangSmith if requested
    if upload:
        client = get_client()
        if replace:
            try:
                existing = client.read_dataset(dataset_name=upload)
                if not yes:
                    console.print(f"[yellow]About to delete dataset: '{upload}'[/yellow]")
                    if input("Are you sure? (y/n): ").lower().strip() != 'y':
                        console.print("[yellow]Upload cancelled[/yellow]")
                        return
                client.delete_dataset(dataset_id=existing.id)
                console.print(f"[yellow]Deleted existing dataset: {upload}[/yellow]")
            except Exception:
                pass
        export_to_langsmith(client, dataset, upload, dataset_type)


if __name__ == "__main__":
    generate()
