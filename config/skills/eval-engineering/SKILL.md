---
name: eval-engineering
description: Iteratively inspect an agent repository and optional user-provided traces, interview the user, and create, run, and audit Harbor evals one at a time. Use for agent evals, Harbor tasks, benchmark cases, verifier design, or controlled agent environments.
---

# Eval Engineering

Create one Harbor task at a time, run it, inspect the result, and repeat with the user.

```text
map harness + environment -> propose directions -> user chooses
-> draft specs -> user approves -> build + run + audit -> repeat
```

Use the latest Harbor release. Put task source under `evals/`.

## Boundaries

- **Task:** `instruction.md` plus an Environment and Verifier.
- **Harness:** the complete agent Harbor runs: model, prompts, loop, repository-defined tools, middleware/hooks, memory/session behavior, and Harbor adapter. Harbor calls this the Agent.
- **Environment:** the container/world around the Harness: OS, files, backing data, services, identity, permissions, network, clock, and mutable state.
- **Verifier:** the test script that independently scores the response, trajectory, or resulting Environment state.

Repository-defined tool code belongs to the Harness. The data or service behind it belongs to the Environment. Example: a docs agent's `search_docs` definition and result parsing stay in the Harness; the frozen search index and its error behavior live in the Environment. If production supplies a tool server dynamically, keep that server in the Environment and preserve how the Harness discovers and calls it.

## References

Read each reference when its decision appears:

- [Trace sourcing](references/trace-sourcing.md): select and analyze traces only when the user supplies a source.
- [Harness](references/harness.md): identify the actual agent Harbor will run and preserve its behavior.
- [Task design](references/task-design.md): turn one selected capability into a judgeable request.
- [Environment building](references/environment-building.md): choose live, frozen, or simulated backing data and services.
- [Multi-turn simulation](references/multi-turn-simulation/guide.md): run scripted or LLM-generated user turns through one Harness session.
- [Verifier design](references/verifier-design.md): define independent evidence, scoring, and calibration.
- [Harbor](references/harbor.md): create, run, and inspect the Harbor task.

## 1. Map the Harness and production Environment

Start at the public agent entrypoint and follow reachable code.

```text
Harness: entrypoint; prompts; models; loop; routing; retries; hooks; memory;
         repository-defined tools, inputs, outputs, and effects
Environment: files; records; indexes; services behind tools; identity;
             permissions; network; time; mutable state
Purpose: intended users, jobs, and useful outcomes
Evidence: tests, fixtures, issues, existing evals, and documented failures
```

Do not start services, install packages, or use credentials during mapping. Explain the map in the conversation and ask only what code cannot answer, such as “Which user job matters most?” or “What failure must this eval catch?”

If the user provides traces, read [Trace sourcing](references/trace-sourcing.md). Use trace evidence only when it changes an eval direction, dependency behavior, realistic request, or failure case. Never treat the recorded answer as truth.

## 2. Propose eval directions

Offer two or three capabilities grounded in the map and any supplied traces:

```text
Name: choose the correct account lookup
Example request: “What plan is account A on?”
Tests: looks up A, uses the returned plan, and does not invent account details
Needs: known account records behind the existing read-only lookup
```

Recommend one and explain why. The user chooses before implementation.

## 3. Draft and approve the specs

Read the Harness, task, Environment, and Verifier references. After the user chooses a direction, write:

```text
evals/specs/<task-id>/
├── harness.md
├── environment.md
└── task.md
```

These are control-plane review files. Never copy or mount them into the Harness workspace or task image. `task.md` is the review spec; Harbor's `instruction.md` is the Harness-visible request created from the approved spec.

- `harness.md`: entrypoint, preserved behavior, adapter, sessions, credentials, recorded evidence, and reconstruction differences.
- `environment.md`: live/frozen/simulated dependencies, backend contracts, generated or copied data, schemas and relationships, storage, effects, reset, and fidelity limits.
- `task.md`: capability, request, initial conditions, pass condition, Verifier evidence, and accepted alternatives.

For each dependency, recommend live, frozen, or simulated use. Read-only, low-cost services backed by hard-to-reproduce data are strong live candidates. Stable copied data is a strong frozen candidate. Writes, unstable services, and resettable state are strong simulation candidates. State required credential names for live use.

Print the full contents of all three specs in the terminal, keeping them concise. Show their paths and your recommendation, then ask the user to approve or revise them. Mark each spec approved only after explicit user approval. Do not build the Harbor task until all three are approved. If implementation changes an approved boundary, update the affected spec, show the change, and obtain approval again.

For multiple user turns, prefer fixed follow-ups when they do not depend on Harness responses. Use an LLM user only when replies must react, correct, reject, or stop; read the multi-turn reference and include simulator credentials in the proposal.

## 4. Build one Harbor task

```text
evals/<task-id>/
├── task.toml
├── instruction.md
├── environment/
└── tests/
```

Use the approved Harness unchanged when possible. Add an adapter only when Harbor needs one to invoke it. Do not expose hidden truth, simulator instructions, verifier criteria, or judge credentials to the Harness.

Use an LLM judge for semantic success and deterministic checks for objective state. Example: a judge checks whether an answer is supported by supplied documents; code checks whether the requested record changed. Emit one primary reward.

## 5. Run and audit

Test the Verifier with one clearly valid result and one realistic wrong result. Run the Harness through Harbor, then inspect:

- Harness-recorded messages, model/tool calls, results, retries, and errors;
- Environment-observed service results, initial/final state, and reset;
- Verifier evidence, decision, reason, reward, and errors;
- resolved Harness and Environment configuration.

Fix and rerun until the Harness exercised the selected capability and the Verifier scored that behavior. If the Environment leaked the answer, a wrong answer passed, a valid answer failed, or infrastructure failed, the eval is not complete.

For an LLM user, inspect representative correct, wrong, clarification, and stop paths. Revise its contract or model when its replies are implausible. Simulator termination is not success; the Verifier alone assigns reward.

## 6. Review and repeat

Explain the task path and exact Harbor command, request, Harness, Environment, run behavior, Verifier decision, and main limitation. Completion requires a real Harbor run, evidence that the Verifier measured the intended capability, and user approval. If continuing, reuse the available evidence and propose a distinct capability.

## Invariants

- One capability per Harbor task.
- No production writes; reset mutable state between trials.
- Keep hidden truth and simulator/judge credentials unavailable to the Harness.
- Treat build, credential, reset, timeout, judge, and Verifier failures as infrastructure errors, not failed agent work.
