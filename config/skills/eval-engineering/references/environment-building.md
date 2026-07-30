# Environment Building

The Environment is the resettable container/world around the Harness. Build only what the approved task needs.

It owns:

- OS, packages, files, and workspace layout;
- backing documents, records, indexes, policies, and fixtures;
- services and state behind Harness tools;
- identity, permissions, network, clock, and feature flags;
- initial state, observable effects, and reset between trials.

It does not own the Harness's prompts, loop, model decisions, repository-defined tool code, retries, parsing, or final response. A tool server supplied to the Harness at runtime may live in the Environment.

## Choose each dependency

| Option | Use when | Example |
|---|---|---|
| Live | Read-only, low-cost, stable, safely credentialed, and difficult to reproduce | query a large internal catalog without mutation |
| Frozen | Results must stay stable across trials | serve a pinned docs corpus and search index |
| Simulated | Writes, permissions, failures, or state must reset | local ticket service with known initial records |

Tell the user what is live, frozen, or synthetic; what credentials live access needs; and what effects are possible. Record a source revision, timestamp, or hash for copied data. Mark constructed records as synthetic.

## Write `environment.md`

Before implementation, write `evals/specs/<task-id>/environment.md`:

```text
Status: draft | approved
Dependencies: name, live/frozen/simulated mode, implementation, credentials, effects
Backend contracts: exercised operations, schemas, rules, failures, and permissions
Data: each dataset's purpose, source or generation rule, structure, relationships,
      representative records, storage backend, and reset
Isolation: filesystem, network, identity, clock, and per-trial state
Fidelity limits: behavior intentionally not reproduced
```

Make generated data concrete enough to review before it exists. Example:

```text
Dataset: accounts and tickets
Purpose: require disambiguation between two same-name accounts
Structure: accounts{id, name, plan, active}; tickets{id, account_id, status}
Relationships: tickets.account_id -> accounts.id
Records: two active Sam Lee accounts on different plans; one closed distractor
Storage: seed.json materialized into SQLite tables `accounts` and `tickets`
Generation: fixed synthetic records; neutral IDs and shuffled insertion order
Reset: recreate the SQLite file from seed.json for every trial
```

Set `Status: approved` only after the user approves this file with `harness.md` and `task.md`.

## Define the backend contract

Write the contract before choosing an implementation:

```text
Interface: operations and exact request/response schemas
State: source of truth and initial records
Rules: validation, permissions, and domain invariants
Failures: errors the task can exercise
Effects: reads, writes, and external actions
Reset: how the initial state is restored
Evidence: repository code, tests, and supplied traces supporting the contract
```

Include only task-exercised behavior: schemas, validation and errors, ordering or pagination, identity and permissions, mutations, domain rules, and time.

Example:

```text
Interface: search_docs(query, limit) -> [{path, title, snippet, score}]
State: pinned document corpus and search index
Rules: enforce result limit and caller permissions
Failures: empty results and missing documents
Effects: read-only
Reset: reload the pinned corpus
Evidence: search wrapper, integration tests, and supplied traces
```

## Choose the implementation and data

Use the smallest injection point that preserves the contract: fixture, dependency override, temporary workspace, test database, local endpoint, or existing integration harness.

| Need | Example implementation |
|---|---|
| Small single-process state | typed objects loaded from a JSON fixture |
| Relational queries or transactions | seeded SQLite or an existing test database |
| Harness calls a production HTTP client | local service implementing the exercised endpoints |
| Production supplies tools dynamically | local MCP server advertising the exercised schemas |
| Read-only files or retrieval | pinned directory, corpus, or search index |

Do not replace repository-defined tool code with a task-specific implementation; replace the service or data behind it.

If generation is necessary, use synthetic identities, a fixed seed, and a materialized fixture so every trial receives the same records. Before implementation, show the proposed records or files and why each exists. Reject a fixture when the Harness can succeed by selecting the only option, following record order, reading answer-coded names, or bypassing the production interface.

## Build the backend and world state

Use one canonical state store. Give IDs, time, and generated values deterministic behavior. Enforce domain rules in the backend, not in the prompt or Verifier. For example, a reservation service should reject an overlapping booking even if the agent never checked availability first.

Seed only data needed to create the selected decision: valid candidates, relevant invalid candidates, and existing state that changes the outcome. Every extra record should exercise a named behavior such as search, ambiguity, permissions, or a constraint. Do not add random distractors.

When traces inform the backend, compare only the exercised schemas, errors, ordering, permissions, and state transitions. Do not recreate unrelated production behavior or copy production records.

Never key results on the task ID, expected answer, exact instruction wording, or a hidden required tool sequence.

## Examples

### Docs search

Task: determine the current account-deletion retention period.

Bad: one file named `account-deletion-answer.md` containing “30 days.”

| Document | Content | Why included |
|---|---|---|
| Current account-deletion policy | 30 days; effective 2026 | supports the answer |
| Archived account-deletion policy | 60 days; superseded in 2025 | requires freshness checking |
| Workspace-deletion policy | 14 days for workspaces | requires scope checking |
| Account-recovery FAQ | recovery process without a retention period | plausible nearby search result |

Serve these through the production-shaped search result schema and document-reading interface. Keep the documents as independent truth for the Verifier. Add empty results or missing pages only when the task exercises them.

### Reservation service

Task: reserve adjacent indoor tables for parties of four and two.

Bad: one available record named `CORRECT_TABLE`.

| Table | Capacity | Area | Available | Adjacent to | Why included |
|---|---:|---|---|---|---|
| T1 | 4 | indoor | yes | T4 | fits four but has no suitable adjacent table |
| T2 | 4 | indoor | yes | T3 | valid first table |
| T3 | 2 | indoor | yes | T2 | valid adjacent second table |
| T4 | 4 | outdoor | yes | T1 | fails the indoor requirement |
| T5 | 6 | indoor | no | T3 | large enough but already reserved |

The service enforces capacity, overlap, and permissions when creating reservations. The Verifier checks the required reservations and prohibited changes from independent initial and final state.

### Coding agent

Task: fix checkout totals without breaking discounts.

Bad: one failing test that reveals the expected implementation and no existing discount coverage.

| Workspace item | Why included |
|---|---|
| Public failing checkout-total test | reproduces the reported behavior |
| Existing percentage- and fixed-discount tests | define behavior that must remain valid |
| Hidden discount-plus-tax regression | checks the outcome without revealing the fix |
| Two plausible calculation paths in repository code | requires diagnosis rather than editing a named line |

Pin the repository revision and dependency lockfiles. Use a writable task workspace and the real build and test commands when safe and deterministic. Reset by restoring the pinned workspace and removing trial-generated files. Simulate an external service only when the task reaches it.

## State, evidence, and isolation

For mutable controlled dependencies, create one backend instance and state store per trial. Preserve state across turns, then reset from a declared baseline even after Harness, timeout, or Verifier failures. Make reset idempotent.

Record non-secret task-relevant requests, responses, errors, and mutations as they occur. Preserve initial and final state for verification.

The Harness sees state through the same interface it has in production. The Verifier may inspect raw final state after the run through a boundary unavailable to the Harness. Example: the Harness can list tables and create reservations; the service owns `reservations.sqlite`; the Verifier reads final rows, but the Harness cannot open that database or call a `dump_state` endpoint. Keep expected outcomes, judge rules, and hidden tests unavailable to the Harness.

Default to no production access. Allow only approved live hosts and pass credentials at runtime, never through images, prompts, fixtures, or logs.

## Validate

Before accepting the Environment:

1. Call every operation exercised by the task and check its response shape.
2. Confirm relevant valid actions succeed and invalid actions fail for the right reason.
3. Confirm mutations are observable and two resets produce the same baseline.
4. When an approved production read or fixture exists, send the same fixed request through it and the replacement; compare response schema, ordering, permissions, and errors, then record known differences.
5. For a complex scenario whose solvability is uncertain, run one reference path. It proves reachability but never constrains the Harness's tool sequence; the Verifier must accept equivalent successful states.
6. Run the real Harness through Harbor and confirm the Environment created the intended decision rather than leaking the answer or causing an infrastructure failure.
