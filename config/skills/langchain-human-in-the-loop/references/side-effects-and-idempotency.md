# Side effects and idempotency

Interrupts and retries create re-execution boundaries. When a LangGraph node
resumes after `interrupt`, the node starts again from the beginning, so code
before the interrupt runs again. A parent node can also re-execute when a
subgraph it invokes interrupts.

Do not catch `interrupt()` with a broad exception handler; the pause uses a
framework control-flow exception. Multiple interrupts inside one node must also
be encountered in the same order on every execution. If the number or order of
reviews is dynamic, split them into separate nodes and route with conditional
edges.

Put the pause before the external effect whenever possible:

1. Compute and persist a reviewable proposal.
2. Interrupt and collect the decision.
3. Validate the resumed decision.
4. Perform the approved effect with an idempotency key.
5. Record the result so a retry can return it rather than repeat the effect.

When an effect must occur before a pause, isolate it in a completed node or make
it idempotent. Use stable operation identifiers for payments, messages,
database mutations, and other external calls. Do not rely on an in-memory flag
to prevent duplication across process restart.

Approval authorizes the reviewed action and parameters. If an edit changes the
action, validate and authorize the edited form. If state has changed since the
proposal was created, reject the stale decision or produce a new proposal
instead of silently applying it. Recheck the reviewer, target resource, and
current authorization immediately before the external effect; authorization at
proposal time may no longer be valid after a long pause.

Test resume, retry, timeout after the external system succeeds, duplicate
review submissions, stale review submissions, and nested-graph interruption.
