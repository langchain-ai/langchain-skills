# Environment Building

Build only the environment required by the approved scenario.

## Choose the target runtime

Recommend the active repository entrypoint when it can run safely. If it cannot run in a controlled eval, offer a reconstruction, name its unsupported behavior, and let the user choose. Never describe a reconstruction as production behavior.

## Choose each dependency

| Option | Use when |
|---|---|
| Live | Read-only, low-cost, stable, safely credentialed, and difficult to reproduce. |
| Frozen | Data or retrieval results must stay stable across trials. Serve them through the relevant interface. |
| Simulated | Writes, permissions, failures, or state must be isolated and resettable. |

For each backing source, state whether it is live, frozen, or synthetic; retain its source/version, commit, timestamp, or hash; and name the behavior it must reproduce. Mark constructed data as synthetic.

Keep target behavior on the target side: prompts, control flow, model decisions, memory, tool choice, retries, parsing, and final synthesis. Replace dependencies through their existing interface; do not move a target decision into an adapter or simulator.

## Define and build the gap

Name only what the scenario needs: startup dependencies, backing data or policy, tool/service behavior, state/identity/time, reset, or observable outcomes. Use the smallest available injection point: fixture, dependency override, temporary workspace, test database, local endpoint, or existing integration harness.

For every replaced dependency, define:

```text
binding: in-process | network | MCP | CLI | filesystem/browser
inputs/outputs: schema, ordering, pagination, empty results
failures: missing, malformed, unauthorized, timeout
effects: reads, writes, idempotency, collateral state
context: identity, permissions, time, feature flags
```

For retrieval, include relevant records, distractors, misses, and bad IDs. For mutations, enforce validation and permissions and expose resulting state. Do not key results on task IDs, expected answers, or exact phrases.

## Validate

Prove that Harbor starts the approved runtime; the target can use the required information and actions; relevant success and error paths work through the dependency interface; state resets; production access is blocked; and the verifier can observe the intended result.

Keep credentials out of files, images, prompts, fixtures, and logs.
