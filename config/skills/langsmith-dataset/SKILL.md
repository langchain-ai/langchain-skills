---
name: langsmith-dataset
description: Use this skill for ANY question about creating test or evaluation datasets for LangChain agents. Covers generating datasets from traces (final_response, single_step, trajectory, RAG types), uploading to LangSmith, and managing evaluation data.
---

# LangSmith Dataset

Auto-generate evaluation datasets from LangSmith traces for testing and validation.

## Setup

### Environment Variables

```bash
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here          # Required
LANGSMITH_PROJECT=your-project-name                   # Optional: default project
LANGSMITH_WORKSPACE_ID=your-workspace-id              # Optional: for org-scoped keys
```

### Dependencies

```bash
pip install langsmith click rich python-dotenv
```

## Usage

Navigate to `skills/langsmith-dataset/scripts/` to run commands.

### Scripts

**`generate_datasets.py`** - Create evaluation datasets from traces
**`query_datasets.py`** - View and inspect datasets

### Common Flags

All dataset generation commands support:

- `--root-run-name <name>` - Filter traces by root run name (e.g., "LangGraph" for DeepAgents)
- `--limit <n>` - Number of traces to process (default: 30)
- `--last-n-minutes <n>` - Only recent traces
- `--output <path>` - Output file (.json or .csv)
- `--upload <name>` - Upload to LangSmith with this dataset name
- `--replace` - Overwrite existing file/dataset (will prompt for confirmation)
- `--yes` - Skip confirmation prompts (use with caution)

**IMPORTANT - Safety Prompts:**
- The script prompts for confirmation before deleting existing datasets with `--replace`
- **ALWAYS respect these prompts** - wait for user input before proceeding
- **NEVER use `--yes` flag unless the user explicitly requests it**
- The `--yes` flag skips all safety prompts and should only be used in automated workflows when explicitly authorized by the user

### Understanding Trace Hierarchy

Traces have depth levels based on parent-child relationships:

```
Depth 0: Root agent (e.g., "LangGraph")
  ├── Depth 1: Middleware/chains (model, tools, SummarizationMiddleware)
  │     ├── Depth 2: Tool calls (sql_db_query, retriever, etc.)
  │     └── Depth 2: LLM calls (ChatOpenAI, ChatAnthropic)
  └── Depth 3+: Nested subagent calls
```

**Use `--root-run-name` to target specific agent frameworks:**
- DeepAgents: `--root-run-name LangGraph`
- Custom agents: Use your root node name

## Dataset Types

### 1. Final Response

Full conversation with expected output - tests complete agent behavior.

```bash
# Basic usage
python generate_datasets.py --type final_response \
  --project my-project \
  --root-run-name LangGraph \
  --limit 30 \
  --output /tmp/final_response.json

# With custom output fields
python generate_datasets.py --type final_response \
  --project my-project \
  --output-fields "answer,result" \
  --output /tmp/final.json

# Messages only (ignore output dict keys)
python generate_datasets.py --type final_response \
  --project my-project \
  --messages-only \
  --output /tmp/final.json
```

**Structure:**
```json
{
  "trace_id": "...",
  "inputs": {"query": "What are the top 3 genres?"},
  "outputs": {
    "expected_response": "The top 3 genres based on the number of tracks are:\n\n1. Rock with 1,297 tracks\n2. Latin with 579 tracks\n3. Metal with 374 tracks"
  }
}
```

**Extraction Priority:**
1. Messages from root run (AI responses with content)
2. User-specified output fields (`--output-fields`)
3. Common keys (answer, output)
4. Full output dict

**Important:** Always checks root run first for final response to avoid intermediate tool outputs.

### 2. Single Step

Single node inputs/outputs - tests any specific node's behavior. **Supports multiple occurrences per trace** to capture conversation evolution.

```bash
# Extract all occurrences (default)
python generate_datasets.py --type single_step \
  --project my-project \
  --root-run-name LangGraph \
  --run-name model \
  --output /tmp/single_step.json

# Sample 2 occurrences per trace
python generate_datasets.py --type single_step \
  --project my-project \
  --root-run-name LangGraph \
  --run-name model \
  --sample-per-trace 2 \
  --output /tmp/single_step_sampled.json

# Target specific tool at depth 2
python generate_datasets.py --type single_step \
  --project my-project \
  --root-run-name LangGraph \
  --run-name sql_db_query \
  --output /tmp/sql_query.json
```

**Structure:**
```json
{
  "trace_id": "...",
  "run_id": "...",
  "occurrence": 2,
  "inputs": {
    "messages": [
      {"type": "human", "content": "What are the top 3 genres?"},
      {"type": "ai", "content": "", "tool_calls": [...]},
      {"type": "tool", "content": "...results..."},
      ...
    ]
  },
  "outputs": {
    "expected_output": {
      "messages": [
        {"type": "ai", "content": "", "tool_calls": [...]}
      ]
    },
    "node_name": "model"
  }
}
```

**Key Features:**
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
python generate_datasets.py --type trajectory \
  --project my-project \
  --root-run-name LangGraph \
  --limit 30 \
  --output /tmp/trajectory_all.json

# Only tool calls up to depth 2
python generate_datasets.py --type trajectory \
  --project my-project \
  --root-run-name LangGraph \
  --depth 2 \
  --output /tmp/trajectory_depth2.json

# Only root-level tool calls (depth 0) - usually empty if tools are at depth 2+
python generate_datasets.py --type trajectory \
  --project my-project \
  --depth 0 \
  --output /tmp/trajectory_root.json
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

Question/chunks/answer/citations - tests retrieval quality.

```bash
python generate_datasets.py --type rag \
  --project my-project \
  --limit 30 \
  --output /tmp/rag_ds.csv  # Supports .json or .csv
```

**Structure (CSV format):**
```csv
question,retrieved_chunks,answer,cited_chunks
"How do I...","Chunk 1\n\nChunk 2","The answer is...","[\"Chunk 1\"]"
```

## Output Formats

All dataset types support both JSON and CSV:
```bash
# JSON output (default)
python generate_datasets.py --type trajectory --project my-project --output ds.json

# CSV output (use .csv extension)
python generate_datasets.py --type trajectory --project my-project --output ds.csv
```

## Upload to LangSmith

```bash
# Generate and upload in one command
python generate_datasets.py --type trajectory \
  --project my-project \
  --root-run-name LangGraph \
  --limit 50 \
  --output /tmp/trajectory_ds.json \
  --upload "Skills: Trajectory"

# Use --replace to overwrite existing dataset
python generate_datasets.py --type final_response \
  --project my-project \
  --output /tmp/final.json \
  --upload "Skills: Final Response" \
  --replace
```

**Naming Convention:** Use "Skills: <Type>" format for consistency:
- "Skills: Final Response"
- "Skills: Single Step (model)"
- "Skills: Single Step (sql_db_query)"
- "Skills: Trajectory (all depths)"
- "Skills: Trajectory (depth=2)"

## Query Datasets

```bash
# List all datasets
python query_datasets.py list-datasets

# Filter by name pattern
python query_datasets.py list-datasets | grep "Skills:"

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

1. **Always use `--root-run-name`** - Filter for specific agent framework (e.g., "LangGraph")
2. **Start with successful traces** - Use recent successful runs for baseline datasets
3. **Use time windows** - `--last-n-minutes 1440` for last 24 hours of data
4. **Sample for single_step** - Use `--sample-per-trace 2` to capture conversation evolution
5. **Match depth to needs** - `--depth 2` typically captures all main tool calls
6. **Review before upload** - Use `query_datasets.py view-file` to inspect first
7. **Iterative refinement** - Generate small batches (10-20) first, validate, then scale up
8. **Use `--replace` carefully** - Overwrites existing datasets, useful for iteration

## Example Workflow

```bash
# 1. Generate fresh traces (if needed)
python tests/test_agent.py --batch  # Your test agent

# 2. Generate all dataset types from LangGraph traces
python generate_datasets.py --type final_response \
  --project skills --root-run-name LangGraph --limit 10 \
  --output /tmp/final.json --upload "Skills: Final Response" --replace

python generate_datasets.py --type single_step \
  --project skills --root-run-name LangGraph --run-name model \
  --sample-per-trace 2 --limit 10 \
  --output /tmp/model.json --upload "Skills: Single Step (model)" --replace

python generate_datasets.py --type trajectory \
  --project skills --root-run-name LangGraph --limit 10 \
  --output /tmp/traj.json --upload "Skills: Trajectory (all depths)" --replace

python generate_datasets.py --type trajectory \
  --project skills --root-run-name LangGraph --depth 2 --limit 10 \
  --output /tmp/traj_d2.json --upload "Skills: Trajectory (depth=2)" --replace

# 3. Review in LangSmith UI
# Visit https://smith.langchain.com → Datasets → Filter for "Skills:"

# 4. Query locally if needed
python query_datasets.py show "Skills: Final Response" --limit 3
```

## Troubleshooting

**Empty final_response outputs:**
- Ensure `--root-run-name` matches your agent's root node
- Check that root run has messages with AI responses
- Use `--messages-only` if output dict is empty

**No trajectory examples:**
- Tools might be at different depth - try removing `--depth` or use `--depth 2`
- Verify tool calls exist: `python query_traces.py trace <id> --show-hierarchy`

**Too many single_step examples:**
- Use `--sample-per-trace 2` to limit examples per trace
- Reduces dataset size while maintaining diversity

**Dataset upload fails:**
- Check dataset doesn't exist or use `--replace`
- Verify LANGSMITH_API_KEY is set

## Related Skills

- Use **langsmith-trace** skill to query and export traces
- Use **langsmith-evaluator** skill to create evaluators and measure performance
