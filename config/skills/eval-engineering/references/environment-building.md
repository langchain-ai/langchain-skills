# Environment Building

Build the smallest resettable world that preserves the production behavior the
Task needs. Put Task-specific choices in the collocated `Task.md`. Put proven,
reusable project methods in the project World Skill.

## Define the boundary

The Environment owns files, data, services, identity, permissions, network,
clock, flags, initial state, effects, and reset. The Harness owns prompts, the
model loop, tools, hooks, memory, sessions, and parsing. A tool server can run
in the Environment, but its interface must match what the Harness expects.

Choose each dependency deliberately:

| Mode | Use when |
|---|---|
| Live | A safe read-only dependency is hard to reproduce and can be pinned or recorded. |
| Frozen | Content must stay stable, such as a document corpus or repository revision. |
| Simulated | Writes, failures, permissions, time, or state must reset for each trial. |

Default to controlled local dependencies. State what differs from production.
Never write to production during an eval.

## Write the contract in `Task.md`

Record:

- exercised operations and exact request and response shapes;
- source of truth, initial records, relationships, and constraints;
- identity, permissions, time, ordering, pagination, and relevant errors;
- reads, writes, external effects, and reset;
- evidence from code, tests, traces, or approved production reads; and
- fidelity limits and agent-visible information.

Define one canonical truth source for each part of state. A cross-system Task
can use several stores when the production decision depends on their distinct
behavior. Keep IDs, time, and generated values stable. Enforce domain rules in
the backend, not in a prompt or Verifier. Do not key behavior on the Task ID,
expected answer, exact instruction, or hidden tool sequence.

## Preserve relationships

Create a relationship-complete subset. Include each record needed to exercise
the decision and each related record needed to make it valid. For a ticket,
this can include its account, requester, owner, entitlement, and relevant
history. Do not add random distractors. Each extra item must test a named
condition such as ambiguity, freshness, permissions, or a constraint.

Use the smallest faithful injection point: a fixture, temporary workspace,
seeded SQLite database, local endpoint, frozen corpus, or local tool server.
Keep production tool names, schemas, parsing, and exercised errors. Replace the
service or data behind the interface, not repository tool code.

## Protect hidden evidence

The Harness must see state only through its normal interface. The Verifier can
read raw final state through a separate boundary. Do not expose expected
results, hidden tests, judge rules, reference actions, or a state dump tool to
the evaluated agent.

Record non-secret requests, responses, errors, and mutations when they occur.
Capture initial and final state. Use one Environment instance per trial. Keep
state across turns. After timeout or failure, destroy and replace a disposable
Environment or reset reused mutable state. Make reset safe to run more than
once when reset is the isolation method.

## Check fidelity before a model run

1. Check trial isolation in the way this Environment needs. For reused mutable
   state, make a representative change, reset, and confirm the Task-relevant
   baseline returns. For a fresh disposable Environment, verify one clean
   construction. For immutable frozen data, verify the pinned input loads; no
   reset check is needed.
2. Call every operation the Task needs.
3. Confirm valid actions succeed and invalid actions fail for the right reason.
4. Compare schemas, ordering, permissions, errors, and state changes with
   production evidence when approved evidence exists.
5. Run a reference path when reachability is uncertain.
6. Confirm the agent cannot read hidden truth or bypass the normal interface.
7. Run the real Harness and inspect whether the Environment created the
   intended decision.

Copy reusable setup, reset, schema, or fixture methods into the project World
Skill only after real Tasks prove them useful.
