# Harbor Task and Run Contract

Use the latest version of Harbor. Install and run it locally with Docker or use a supported cloud environment; see the [Harbor documentation](https://www.harborframework.com/docs). Use installed CLI help as the command contract.

## Source and run output

Keep task source under `evals/` and generated run evidence under `evals/jobs/`:

```text
evals/
├── <task-id>/
│   ├── task.toml
│   ├── instruction.md
│   ├── environment/
│   └── tests/
├── harbor_agents/              # Harness adapter, only when required
├── configs/                    # only when non-default config is required
└── jobs/                       # generated run evidence
```

Each directory with `task.toml` is a task. Keep only instructions, Environment assets, Verifier code, and hidden judge evidence in it. Do not add plans, trace exports, audit files, credentials, or copied run output.

A Harness adapter may translate I/O and bind approved dependencies. It must not decide the task, contain answers, or fabricate actions. It and the Verifier must retain the Harness response/action record, Verifier evidence, verdict/reason, reward, and errors in Harbor artifacts or logs.

Record a digest for Harness source outside the task directory because Harbor's task checksum may not cover it. A source change invalidates prior run evidence.

## Lifecycle

```bash
mkdir -p evals
harbor tasks init "<task-id>" --tasks-dir evals --no-solution

harbor run \
  --path evals \
  --include-task-name <task-id> \
  --agent <harness-or-adapter> \
  --env docker \
  --jobs-dir evals/jobs \
  --print-config

harbor run \
  --path evals \
  --include-task-name <task-id> \
  --agent <harness-or-adapter> \
  --env docker \
  --jobs-dir evals/jobs \
  --job-name <job-name>
```

`--print-config` resolves configuration without executing. Remove scaffold-only files such as the generated task README. Harbor scaffolds `network_mode = "public"`; replace it with the approved network policy before any credentialed run.

Before the Harness run, execute the Verifier's focused fixtures through the same image and command Harbor will use. Retain the calibration result in its logs or artifacts.

## Environment and evidence

Docker is the default. Start the smallest image, services, mounts, and network configuration required by the task before completing the scenario. Pass approved credentials at runtime by environment-variable reference only.

Default to no network. Allow only hosts needed by approved live dependencies. Keep Verifier credentials and hidden evidence unavailable to the Harness. If Docker cannot provide a required capability, explain it and agree on a supported Harbor Environment; do not weaken isolation silently.

Verify the effective network boundary from resolved backend state or controlled allowed-host and denied-host probes. A declaration in `task.toml` alone does not prove enforcement. If the backend cannot expose or test the policy, report that limitation instead of claiming the allowlist was verified.

The job directory is the run record. Read the actual trial files and correlate:

- Harness response and actions from ATIF or an equivalent artifact;
- Harness-recorded calls and Environment-observed results/state;
- Verifier evidence, verdict, reason, and logs;
- reward, resolved configuration, timing, and phase errors.

Trust actions and state only when the Harness or Environment observed them. Wrong agent work receives reward 0; build, adapter, credential, reset, timeout, judge, or Verifier failures are infrastructure errors. Keep `evals/jobs/` until the user accepts, revises, or drops the eval.

Record messages, calls, observations, and responses when each event occurs so ATIF timestamps remain chronological. Before review, ensure every attempted trial is completed or explicitly classified as cancelled or an infrastructure error; do not treat an indefinitely pending trial as evidence.

For multi-turn runs, also verify from ATIF and adapter evidence that:

- the first Harness input exactly equals `instruction.md`;
- every later user message is recorded as scripted or linked to an LLM-user decision;
- every Harness call uses the same approved session or thread;
- no future user message was preloaded into Harness context;
- termination has an adapter-recorded reason and no Harness call occurs afterward.
