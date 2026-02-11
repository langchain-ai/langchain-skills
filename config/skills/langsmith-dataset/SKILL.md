---
name: langsmith-dataset
description: Use this skill for ANY question about creating test or evaluation datasets for agents. Covers generating datasets from exported trace files (final_response, single_step, trajectory, RAG types), uploading to LangSmith, and managing evaluation data.
---

# LangSmith Dataset

Auto-generate evaluation datasets from exported JSONL trace files for testing and validation.

## Setup

### Environment Variables

```bash
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here          # Required
LANGSMITH_WORKSPACE_ID=your-workspace-id              # Optional: for org-scoped keys
```

### Dependencies

```bash
pip install langsmith click rich python-dotenv
```

## Input Format

This script requires traces exported in **JSONL format** (one run per line) from `query_traces.py export`.

### Required Fields

Each line must be a JSON object with these fields:

```json
{"run_id": "...", "trace_id": "...", "name": "...", "run_type": "...", "parent_run_id": "...", "inputs": {...}, "outputs": {...}}
```

| Field | Description |
|-------|-------------|
| `run_id` | Unique identifier for this run |
| `trace_id` | Groups runs into traces (used for hierarchy reconstruction) |
| `name` | Run name (e.g., "model", "classify_email") |
| `run_type` | One of: chain, llm, tool, retriever |
| `parent_run_id` | Parent run ID (null for root) |
| `inputs` | Run inputs (required for dataset generation) |
| `outputs` | Run outputs (required for dataset generation) |

**Important:** You MUST have inputs and outputs to generate datasets correctly.

## Usage

Navigate to `skills/langsmith-dataset/scripts/` to run commands.

### Scripts

**`generate_datasets.py`** - Create evaluation datasets from exported trace files
**`query_datasets.py`** - View and inspect datasets

### Common Flags

All dataset generation commands support:

- `--input <path>` - Input traces: directory of .jsonl files or single .jsonl file (required)
- `--type <type>` - Dataset type: final_response, single_step, trajectory, rag (required)
- `--output <path>` - Output file (.json or .csv) (required)
- `--input-fields` - Comma-separated input keys to extract (e.g., "query,question")
- `--output-fields` - Comma-separated output keys to extract (e.g., "answer,response")
- `--messages-only` - Only extract from messages arrays, skip other fields
- `--upload <name>` - Upload to LangSmith with this dataset name
- `--replace` - Overwrite existing file/dataset (will prompt for confirmation)
- `--yes` - Skip confirmation prompts (use with caution)

**IMPORTANT - Safety Prompts:**
- The script prompts for confirmation before deleting existing datasets with `--replace`
- **ALWAYS respect these prompts** - wait for user input before proceeding
- **NEVER use `--yes` flag unless the user explicitly requests it**
- The `--yes` flag skips all safety prompts and should only be used in automated workflows when explicitly authorized by the user

### Extraction Priority

When extracting inputs/outputs for dataset generation, the script uses this priority:

1. **User-specified fields** (`--input-fields`, `--output-fields`)
2. **Messages array** (LangChain/OpenAI format)
3. **Common fields** (inputs: query, input, question, message, prompt, text; outputs: answer, output, response, result)
4. **Raw dict** (fallback)

### Understanding Trace Hierarchy

Traces have depth levels based on parent-child relationships:

```
Depth 0: Root agent (e.g., "LangGraph")
  ├── Depth 1: Middleware/chains (model, tools, SummarizationMiddleware)
  │     ├── Depth 2: Tool calls (sql_db_query, retriever, etc.)
  │     └── Depth 2: LLM calls (ChatOpenAI, ChatAnthropic)
  └── Depth 3+: Nested subagent calls
```

## Dataset Types

### 1. Final Response

Full conversation with expected output - tests complete agent behavior.

```bash
# Basic usage (raw inputs, extracted output)
generate_datasets.py --input ./traces --type final_response --output /tmp/final_response.json

# Extract specific fields
generate_datasets.py --input ./traces --type final_response \
  --input-fields "email_content" \
  --output-fields "response" \
  --output /tmp/final.json

# Messages only (ignore output dict keys)
generate_datasets.py --input ./traces --type final_response \
  --messages-only \
  --output /tmp/final.json
```

**Structure:**
```json
{
  "trace_id": "...",
  "inputs": {"email_content": "..."},
  "outputs": {"expected_response": "The response text..."}
}
```

With `--input-fields`, inputs become `{"expected_input": "extracted value"}`.

**Important:** Always checks root run first for final response to avoid intermediate tool outputs.

### 2. Single Step

Single node inputs/outputs - tests any specific node's behavior. **Supports multiple occurrences per trace** to capture conversation evolution.

```bash
# Extract all occurrences (default)
generate_datasets.py --input ./traces --type single_step \
  --run-name model \
  --output /tmp/single_step.json

# Sample 2 occurrences per trace
generate_datasets.py --input ./traces --type single_step \
  --run-name model \
  --sample-per-trace 2 \
  --output /tmp/single_step_sampled.json

# Target specific tool
generate_datasets.py --input ./traces --type single_step \
  --run-name classify_email \
  --output /tmp/classify.json
```

**Structure:**
```json
{
  "trace_id": "...",
  "run_id": "...",
  "node_name": "classify_email",
  "occurrence": 1,
  "inputs": {"email_content": "..."},
  "outputs": {"expected_output": {"category": "URGENT", "confidence": 0.95}}
}
```

**Key Features:**
- `node_name` at top level identifies which node was extracted
- `occurrence` field tracks which invocation (1st, 2nd, 3rd, etc.)
- Later occurrences have more conversation history → tests context handling
- `--sample-per-trace` randomly samples N occurrences per trace
- Use `--run-name` to target any node at any depth

**Common targets:**
- `model` (depth 1) - LLM invocations with growing context
- `tools` (depth 1) - Tool execution chain
- Any custom node name

### 3. Trajectory

Tool call sequence - tests execution path with configurable depth.

```bash
# Include all tool calls (all depths)
generate_datasets.py --input ./traces --type trajectory --output /tmp/trajectory_all.json

# Only tool calls up to depth 2
generate_datasets.py --input ./traces --type trajectory \
  --depth 2 \
  --output /tmp/trajectory_depth2.json
```

**Structure:**
```json
{
  "trace_id": "...",
  "inputs": {"query": "What are the top 3 genres?"},
  "outputs": {
    "expected_trajectory": [
      "sql_db_list_tables",
      "sql_db_schema",
      "sql_db_query_checker",
      "sql_db_query"
    ]
  }
}
```

**Depth Control:**
- Omit `--depth` = all levels (includes subagent tool calls)
- `--depth 2` = root + 2 levels (typical for capturing all main tools)
- `--depth 1` = often only middleware/chains, no actual tool calls
- `--depth 0` = root only (no tool calls)

**Note:** Tool calls are typically at depth 2 in LangGraph/DeepAgents architecture.

### 4. RAG

Question/chunks/answer - tests retrieval quality. Only matches runs with `run_type="retriever"`.

```bash
generate_datasets.py --input ./traces --type rag --output /tmp/rag_ds.json
```

**Structure:**
```json
{
  "trace_id": "...",
  "question": "How do I...",
  "retrieved_chunks": "Chunk 1\n\nChunk 2",
  "answer": "The answer is...",
  "cited_chunks": "[\"Chunk 1\", \"Chunk 2\"]"
}
```

Extracts LangChain Documents (`page_content`) if present, otherwise returns raw outputs.

## Output Formats

All dataset types support both JSON and CSV:
```bash
# JSON output (default)
generate_datasets.py --input ./traces --type trajectory --output ds.json

# CSV output (use .csv extension)
generate_datasets.py --input ./traces --type trajectory --output ds.csv
```

## Upload to LangSmith

```bash
# Generate and upload in one command
generate_datasets.py --input ./traces --type trajectory \
  --output /tmp/trajectory_ds.json \
  --upload "Skills: Trajectory"

# Use --replace to overwrite existing dataset
generate_datasets.py --input ./traces --type final_response \
  --output /tmp/final.json \
  --upload "Skills: Final Response" \
  --replace
```

## Query Datasets

```bash
# List all datasets
python query_datasets.py list-datasets

# View dataset examples
python query_datasets.py show "Skills: Trajectory" --limit 5

# View local file
python query_datasets.py view-file /tmp/trajectory_ds.json --limit 3

# Analyze structure
python query_datasets.py structure /tmp/trajectory_ds.json

# Export from LangSmith to local
python query_datasets.py export "Skills: Final Response" /tmp/exported.json --limit 100
```

## Tips for Dataset Generation

1. **Sample for single_step** - Use `--sample-per-trace 2` to capture conversation evolution
2. **Match depth to needs** - `--depth 2` typically captures all main tool calls
3. **Review before upload** - Use `query_datasets.py view-file` to inspect first
4. **Iterative refinement** - Generate small batches (10-20) first, validate, then scale up
5. **Use `--replace` carefully** - Overwrites existing datasets, useful for iteration
6. **Stitch files for large datasets** - `cat ./traces/*.jsonl > all.jsonl`

## Example Workflow

```bash
# 1. Export traces as JSONL with inputs/outputs
query_traces.py export ./traces \
  --project skills \
  --limit 30 \
  --include-io

# 2. Generate all dataset types from exported traces
generate_datasets.py --input ./traces --type final_response \
  --output /tmp/final.json \
  --upload "Skills: Final Response" --replace

generate_datasets.py --input ./traces --type single_step \
  --run-name model \
  --sample-per-trace 2 \
  --output /tmp/model.json \
  --upload "Skills: Single Step (model)" --replace

generate_datasets.py --input ./traces --type trajectory \
  --output /tmp/traj.json \
  --upload "Skills: Trajectory (all depths)" --replace

# 3. Review in LangSmith UI
# Visit https://smith.langchain.com → Datasets

# 4. Query locally if needed
python query_datasets.py show "Skills: Final Response" --limit 3
```

## Troubleshooting

**"No valid traces found":**
- Ensure input path contains `.jsonl` files (not `.json`)
- Check files have required fields (trace_id, inputs, outputs)
- Verify traces were exported with `--include-io`

**Empty final_response outputs:**
- Check that root run has outputs
- Use `--output-fields` to target specific field
- Use `--messages-only` if output is in messages format

**No trajectory examples:**
- Tools might be at different depth - try removing `--depth` or use `--depth 2`
- Verify tool calls exist in traces

**Too many single_step examples:**
- Use `--sample-per-trace 2` to limit examples per trace
- Reduces dataset size while maintaining diversity

**No RAG data:**
- RAG only matches `run_type="retriever"`
- For custom retriever names, use `single_step --run-name <retriever>` instead

**Dataset upload fails:**
- Check dataset doesn't exist or use `--replace`
- Verify LANGSMITH_API_KEY is set
