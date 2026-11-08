# Thread-level LLM judge

Status: Draft (exploratory, unscored)

## Purpose

Find out what CLI guidance the online-evaluation skill must carry beyond the
LangSmith CLI's own help and the documentation MCPs. The agent must create a
thread-level LLM-as-judge online evaluator for a multi-turn support assistant.
The instruction names the behavior and the thread scope but not the tool, so
the trajectory shows whether the agent loads the skill, which commands it
tries, and where it gets stuck.

## Environment and evidence

Each trial receives a fresh target tracing project containing the four `seed`
threads in `fixtures.json`, emitted as one root run per turn with a shared
`thread_id`. After the agent finishes, the harness emits the four `held_out`
threads. The report records the enabled rules on the target project (type,
grouping, variable mapping keys, feedback keys, filters), feedback on the last
turn of each held-out thread next to its `expected_resolved` label, and the
agent's tool and skill usage.

## Fairness and limits

Resolution depends on later turns, so a run-level evaluator on a single turn
cannot judge it reliably. Expected labels live outside `environment/` and are
used only for descriptive comparison. One trial per profile is an anecdote,
not a rate.
