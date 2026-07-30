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

## Implement behind the existing boundary

Preserve the interface the Harness already calls. Use the smallest injection point: fixture, dependency override, temporary workspace, test database, local endpoint, or existing integration harness.

For a docs agent:

```text
Harness owns: `search_docs(query)`, argument validation, result parsing, retries
Environment owns: frozen index, relevant pages, distractors, missing pages,
                  empty results, and timeout responses
```

For each replaced dependency, specify only behavior the task exercises:

```text
Binding: HTTP `GET /accounts/{id}`
Results: known record, missing ID, unauthorized ID
Effects: read-only
Context: caller identity and permissions
```

When traces inform the replacement, check the exercised request and result schemas, error shape, ordering, pagination, permissions, and state transitions against those traces. Do not recreate behavior the task never reaches.

Do not key a result on the task ID, expected answer, or exact request wording.

## State and reset

Use one source of truth for mutable state. Preserve state across turns, then reset from a declared baseline after each trial. Make reset idempotent. Expose enough initial and final state for the Verifier to judge the requested change and prohibited collateral changes.

Default to no production access. Allow only approved live hosts and pass credentials at runtime, never through images, prompts, fixtures, or logs.

## Validate

Before accepting the Environment, prove that:

- Harbor starts it and the Harness reaches required data/actions;
- the paths exercised by the task match the defined interface;
- mutable state resets;
- production writes are blocked;
- the Verifier can observe the intended result without trusting Harness claims.
