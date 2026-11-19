# Regression experiment from plain-language requirements

Status: Draft (exploratory, unscored)

## Purpose

Evaluate whether the agent-experiments skill helps a coding agent turn a
support lead's written requirements into a LangSmith dataset and an experiment
whose scores point at the requirement that broke. The skill's claim is the
order of work: inspect the application's real output, store the requirements
as assertions, grade each with deterministic code where the claim allows, and
never copy the application's own output as the reference. The instruction
names the outcome but not the skill, CLI, `evaluate()`, or assertions.

## Environment and evidence

`/app/support_agent.py` is a LangChain `create_agent` agent with a scripted
model: it routes on the question and the tool results already in the
conversation, so every trial sees the same answers in about a second, with no
provider calls. It returns the agent state, so the final answer is the last of
several messages and tool calls appear in earlier ones. `/app/cases.md` holds
six questions with two requirements each. The agent breaks exactly two of
them, which only `expected.json` (outside `environment/`) records:

- `warranty-length`: says 12 months, not 24 (first requirement).
- `damaged-order`: promises a refund without opening a ticket (second
  requirement).

`prepare` assigns the trial a dataset name and passes it as
`TARGET_DATASET_NAME`. The live report records the dataset's examples mapped
to case IDs, each experiment on the dataset with its runs' case, error state,
feedback keys, and scores, and the IDs of rules bound to the dataset. It never
stores inputs, outputs, or feedback comments.

## Pass rule

Pass iff the dataset holds each of the six cases once, and the latest
experiment that ran and scored every case without errors still shows the
shipped behavior, scores some requirement as failing and another as passing on
each of the two broken cases, with different failing keys for the two, and
scores nothing as failing on the other four.

A score fails when it is below 1 for a key whose scores all lie in [0, 1], and
below the key's best observed score otherwise. Any evaluator mechanism, key
naming, judge, or repetition count passes. The checks are:

- `dataset`: six examples, one per case, matched by question text.
- `experiment`: a complete experiment exists; the latest one is scored.
- `app_unchanged`: the warranty answer still says 12 months and the damaged
  order still has no `open_ticket` call.
- `failures_localized`: per-requirement scores on the two broken cases.
- `no_false_failures`: no failing score on the four correct cases.

## Fairness and limits

The failure modes the checks catch: evaluators that guessed the output shape
fail every case (`no_false_failures`); references copied from the agent's
output pass the broken cases (`failures_localized`); one overall score, even
with a constant second key, fails both broken cases on the same key
(`failures_localized`); fixing the agent fails `app_unchanged`. A key whose
high score means failure, or requirements scored only in feedback comments,
are reported as failures; read the trajectory before attributing them to the
skill. The agent's written explanation of the failures is not scored. Cleanup
deletes the trial dataset, its experiments, and its bound rules after the live
report records the dataset ID. One trial per profile is an anecdote, not a
rate.
