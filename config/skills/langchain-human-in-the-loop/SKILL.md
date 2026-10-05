---
name: langchain-human-in-the-loop
description: Add or modify pauses for human review, approval, editing, or rejection in an agent or workflow. Use when execution must stop before a consequential action and later resume from the same state; choose the review behavior before selecting its APIs.
---

# Human in the loop

Inspect where the action is proposed, which component owns execution at that
point, and how the application persists and resumes work. LangChain tool-review
middleware, Deep Agents approval configuration, and LangGraph interrupts can
participate in the same application. Choose among them from the kind of pause
the application needs.

A resumable review flow needs:

- a clearly defined interrupt point and review payload;
- durable state or a checkpointer appropriate to the deployment;
- a stable checkpoint or thread identity reused on resume;
- an application surface that presents the pending action and records a valid
  decision;
- authorization checks when a different process or user resumes execution.

Treat approve, edit, and reject as application decisions with explicit
semantics. Some Python tool-review APIs also support `respond` for tools that
ask a person for information. Do not invent decision payload fields from
memory; verify them for the installed package version.

Keep two kinds of multiplicity distinct: decisions for one batched tool-review
request correspond to its action list in order, while independent interrupts
from parallel graph branches are resumed by interrupt ID. Treat interrupt and
resume payloads as untrusted input. Recheck authorization and relevant state
immediately before an approved effect, then test both the pause and the resumed
path.

## References

- To review selected tool calls before they execute, read
  [Tool approvals](references/tool-approvals.md).
- To pause at an application-defined point in a graph, read
  [Explicit interrupts](references/explicit-interrupts.md).
- To connect a pending review to an authorized UI or API and resume it, read
  [Resume and review](references/resume-and-review.md).
- Before placing side effects around a pause or retry boundary, read
  [Side effects and idempotency](references/side-effects-and-idempotency.md).
