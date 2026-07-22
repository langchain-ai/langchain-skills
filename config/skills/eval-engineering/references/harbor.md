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
├── harbor_agents/              # only when an adapter is required
├── configs/                    # only when non-default config is required
└── jobs/                       # generated; do not commit
```

Each directory with `task.toml` is a task. Keep only instructions, runtime assets, verifier code, and hidden judge evidence in it. Do not add plans, trace exports, audit files, credentials, or copied run output.

An adapter may translate I/O and bind approved dependencies. It must not decide the task, contain answers, or fabricate actions. It and the verifier must retain the target response/action record, verifier evidence, verdict/reason, reward, and errors in Harbor artifacts or verifier logs.

## Lifecycle

```bash
mkdir -p evals
harbor task init "<task-id>" --tasks-dir evals --no-solution

harbor run \
  --path evals \
  --include-task-name <task-id> \
  --agent <target-or-adapter> \
  --env docker \
  --jobs-dir evals/jobs \
  --print-config

harbor run \
  --path evals \
  --include-task-name <task-id> \
  --agent <target-or-adapter> \
  --env docker \
  --jobs-dir evals/jobs \
  --job-name <job-name>
```

`--print-config` resolves configuration without executing. Remove scaffold-only files such as the generated task README. Harbor scaffolds `network_mode = "public"`; replace it with the approved network policy before any credentialed or target run.

Before the target run, execute the verifier's focused fixture test: one valid result passes and one realistic incorrect result fails.

## Environment and evidence

Docker is the default. Start the smallest image, services, mounts, and network configuration required by the task before completing the scenario. Pass approved credentials at runtime by environment-variable reference only.

Default to no network. Allow only hosts needed by approved live dependencies. Keep verifier credentials and hidden evidence unavailable to the target. If Docker cannot provide a required capability, explain it and agree on a supported Harbor environment; do not weaken isolation silently.

The job directory is the run record. Read the actual trial files and correlate:

- target response and actions from ATIF or an equivalent target artifact;
- harness-observed calls and state;
- verifier evidence, verdict, reason, and logs;
- reward, resolved configuration, timing, and phase errors.

Trust actions and state only when the harness or dependency observed them. Wrong target work receives reward 0; build, adapter, credential, reset, timeout, judge, or verifier failures are infrastructure errors. Keep `evals/jobs/` until the user accepts, revises, or drops the eval.
