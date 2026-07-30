# Task Design

Design one request that makes the selected capability necessary.

## Write `task.md`

Before implementation, write `evals/specs/<task-id>/task.md`:

```text
Status: draft | approved
Capability: behavior being measured
Request: exact instruction later placed in Harbor's instruction.md
Initial conditions: information, permissions, and state available
Why this requires the capability: shortcut the task rules out
Pass iff: independently observable successful outcome
Verifier: LLM judge, deterministic check, or both
Verifier evidence: exact sources, trajectory fields, or initial/final state
Accepted alternatives: materially equivalent successful outcomes
```

`task.md` is a control-plane review spec, not Harness input. Set `Status: approved` only after the user approves it with `harness.md` and `environment.md`.

## The contract

Define this before implementation:

~~~text
Capability: behavior being measured
Request: concrete instruction sent to the Harness
Initial conditions: information, permissions, and state available
Required outcome: independently observable success
~~~

Reject it when the Harness can succeed without the capability, required information is missing, or success is ambiguous.

When a trace informs the task, preserve the condition that required the capability, not the production wording or records. Example: recreate “lookup returned two same-name accounts and required disambiguation” with synthetic accounts.

Compare it with existing evals. Reject a case that changes only names, wording, or fixtures. Reusing a capability is useful when the new case introduces a distinct obstacle, state, evidence condition, or failure mode.

## Judge evidence

Choose evidence independently of the Harness's answer. A reference answer is valid only when it comes from independent source material:

| Domain | Evidence |
|---|---|
| Coding | failing case plus behavior and regression tests |
| Search / Q&A | pinned source records supporting or contradicting the answer |
| Analysis | independently recomputed result from the supplied raw data |
| Tool use | Harness-recorded calls plus Environment-observed results/state |
| Stateful action | initial state, policy/permissions, final state, and allowed change |

If the judge cannot determine success from this evidence, change the question or environment before writing the rubric.

## Examples

| Domain | Capability | Question shape | Minimum environment |
|---|---|---|---|
| Coding | repair without regression | reproduce and fix a specific failure | repository, failing case, runnable tests |
| Search / Q&A | evidence-grounded synthesis | answer a question requiring several sources | searchable corpus with relevant and distracting records |
| Analysis | correct reasoning from data | compute and explain a decision-relevant result | raw data, definitions, relevant edge cases |
| Tool use | select and use the right tool | complete a request with competing tools | realistic tool interfaces, results, and errors |
| Stateful action | make a safe change | update requested state while preserving constraints | known initial state, permissions, observable final state |

## Rules

- Put the task under `evals/<task-id>/`.
- Include only context needed for this capability.
- Do not expose expected conclusions or verifier criteria.
- Do not prescribe a tool sequence, file, wording, or implementation unless it is part of the capability.
- Allow materially equivalent valid solutions.
- Start mutable tasks from known state and reset after every run.
