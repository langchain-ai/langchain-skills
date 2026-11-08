# Harbor skill evaluations

This suite evaluates the skills in this repository with Harbor 0.18.0 and
LangSmith Sandboxes. `profiles.json` defines treatment profiles; each directory
under `tasks/` defines one task. The first task, `chained-eval`, preserves the
exact prompt and synthetic conversations from the November 7, 2026 exploratory
study. It has no preset evaluator or automated score. The report describes what
the agent built and what feedback appeared on fresh conversations, then checks
the resulting evaluator chain and Insights job configuration.
The `thread-llm-judge` task asks for a single thread-level LLM judge. Its seed
and held-out fixtures contain multiple turns per thread, and its report records
the created rule shape and feedback against held-out labels. It is exploratory
and unscored.

The `none`, `full`, and `mcp-only` profiles are the supported comparison. `full`
copies the current `skills/` tree, so a newly added skill participates without
editing the runner. Add a narrower profile by listing skill directory names in
`profiles.json`. Each trial gets a temporary target LangSmith project for task
data and evaluator rules. All Harbor and granular Claude traces go to the one
shared dataset-linked experiment project, distinguished by `eval_task`,
`eval_profile`, `eval_run_id`, and `eval_skill_sha` metadata.

## Runtime setup

Use the Python in the Harbor tool environment. The current integration is
version-bound to Harbor 0.18.0, `harbor-langsmith` 0.2.0, and the vendored
Claude adapter patch in `evals/patch_harbor.py`. It uses
the Claude `langsmith-tracing` plugin from that repo until the plugin is
packaged independently. `check` verifies the installed versions and adapter
markers without contacting LangSmith. The task stages the previously verified
Linux LangSmith CLI binary from the November 7 study; use `--cli-bin` to select
another verified Linux binary.

Credentials stay in environment variables. Supply `LANGSMITH_API_KEY`,
`WORKSPACE_ID`, and `ANTHROPIC_API_KEY` from your local credential store. The
Anthropic key must have access to the LangSmith gateway. Never print, copy, or
commit credential values. In a local shell, after loading your credential store:

```bash
export ANTHROPIC_BASE_URL="https://gateway.smith.langchain.com/anthropic"
export LANGSMITH_LINUX_CLI="/path/to/verified/linux/langsmith"
export HARBOR_PY="$(uv tool dir)/harbor/bin/python"
```

The shared project must be linked to a dataset. Once its name is chosen,
create or validate it in the selected workspace with:

```bash
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
`fixtures.json` for single-run cases, `fixture_type: "synthetic_threads"` for
multi-turn cases with shared `thread_id`, or `fixture_type: "none"` when no
fixtures are needed. Set `verifier_enabled: true` and provide
`tests/test.sh` for a scored task. Set `linux_cli_required: true` only when its
Dockerfile copies the staged `langsmith` binary. Keep hidden truth and held-out
fixtures outside `environment/`.

## Check and run a profile

From this checkout, first resolve each profile without a paid trial:

```bash
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
same environment credentials and keeps all job artifacts under ignored
`evals/jobs/<run-id>/`:

```bash
PLUGIN=/path/to/skills-benchmarks/scaffold/plugins/langsmith-tracing
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

For `chained-eval`, the live report also records three configuration checks in
`validators`: one enabled decision-model evaluator and one enabled LLM judge
with distinct IDs; a run-level judge filter referring to the decision model's
feedback key and a distinct judge feedback key; and a persisted Insights job
whose saved filter selects the judge key with `feedback_score = 1`. The report
keeps only resource IDs, feedback keys, filters, and type evidence. These checks
do not require feedback to arrive, a particular decision-model score, or the
Insights job to finish. A failed check is a regression to inspect; it does not
prevent the report from being saved. A local `langsmith` CLI must be on `PATH`
for the Insights queries.

For `thread-llm-judge`, use the same `check`, `prepare`, `run`, `replay`, and
`report` commands with `--task thread-llm-judge`. The `full` and `mcp-only`
profiles compare skill guidance with docs MCP alone. The live report records
rule type, thread grouping, variable mapping, feedback keys, and held-out
`expected_resolved` labels. Review the agent trajectory and reasoning alongside
the scores; four cases are descriptive evidence, not a pass rate.

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
that the chained-eval report captured configuration evidence, then verifies
the live project's ID, name, workspace, and run description before deleting
it. It preserves the shared trace project, dataset, baseline projects from the
prior study, and local artifacts.
Workspace-wide annotation queues and Insights configurations are outside this
automatic cleanup boundary; inspect and remove those by their exact IDs if an
agent created them. Do not run cleanup merely because a trial failed: its
target project and local JSONL may be needed for diagnosis.

## Scheduled GitHub Action

`.github/workflows/skills-evals.yml` runs the three profiles sequentially at
9:00 AM Sunday in `America/New_York`. GitHub evaluates schedules from the
repository's default branch, so merge the workflow there to activate the
schedule. `workflow_dispatch` also permits a manual run. The action checks out
the current `skill-restructure` branch for the skills and the default branch
for the harness and task definitions. Changes to a skill on `skill-restructure`
or a task on the default branch appear in the next run without editing the
workflow. The workflow currently selects `chained-eval`; `thread-llm-judge`
is available through the harness commands above and is not scheduled.

Configure these GitHub Actions secrets in the `langchain-ai/langchain-skills`
repository: `LANGSMITH_API_KEY` for the LangChain Inc workspace,
`LANGSMITH_WORKSPACE_ID`, and `LANGSMITH_GATEWAY_API_KEY`. Configure the
repository variable `PUBLIC_SKILL_EVALS_PROJECT_ID` with the UUID of the
long-lived, dataset-linked `public-skill-evals` project. No local credential
path is needed by the hosted runner. The workflow pins Harbor, the tracing
plugin revision, the Linux LangSmith CLI checksum, and its GitHub Actions.

The Action uploads only `skill-eval-summary.json`, containing aggregate cost,
latency, tool count, feedback count, trace nesting, validator outcomes, and run
IDs. Workflow logs, artifacts, task prompts, synthetic fixtures, and this
repository are public; do not put confidential content in task definitions.
Raw Claude transcripts, Harbor trajectories, and complete reports stay on the
ephemeral runner while it runs and are **not** uploaded as Actions artifacts.
The shared LangSmith project retains granular traces with
`eval_task`, `eval_profile`, `eval_run_id`, and `eval_skill_sha` metadata for
private inspection. A run's temporary task project is deleted after its live
report is saved. On an earlier failure, the project is left for diagnosis;
the summary records its run and target project IDs when available. The hosted
runner's manifest is ephemeral, so inspect and remove that exact project in
LangSmith after diagnosing a cloud failure. For durable access to raw cloud
transcripts and trajectories, configure a private artifact store; GitHub Pages
does not provide that storage boundary for this public repo.
