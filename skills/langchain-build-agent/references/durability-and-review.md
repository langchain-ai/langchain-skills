# Durability and review

Decide the lifetime and owner of each piece of state before selecting APIs:

- Conversation state supports continuity and resumption within one thread.
- Cross-conversation memory retains selected facts outside an individual thread.
- Working files may be transient or persistent depending on their backend.
- Standing instructions and on-demand skills are not substitutes for storage.

Consult the current framework's persistence, storage, backend, and human-review
guides for the language and installed release. A checkpointer and a memory store
have different scopes; neither an in-memory example nor a stable conversation ID
alone establishes survival across process restart.

Use trusted runtime identity to select user or tenant storage scopes. Define
which component owns durable state, how it is recovered, and how related
threads or delegated workers find it. Keep transient request dependencies out
of serialized state. When routing files among backends, verify actual paths
reach storage with the intended lifetime and isolation.

For human review, identify the proposed action, the point before its external
effect, the review payload, and the state needed to continue. Use the harness's
supported tool-review capability when reviewing tool calls; use lower-level
workflow interruption for other application-defined pauses. Retrieve the exact
configuration and resume contract rather than inventing a decision payload.

Review requires a caller-facing path to present the proposal and submit a
decision. Resume the intended interrupted execution. An edited action must use
the reviewed parameters; a rejected action must not execute. Handle batched
tool decisions and independent parallel interruptions according to their distinct
runtime contracts.

Interrupts and retries can replay work. Keep effects after review where possible,
and define idempotency at external service boundaries. Recheck authorization and
relevant state after a long pause. Do not equate an agent's final message with
evidence that the effect happened or was prevented.

Verify the required storage lifetime, isolation, pause, and resume behavior by
observing real storage and tool effects. Include restart only when restart
survival is part of the requested feature, and test rejection/editing when those
decisions are exposed by the application.
