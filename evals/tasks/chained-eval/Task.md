# Chained online evaluation

Status: Draft (exploratory, unscored)

## Purpose

Evaluate whether the installed LangChain skills and documentation MCPs help a
coding agent configure a working, multi-stage LangSmith online evaluation.
The exact agent instruction is in `instruction.md`, copied unchanged from the
November 7, 2026 four-condition study. This task deliberately supplies no
evaluator, scorer, reference solution, or automated reward. The agent must
decide what to build from the seed traces and workspace documentation.

## Environment and evidence

Each trial receives a fresh target tracing project containing the four `seed`
conversations in `fixtures.json`. After the agent finishes, the harness emits
the four `held_out` conversations with the same text used in the prior study.
The harness records the resources created, feedback on the held-out runs,
the agent trajectory, and cost and latency. A profile comparison is descriptive;
it is not a pass/fail claim. The target project is distinct from the shared
Harbor/Claude tracing project so one profile's online evaluator rules cannot
affect another profile's traces.

## Fairness and limits

The seed cases cover unsupported refund and billing changes as well as
supported product and ticket requests. They are visible to the agent as
LangSmith runs, not as a local answer file. The held-out case text is kept
outside `environment/` and is emitted only after agent completion. Different
valid implementation paths are allowed. Workspace-level resources such as
annotation queues may still be reused by an agent; the report identifies such
resources when observable and never interprets reuse as an isolated result.

The previous one-attempt study found first-stage scores for the full profile
but did not observe a gated judge verdict within eleven minutes. This task
does not treat that absence as proof of a specific failure cause.
