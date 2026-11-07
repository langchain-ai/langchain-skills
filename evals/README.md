# Harbor skill evaluations

This suite evaluates the skills in this repository with Harbor 0.18.0 and
LangSmith Sandboxes. `profiles.json` defines treatment profiles; each directory
under `tasks/` defines one task. The first task, `chained-eval`, preserves the
exact prompt and synthetic conversations from the November 7, 2026 exploratory
study. It has no preset evaluator or automated score. The report describes what
the agent built and what feedback appeared on fresh conversations.

The `none`, `full`, and `mcp-only` profiles are the supported comparison. `full`
copies the current `skills/` tree, so a newly added skill participates without
editing the runner. Add a narrower profile by listing skill directory names in
`profiles.json`. Each trial gets a temporary target LangSmith project for task
data and evaluator rules. All Harbor and granular Claude traces go to the one
shared dataset-linked experiment project, distinguished by `eval_task`,
`eval_profile`, `eval_run_id`, and `eval_skill_sha` metadata.

## Runtime setup

Use the Python in the Harbor tool environment. The current integration is
version-bound to Harbor 0.18.0, `harbor-langsmith` 0.2.0, and the maintained
Claude adapter patch from `skills-benchmarks/scripts/patch_harbor.py`. It uses
the Claude `langsmith-tracing` plugin from that repo until the plugin is
packaged independently. `check` verifies the installed versions and adapter
markers without contacting LangSmith. The task stages the previously verified
Linux LangSmith CLI binary from the November 7 study; use `--cli-bin` to select
another verified Linux binary.

Credentials stay in environment variables. The LangChain Inc workspace
configuration is `/Users/jacobkleiman/Documents/skills/.env` and supplies
`LANGSMITH_API_KEY` and `WORKSPACE_ID`. The gateway credential is referenced from
`/Users/jacobkleiman/Documents/projects/juji/api/.env` as in the prior tracing
guide. Never print, copy, or commit either file's values. In a local shell:

```bash
source ~/.zshrc
set -a
source /Users/jacobkleiman/Documents/projects/juji/api/.env
source /Users/jacobkleiman/Documents/skills/.env
set +a
export ANTHROPIC_API_KEY="$GATEWAY_API_KEY"
export ANTHROPIC_BASE_URL="https://gateway.smith.langchain.com/anthropic"
```

The shared project must be linked to a dataset. Once its name is chosen,
create or validate it in the selected workspace with:

```bash
HARBOR_PY=/Users/jacobkleiman/.local/share/uv/tools/harbor/bin/python
$HARBOR_PY evals/harness.py bootstrap \
  --project-name <shared-project-name> \
  --dataset-name <shared-dataset-name>
```

`bootstrap` returns the project ID. An existing project works only if it is
already linked to that dataset. The shared project and dataset are long-lived;
the cleanup command does not delete them.

## Add a task

Create `evals/tasks/<task-name>/` with `Task.md`, the exact agent
`instruction.md`, `task.toml`, `environment/Dockerfile` (or Compose), and
`harness.json`. Use `fixture_type: "synthetic_conversations"` plus
`fixtures.json` when the task needs seed and held-out conversations, or
`fixture_type: "none"` otherwise. Set `verifier_enabled: true` and provide
`tests/test.sh` for a scored task. Set `linux_cli_required: true` only when its
Dockerfile copies the staged `langsmith` binary. Keep hidden truth and held-out
fixtures outside `environment/`.

## Check and run a profile

From this checkout, first resolve each profile without a paid trial:

```bash
HARBOR_PY=/Users/jacobkleiman/.local/share/uv/tools/harbor/bin/python
$HARBOR_PY evals/harness.py check --task chained-eval --profile full
```

Then prepare a run, using the shared project ID returned by `bootstrap` or
provided by the workspace owner:

```bash
$HARBOR_PY evals/harness.py prepare --task chained-eval --profile full \
  --trace-project-id <shared-project-uuid>
```

`prepare` prints the run ID, creates one target project, and emits only the seed
conversations. It never creates an evaluator or judge. Before running, verify
that the Claude tracing plugin directory exists. The `run` command uses the
same credential file by path and keeps all job artifacts under ignored
`evals/jobs/<run-id>/`:

```bash
PLUGIN=/Users/jacobkleiman/Documents/skills/skills-benchmarks/scaffold/plugins/langsmith-tracing
$HARBOR_PY evals/harness.py run <run-id> \
  --tracing-plugin-dir "$PLUGIN" --print-config
$HARBOR_PY evals/harness.py run <run-id> \
  --tracing-plugin-dir "$PLUGIN"
```

After Harbor completes, emit the fresh cases and inspect feedback and trace
parentage. Online evaluators ingest asynchronously; use a bounded wait if the
first snapshot is incomplete:

```bash
$HARBOR_PY evals/harness.py replay <run-id>
$HARBOR_PY evals/harness.py report <run-id> --live --wait-seconds 900
```

`report.json` includes local duration, agent cost, tool and skill counts,
held-out feedback, and whether `Claude Code Turn` spans are descendants of
`agent-start` in the shared project. Keep the local Claude JSONL and Harbor
trajectory for deeper review. Successful tracing requires Node in the task
image, the patched adapter, the tracing plugin, and a completed Stop-hook flush.

## Cleanup and retention

The manifest records exact project and run IDs. After saving a live report for
each run that emitted fresh cases, preview cleanup, then explicitly execute it:

```bash
$HARBOR_PY evals/cleanup.py --run-id <run-id>
$HARBOR_PY evals/cleanup.py --run-id <run-id> --execute
# Select multiple runs with repeated --run-id, or preview all recorded runs:
$HARBOR_PY evals/cleanup.py --all
```

`--all --execute` deletes every eligible target project recorded in this
checkout, so inspect its dry-run list first. The legacy
`harness.py cleanup <run-id>` command follows the same checks. Cleanup verifies
the live project's ID, name, workspace, and run description before deleting
it. It preserves the shared trace project, dataset, baseline projects from the
prior study, and local artifacts.
Workspace-wide annotation queues and Insights configurations are outside this
automatic cleanup boundary; inspect and remove those by their exact IDs if an
agent created them. Do not run cleanup merely because a trial failed: its
target project and local JSONL may be needed for diagnosis.
