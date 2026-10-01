---
name: human-in-the-loop
description: Add or modify pauses for human review, approval, editing, or rejection in an agent or workflow. Use when execution must stop before a consequential action and later resume from the same state; inspect the application's framework and persistence setup first.
---

# Human in the loop

Inspect where the action is proposed, which framework owns execution at that
point, and how the application persists and resumes work. A LangChain agent can
run inside LangGraph, and a Deep Agent is built from LangChain and LangGraph
components, so route by the code path rather than the product name in the
prompt.

A resumable review flow needs:

- a clearly defined interrupt point and review payload;
- durable state or a checkpointer appropriate to the deployment;
- a stable checkpoint or thread identity reused on resume;
- an application surface that presents the pending action and records a valid
  decision;
- authorization checks when a different process or user resumes execution.

Treat approve, edit, and reject as application decisions with explicit
semantics. Do not invent decision payload fields from memory; verify them for
the installed framework version. Test both the pause and the resumed path.

## References

- For LangChain agent tool approvals, read
  [LangChain](references/langchain.md).
- For LangGraph interrupts, read
  [LangGraph](references/langgraph.md).
- For Deep Agents tool approvals, read
  [Deep Agents](references/deep-agents.md).
