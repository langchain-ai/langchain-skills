# Harbor

## Contents

- [Task layout](#task-layout)
- [Audit package completeness before running](#audit-package-completeness-before-running)
- [Run contract](#run-contract)

Use the project's pinned or supported Harbor version. Otherwise, use the
installed supported version and record it. Upgrade only with user approval and
a stated compatibility reason. Use that CLI's help as the command contract.
Use Docker locally unless the Task requires another supported Environment.

## Task layout

Create this package before any Harbor trial:

```text
evals/<suite>/tasks/<task-id>/
├── Task.md                 # required by eval-engineering; hidden from agent
├── task.toml               # required by Harbor
├── instruction.md          # required by Harbor; exact agent input
├── environment/            # required by Harbor
│   ├── Dockerfile          # use this or docker-compose.yaml
│   ├── docker-compose.yaml # optional; primary service must be main
│   └── <agent-visible seed files>
├── tests/
│   ├── test.sh             # required Harbor Verifier entry point
│   ├── test_*.py           # optional Verifier helpers
│   └── fixtures/           # optional hidden Verifier data
└── solution/
    └── solve.sh            # optional reference path
```

The files have these contracts:

- `Task.md` is the human-reviewed control-plane spec. Keep the exact request,
  initial state, hidden truth, complete scoring rules, fairness analysis, and
  open decisions here. Never mount or copy it into the agent image or workspace.
- `task.toml` follows the installed project-supported Harbor schema. Record the
  agent and Verifier timeouts, Environment resources and services, network
  policy, and runtime variable names needed by this Task. Never store secret
  values in it.
- `instruction.md` contains the exact approved agent input. State the goal,
  agent-visible context, required output or effect, paths, and real limits. Do
  not mention hidden tests, scoring, expected answers, or the solution.
- `environment/` contains one usable Environment definition: a `Dockerfile`, or
  a `docker-compose.yaml` whose primary service is `main`. Include only the
  dependencies and seed state visible to the agent. Never copy `Task.md`,
  `tests/`, `solution/`, hidden truth, judge rules, or credentials into it.
- `tests/test.sh` always exists. Harbor uploads `tests/` only after agent work
  ends and runs this file as the Verifier entry point. It may call optional
  helper tests and hidden fixtures. It must read independent evidence and write
  a valid reward to `/logs/verifier/reward.txt` or
  `/logs/verifier/reward.json` on every completed Verifier path. It must not
  exit before writing the reward, turn an infrastructure failure into a zero,
  or expose hidden truth or secrets in output.
- `solution/solve.sh` is optional. When present, it performs the real reference
  work against the same Environment and proves the intended result is
  reachable. It does not write a hard-coded answer only to satisfy the Verifier.

Use optional Verifier helpers, fixtures, or a solution only when the Task needs
them. Do not create empty placeholder files or directories.

A Harness adapter can bind approved dependencies and translate I/O. It must not
decide the answer or fabricate actions.

Keep generated jobs outside task source, for example under `evals/jobs/`. Keep
them until the user accepts, revises, or drops the eval. Before retaining
private transcripts, define who can read them, what must be redacted, how long
to keep them, and how to delete them. Keep only the evidence needed to audit
the Task.

## Audit package completeness before running

Use `harbor --help` and subcommand help to confirm current flags. Resolve the
configuration without a scored run when the installed version supports it.
Do not start any Harbor trial, including an Oracle or model trial, until this
audit passes for the exact Task package:

1. Confirm `task.toml`, `instruction.md`, `tests/test.sh`, and a usable
   Environment definition all exist at the paths Harbor will load. Confirm
   `Task.md` exists beside them for human review.
2. Parse `task.toml` with the supported Harbor version. Confirm exact Task
   selection, Harness or adapter, model, resources, network policy, runtime
   variable names, trial count, concurrency, timeouts, judge, and output paths.
3. Build and start the Environment through Harbor. Confirm mounts, the `main`
   service when Compose is used, readiness, agent-visible seed state, allowed
   operations, cleanup, and trial isolation.
4. Inspect the built agent image and workspace. Confirm they do not contain
   `Task.md`, `tests/`, `solution/`, hidden evidence, expected answers, judge
   rules, or secret material.
5. Confirm Harbor can upload and execute `tests/test.sh` with the required file
   permissions and working paths. Exercise each Verifier dependency.
6. Run known-good, alternative-valid, wrong, shortcut, collateral-change, and
   missing-or-corrupt-evidence cases through the real Verifier command. Confirm
   each completed path produces a parseable reward and criterion evidence.
7. Run `solution/solve.sh` through Harbor when it exists, then run the Verifier.
   Confirm the reference result is reachable and receives the intended reward.
8. Fix every missing file, invalid path, parse error, build error, startup
   error, missing dependency, permission error, missing reward, or leaked file
   before starting a trial.

Docker is the default boundary, not proof that isolation works. Test allowed
and denied access when network policy matters. Report a limit if the backend
cannot enforce or expose it. Never put secret values in source, images, prompts,
fixtures, or logs.

## Run contract

Before model trials, run Environment checks, the reference path, and focused
Verifier fixtures through the same images and commands Harbor will use. Increase
timeouts only when evidence shows valid work exceeds the current limit. Keep a
finite bound and record the reason.

For each trial, retain:

- resolved configuration;
- Harness messages, calls, results, retries, and errors;
- Environment startup, requests, state, reset, and cleanup evidence;
- Verifier criteria, evidence, verdict, reason, reward, and errors; and
- phase timing and termination reason.

Wrong agent work receives zero. Build, adapter, credential, reset, timeout,
judge, Verifier, or cleanup failure receives no agent score. Every attempted
trial must end as completed, cancelled, or infrastructure error. Do not use a
pending trial as evidence.

For multi-turn runs, also prove that the first Harness input equals
`instruction.md`, later turns came from the declared user policy, one approved
session was reused, future messages were not preloaded, and no model call
occurred after termination. See the multi-turn reference for implementation
details.
