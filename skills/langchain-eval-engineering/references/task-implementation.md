# Implement and Audit a Task

This is the concrete implementation guide for Spec2Task. Use it after the user
selects a Task and reviews its collocated `Task.md`. The result is a runnable
Harbor Task whose Environment, Verifier, and real-run evidence match that Task
Spec.

## Contents

- [Read references at each decision](#read-references-at-each-decision)
- [Build in this order](#build-in-this-order)
- [Check setup and trial isolation](#check-setup-and-trial-isolation)
- [Run deterministic checks](#run-deterministic-checks)
- [Run and inspect the Harness](#run-and-inspect-the-harness)
- [Revise the correct layer](#revise-the-correct-layer)
- [Finish with reusable knowledge](#finish-with-reusable-knowledge)

## Read references at each decision

| Current decision | Read | Required output |
|---|---|---|
| What state, service, access, fidelity, or trial isolation to build | [Environment building](environment-building.md) | Environment contract and setup or isolation method recorded in `Task.md` |
| How to create structured records or natural-language content | [Synthetic data](synthetic-data.md) | Materialized data, validation evidence, and generation review when used |
| What evidence proves success and how failures score | [Verifier design](verifier-design.md) | Pass rule, criteria, independent evidence, and focused fixtures |
| How to package, configure, and run the Task | [Harbor](harbor.md) | Runnable task source, resolved configuration, and retained job evidence |
| How to inspect traces and judge fairness | [Calibration](calibration.md) | Run classifications, defects, rerun results, and remaining uncertainty |
| How to preserve reusable project knowledge | [World knowledge](world-knowledge.md) | World Skill additions, corrections, or an explicit decision that none are reusable |

Read only the references required by the current Task, but do not implement a
layer before reading the reference that defines its checks.

## Build in this order

### 1. Synchronize the Task files

Create `instruction.md` from the exact agent input in `Task.md`. Normally this
input has explicit approval. If the human requested an end-to-end build with
no approval pause, implementation can use the agent-reviewed Draft input, but
`Task.md` must remain `Status: Draft`. Create the complete package defined in
[Harbor](harbor.md): `task.toml`, `instruction.md`, a usable Environment
definition, and `tests/test.sh`, plus only the optional Verifier helpers,
fixtures, and reference solution the Task needs. Check that later turns,
access, time limits, and invalid-run conditions match the Task Spec.

Read the project World Skill used during design. Add or correct only reusable
knowledge supported by the current implementation work. Keep the exact request,
focal records, expected result, hidden truth, and exact scoring rules in
`Task.md`.

### 2. Build the Environment

Follow [Environment building](environment-building.md). Preserve the
production interface used by the Harness. Implement only the services, files,
records, permissions, errors, and state changes needed by this Task. Keep
hidden truth and raw Verifier access unavailable to the evaluated agent.
Update the World Skill when this work proves a reusable project setup, service,
state, access, or isolation method.

### 3. Build and validate data

When the Task needs constructed data, follow [Synthetic data](synthetic-data.md).
Create IDs, relationships, permissions, dates, and constraints with code. Use a
model only for fields that need natural language. Materialize the accepted data
so every trial uses the same reviewed input.
Update the World Skill when the method, schema, relationship rule, or validator
can support another Task.

### 4. Build the Verifier

Follow [Verifier design](verifier-design.md). Implement objective checks from
raw files, tests, database state, service state, or other independent evidence.
Use a model judge only for bounded semantic meaning that code cannot settle.
Keep judge instructions, credentials, and expected results outside the Harness
boundary.
Update the World Skill when this work proves a reusable independent evidence
source, accepted alternative, or known scoring risk.

### 5. Package the Harbor Task

Follow the package-completeness audit in [Harbor](harbor.md). Confirm that every
required file, entry point, path, permission, configuration value, mount,
service, dependency, and reward output needed to run the exact Task exists and
works through Harbor. Confirm hidden Task, Verifier, solution, and secret
material is absent from the agent-visible image and workspace. Fix every gap
before any Oracle or model trial. Then confirm the model, trial count, judge,
timeout, and maximum expected cost with the human unless that run plan is
already authorized.

## Check setup and trial isolation

Reset means returning mutable state to the Task's declared starting condition
before another trial uses it. It is an infrastructure concern, not a score of
Task quality. Choose the check that matches the Environment:

| Environment | Appropriate check |
|---|---|
| Fresh disposable container, VM, or worktree per trial | Build one fresh trial and verify its declared starting state. Replacement provides isolation. |
| Mutable service or database reused across trials | Capture Task-relevant starting state, make a representative change, run reset, and confirm the starting state returns. |
| Immutable frozen files, corpus, or repository | Verify the pinned source loads correctly. No reset test is needed. |
| Approved live sandbox | Verify the dedicated identity, safe starting state, allowed effects, and cleanup method. Do not use production writes. |

Create or compare another fresh trial only when nondeterminism, shared state,
or flaky setup is a real risk. Record expected runtime differences only when
they cannot affect agent behavior or scoring.

## Run deterministic checks

Before a model run:

1. Call every operation the Task needs and confirm its response and effect.
2. Confirm relevant invalid actions fail for the intended reason.
3. Run the reference path when one exists to prove the Task is reachable.
4. Run Verifier fixtures for a known-good result, a different valid result, a
   realistic wrong result, a shortcut, a prohibited collateral change, and
   missing or corrupt evidence.
5. Confirm wrong work receives zero and infrastructure faults receive no agent
   score.
6. Confirm every completed Verifier path writes criterion evidence and reward.

Fix deterministic failures before spending a model call. These checks establish
reachability and Verifier behavior. They do not by themselves prove that the
Task has the intended difficulty or realism.

## Run and inspect the Harness

Run the actual Harness through Harbor. Follow [Calibration](calibration.md).
Read the complete selected trajectories, initial and final state, Verifier
evidence, service logs, resolved configuration, phase timing, and errors.

Classify each bad outcome before changing anything. Keep a fair capability
failure as an agent result. Repair missing information, Harness defects,
Environment defects, false acceptance, false rejection, leakage, and
infrastructure failure, then rerun the affected trial.

## Revise the correct layer

| Evidence shows | Change |
|---|---|
| The request is unclear or unfair | `instruction.md` and `Task.md` |
| Required state is missing or unrealistic | Environment implementation and its description in `Task.md` |
| A valid result fails or invalid result passes | Verifier and its fixtures |
| Tools, prompts, sessions, or adapters differ from the intended agent | Harness or adapter |
| Startup, timeout, credential, judge, or cleanup fails | Harbor or runtime configuration; keep the old run unscored |

For a material Task Spec change, set `Task.md` to `Draft`, show the diff, and
require explicit reapproval before marking it `Approved` again.

## Finish by reconciling reusable knowledge

After the Task passes its audit, follow [World knowledge](world-knowledge.md)
and reconcile the World Skill already used during design and implementation.
Keep supported project-specific knowledge that can help another Task. Narrow or
remove claims that the audit disproved. Keep the current Task's exact request,
focal state, expected result, hidden truth, and scoring criteria in its Task
directory. Show the final World Skill changes with the audit results.
