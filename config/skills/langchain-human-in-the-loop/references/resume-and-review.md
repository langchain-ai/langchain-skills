# Resume and review

A pause becomes a usable human-review flow only when the application can show
the pending action, collect a valid decision, and resume the exact execution
that produced it.

Build the review path around these invariants:

- Compile the graph or agent with a checkpointer. Use durable storage when a
  pause must survive restart or worker failover.
- Assign a stable thread identity and retain the pending checkpoint or
  interrupt identity. Reuse the correct configuration on resume.
- Authorize access to the thread, checkpoint, history, interrupt payload, and
  every resume request. A caller-supplied thread ID is not proof of ownership.
- Show the actual returned interrupt payload rather than reconstructing the
  proposed action from other application state.
- Limit payload visibility to authorized reviewers. Avoid logging credentials,
  tokens, or sensitive tool arguments merely because they appear in an
  interrupt; redact display and logs without changing the reviewed action.
- Define explicit schemas and semantics for approve, edit, reject, and any
  application-specific decisions. Validate all resume data as untrusted input.
- Persist only values supported by the checkpointer's serializer. Do not place
  functions, open connections, credentials, or arbitrary runtime objects in
  interrupt or resume payloads.

Resume LangChain agents, Deep Agents, and LangGraph workflows with the current
release's `Command` API. A typical call reuses the same configuration:

```python
from langgraph.types import Command

result = runnable.invoke(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config,
)
```

```typescript
import { Command } from "@langchain/langgraph";

const result = await runnable.invoke(
  new Command({ resume: { decisions: [{ type: "approve" }] } }),
  config,
);
```

The tool-approval and explicit-interrupt shapes differ, and edit and rejection
fields can change between versions. Inspect the pending interrupt and verify
the installed package's schema instead of copying one resume payload into a
different review flow.

For a single tool-review interrupt containing several `action_requests`, send
one decision for each request in the same order. For independent interrupts
raised by parallel branches, send the release's interrupt-ID-to-resume-value
mapping. Do not use the tool batch's ordered decision list to resume unrelated
parallel interrupts.

Match the review UI to the execution API. Default invoke calls commonly expose
`__interrupt__`; newer typed graph output and event streaming expose interrupt
collections and an interrupted flag. For streaming UIs, finish consuming the
current run, collect decisions, then begin a new invocation or stream with
`Command(resume=...)` and the same thread configuration. Repeat until the run
finishes without another interrupt.

Treat resume as a new authorized operation. Confirm that the interrupt is still
pending, the reviewer is still permitted, the reviewed arguments still match,
and any relevant resource version has not changed. Make duplicate submissions
idempotent and reject decisions for completed, superseded, or different
checkpoints.

Test the complete UI or API round trip: pause, display, authorized resume,
approve, edit, reject, process restart where required, repeated requests, stale
decisions, parallel interrupts, sensitive payload handling, and unauthorized
access.
