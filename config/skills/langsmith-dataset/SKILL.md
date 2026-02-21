---
name: LangSmith Datasets
description: "INVOKE THIS SKILL when creating evaluation datasets from traces OR uploading datasets to LangSmith. Covers dataset types (final_response, single_step, trajectory, RAG) and LangSmith upload. Contains helper scripts to use or refer to."
---

<oneliner>
Auto-generate evaluation datasets from exported JSONL trace files for testing and validation.
</oneliner>

<setup>
Environment Variables

```bash
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here          # Required
LANGSMITH_WORKSPACE_ID=your-workspace-id              # Optional: for org-scoped keys
```

Dependencies (Python)

```bash
pip install langsmith click rich python-dotenv
```

Dependencies (TypeScript/JavaScript)

```bash
npm install langsmith commander chalk cli-table3 dotenv
```
</setup>

<input_format>
This script requires traces exported in **JSONL format** (one run per line).

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

**Before generating datasets, verify your traces exist:**
- Check that JSONL files exist in the output directory
- Confirm traces have both `inputs` and `outputs` populated
- Inspect the trace hierarchy to understand the structure
</input_format>

<usage>
Use the included scripts to generate datasets.

### Scripts

**Python:**
- `generate_datasets.py` - Create evaluation datasets from exported trace files
- `query_datasets.py` - View and inspect datasets

**TypeScript/JavaScript:**
- `generate_datasets.ts` - Create evaluation datasets from exported trace files
- `query_datasets.ts` - View and inspect datasets

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
- **If you are running with user input:** ALWAYS wait for user input; NEVER use `--yes` unless the user explicitly requests it
- **If you are running non-interactively:** Use `--replace --yes` together to ensure proper replacement
</usage>

<dataset_types_overview>
Use `--type <type>` flag with the generate_datasets script:

- **final_response** - Full conversation with expected output. Tests complete agent behavior.
- **single_step** - Single node inputs/outputs. Tests specific node behavior. Use `--run-name` to target a node.
- **trajectory** - Tool call sequence. Tests execution path. Use `--depth` to control depth.
- **rag** - Question/chunks/answer/citations. Tests retrieval quality. Only matches `run_type="retriever"`.
</dataset_types_overview>

<script_usage>
## Script Usage

<python>
Generate and query datasets using the Python CLI scripts.
```bash
# Basic usage (raw inputs, extracted output)
python generate_datasets.py --input ./traces --type final_response --output /tmp/final_response.json

# Extract specific fields
python generate_datasets.py --input ./traces --type final_response \
  --input-fields "email_content" \
  --output-fields "response" \
  --output /tmp/final.json

# Generate trajectory dataset
python generate_datasets.py --input ./traces --type trajectory --output /tmp/trajectory.json

# Generate and upload
python generate_datasets.py --input ./traces --type trajectory \
  --output /tmp/trajectory.json \
  --upload "Skills: Trajectory"

# Query datasets
python query_datasets.py list-datasets
python query_datasets.py show "Skills: Trajectory" --limit 5
python query_datasets.py view-file /tmp/trajectory_ds.json --limit 3
```
</python>

<typescript>
Generate and query datasets using the TypeScript CLI scripts.
```bash
# Basic usage (raw inputs, extracted output)
npx tsx generate_datasets.ts --input ./traces --type final_response --output /tmp/final_response.json

# Extract specific fields
npx tsx generate_datasets.ts --input ./traces --type final_response \
  --input-fields "email_content" \
  --output-fields "response" \
  --output /tmp/final.json

# Generate trajectory dataset
npx tsx generate_datasets.ts --input ./traces --type trajectory --output /tmp/trajectory.json

# Generate and upload
npx tsx generate_datasets.ts --input ./traces --type trajectory \
  --output /tmp/trajectory.json \
  --upload "Skills: Trajectory"

# Query datasets
npx tsx query_datasets.ts list-datasets
npx tsx query_datasets.ts show "Skills: Trajectory" --limit 5
npx tsx query_datasets.ts view-file /tmp/trajectory_ds.json --limit 3
```
</typescript>
</script_usage>

<example_workflow>
Complete workflow from exported traces to LangSmith datasets:

<python>
Generate all dataset types from exported traces and upload to LangSmith.
```bash
# Generate all dataset types from exported traces
python generate_datasets.py --input ./traces --type final_response \
  --output /tmp/final.json \
  --upload "Skills: Final Response" --replace

python generate_datasets.py --input ./traces --type single_step \
  --run-name model \
  --sample-per-trace 2 \
  --output /tmp/model.json \
  --upload "Skills: Single Step (model)" --replace

python generate_datasets.py --input ./traces --type trajectory \
  --output /tmp/traj.json \
  --upload "Skills: Trajectory (all depths)" --replace

# Query locally if needed
python query_datasets.py show "Skills: Final Response" --limit 3
```
</python>

<typescript>
Generate all dataset types from exported traces and upload to LangSmith.
```bash
# Generate all dataset types from exported traces
npx tsx generate_datasets.ts --input ./traces --type final_response \
  --output /tmp/final.json \
  --upload "Skills: Final Response" --replace

npx tsx generate_datasets.ts --input ./traces --type single_step \
  --run-name model \
  --sample-per-trace 2 \
  --output /tmp/model.json \
  --upload "Skills: Single Step (model)" --replace

npx tsx generate_datasets.ts --input ./traces --type trajectory \
  --output /tmp/traj.json \
  --upload "Skills: Trajectory (all depths)" --replace

# Query locally if needed
npx tsx query_datasets.ts show "Skills: Final Response" --limit 3
```
</typescript>
</example_workflow>

<troubleshooting>
**"No valid traces found":**
- Ensure input path contains `.jsonl` files (not `.json`)
- Check files have required fields (trace_id, inputs, outputs)
- Verify traces have inputs and outputs populated

**Empty final_response outputs:**
- Check that root run has outputs
- Use `--output-fields` to target specific field
- Use `--messages-only` if output is in messages format

**No trajectory examples:**
- Tools might be at different depth - try removing `--depth` or use `--depth 2`
- Verify tool calls exist in your exported JSONL files

**Too many single_step examples:**
- Use `--sample-per-trace 2` to limit examples per trace
- Reduces dataset size while maintaining diversity

**No RAG data:**
- RAG only matches `run_type="retriever"`
- For custom retriever names, use `single_step --run-name <retriever>` instead

**Dataset upload fails:**
- Check dataset doesn't exist or use `--replace`
- Verify LANGSMITH_API_KEY is set
</troubleshooting>
