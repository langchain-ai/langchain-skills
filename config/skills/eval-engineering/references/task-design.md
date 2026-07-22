# Task Design

Design one question that makes the selected capability necessary.

## The contract

Define four lines internally before implementing:

~~~text
Capability: the behavior being measured
Question: the concrete request given to the target
Environment: the information and actions available
Success: the observable qualities of a capable result
~~~

Reject the design when a target can succeed without the capability, when required information is missing, or when success is too ambiguous to judge.

Compare it with existing evals. Reject a case that changes only names, wording, or fixtures. Reusing a capability is useful when the new case introduces a distinct obstacle, state, evidence condition, or failure mode.

## Judge evidence

Choose evidence independently of the target's answer. A reference answer is valid only when it comes from independent source material:

| Domain | Evidence |
|---|---|
| Coding | failing case plus behavior and regression tests |
| Search / Q&A | pinned source records supporting or contradicting the answer |
| Analysis | independently recomputed result from the supplied raw data |
| Tool use | harness-observed calls, returned data, and resulting state |
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

- Use the user-approved target runtime; prefer the active entrypoint.
- Put the task under `evals/<task-id>/`.
- Prefer the existing runtime and data.
- Include only context needed for this capability.
- Do not expose expected conclusions or verifier criteria.
- Do not prescribe a tool sequence, file, wording, or implementation unless it is part of the capability.
- Allow materially equivalent valid solutions.
- Start mutable tasks from known state and reset after every run.
