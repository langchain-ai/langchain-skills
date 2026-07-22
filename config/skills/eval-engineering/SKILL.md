---
name: eval-engineering
description: Iteratively inspect an agent repository and optional traces, interview the user, and create, run, and audit Harbor evals one at a time. Use for agent evals, benchmark tasks, regression cases, trace-informed evals, verifier design, or controlled agent environments.
---

# Eval Engineering

Build evals iteratively:

```text
inspect agent and interview user -> propose directions -> user chooses
-> approve runtime and environment -> build, run, audit -> review and repeat
```

Use the latest version of Harbor. Put task source under `evals/`. Read [references/harbor.md](references/harbor.md) before creating or running a task.

## 1. Map the agent

Inspect the active agent and code reachable from its public entrypoint. Find:

- runtime: entrypoint, input/output, prompts, models, routing, retries, hooks, middleware, and memory;
- actions: tools, inputs, outputs, failures, external dependencies, and effects;
- backing data: documents, records, indexes, files, policies, schemas, and source/version when available;
- state: identity, permissions, filesystem, network, time, sessions, and mutable state;
- purpose: intended users, jobs, and what a good result provides;
- evidence: tests, fixtures, issues, existing evals, and documented failures.

Mapping is read-only. Do not start the target or services, install packages, or use external credentials before the user approves the runtime and environment.

Summarize the map in the conversation:

```text
Agent: target and entrypoint
Purpose: users and jobs
Abilities: work it is expected to perform
Tools and data: actions, backing data, and dependencies
Effects: reads, writes, and state changes
Evidence: tests, failures, or traces
```

Use code to model the agent; do not turn implementation details into the eval question unless answering questions about that code is the agent's job.

Keep the user involved: explain the map and what it implies in plain language, then ask only for information the repository and traces cannot establish. For example: “Which user job matters most?”, “What failure should never happen?”, or “What would a good result look like?”

### Optional traces

Use traces only when the user provides a source or asks to use them. Read [references/trace-sourcing.md](references/trace-sourcing.md). Use selected traces to identify real requests and dependency behavior, and never treat a recorded target answer as truth.

## 2. Discuss and choose an eval direction

Propose two or three capabilities grounded in the map. For each, give:

```text
Name
Example request: realistic request sent to the agent
Tests: behavior the eval distinguishes
Needs: main obstacle, data, or environment requirement
```

Example:

```text
Name: choose the right account lookup
Example request: “What plan is account A on?”
Tests: retrieves account A, uses the returned plan, and does not invent account details
Needs: a read-only account lookup with known records
```

Recommend one and ask the user which to build. The request must make the agent exercise the capability: use multiple turns for context use, competing tools for tool choice, source material for retrieval, or known state for an action.

Do not implement until the user chooses.

## 3. Checkpoint: approve runtime and environment

Read [references/task-design.md](references/task-design.md) and [references/environment-building.md](references/environment-building.md). Design one scenario that requires the selected capability.

Recommend a target runtime:

- **Active entrypoint:** preserve the repository's agent behavior. Recommend this when it can run safely.
- **Reconstruction:** use only when the active entrypoint cannot run in a controlled eval. Name the behavior it cannot preserve and label the eval as a reconstruction.

Before implementation, give the user one proposal under 150 words:

```text
Task: request and capability
Runtime: active entrypoint or reconstruction, with tradeoff
Dependencies and backing data: live, frozen, or simulated; required credentials if live, effects, and source/version
Success: how the result is judged
Recommendation: preferred setup and why
```

The user approves or revises the target runtime and environment boundary. Never write to production; isolate mutations.

## 4. Build one Harbor task

Create one task for the selected capability:

```text
evals/<task-id>/
├── task.toml
├── instruction.md
├── environment/
└── tests/
```

Add an adapter or non-default configuration only when Harbor needs it to invoke the approved target runtime. Keep instructions and environment facts visible to the target; keep expected outcomes, judge criteria, and judge credentials unavailable to it.

An adapter may translate I/O and inject approved dependencies. It must not make target decisions, contain answers, or fabricate actions. Custom adapters and verifiers must write the target response/action record, verifier evidence, verdict/reason, reward, and errors to Harbor artifacts or verifier logs. Do not add `audit.json` or another result ledger.

Use an LLM judge for semantic success and deterministic checks for execution, parsing, files, or state. Read [references/verifier-design.md](references/verifier-design.md). Emit one primary reward.

## 5. Test, run, and audit

Start the minimum environment before completing the scenario. Test the verifier directly with one clearly valid result that passes and one realistic incorrect result that fails.

Run the approved target runtime through Harbor. Inspect:

- target response and trajectory;
- harness-observed tool calls, actions, and state;
- verifier evidence, verdict, reason, reward, and errors;
- resolved target and environment configuration.

Fix and rerun when the task is unclear, the environment is unrealistic, the verifier is wrong, or infrastructure failed. Before approval, confirm that the target exercised the selected capability and the verifier scored that behavior, not an environment or verifier failure. If the environment returned the answer before the target used the intended tool, revise the task.

## 6. Review with the user

Explain the task path and run command, capability and scenario, runtime and dependency boundary, target behavior, verifier decision, and limitation. Ask the user to approve, revise, drop, or choose the next direction. If continuing, reuse the map and trace findings, then propose a distinct capability.

## Invariants

- One capability per Harbor task under `evals/`.
- No production writes; reset mutable state between trials.
- Keep hidden truth and judge credentials unavailable to the target.
- Treat build, credential, reset, timeout, judge, and verifier failures as infrastructure errors.
