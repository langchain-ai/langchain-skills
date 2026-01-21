---
name: langsmith-trace
description: Query, analyze, and export traces from LangSmith observability platform. Use this skill for debugging agent behavior, viewing trace hierarchy, exporting runs, and understanding trace structure in LangSmith.
---

# LangSmith Trace

Query, analyze, and export LangSmith traces for debugging and analysis.

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

Navigate to `skills/langsmith-trace/scripts/` to run commands.

### Quick Reference

```bash
# Show recent traces
python query_traces.py recent --limit 10 --project my-project

# Show with metadata (timing, tokens, costs)
python query_traces.py recent --limit 10 --include-metadata

# Filter by time
python query_traces.py recent --last-n-minutes 60
python query_traces.py recent --since 2025-01-20T10:00:00Z

# Get specific trace details
python query_traces.py trace <trace-id> --show-hierarchy

# Export traces to directory (recommended for bulk collection)
python query_traces.py export ./traces --limit 50 --include-metadata
python query_traces.py export /tmp/traces --limit 20  # Use temp files

# Search by name pattern
python query_traces.py search "agent" --project my-project

# Output as JSON
python query_traces.py recent --format json --limit 5
```

## Commands

**`recent`** - List recent traces (`--limit`, `--project`, `--last-n-minutes`, `--include-metadata`, `--format`)

**`trace <id>`** - Get specific trace (`--show-hierarchy`, `--include-metadata`, `--output`)

**`export <dir>`** - Bulk export to directory (`--limit`, `--include-metadata`, `--max-concurrent`)

**`search <pattern>`** - Find runs by name (`--limit`, `--last-n-minutes`)

## Tips

- Use `export` for bulk data, always specify `--project`, use `/tmp` for temp files
- Include `--include-metadata` for performance/cost analysis
- Increase `--max-concurrent 10` for large exports
- Use `--format json` with jq for analysis

## Next Steps

- Use **langsmith-dataset** skill to generate evaluation datasets from traces
- Use **langsmith-evaluator** skill to create evaluators and measure performance
