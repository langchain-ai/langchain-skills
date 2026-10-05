# Built-in middleware

Prefer a maintained built-in component when it already owns the required
agent-loop behavior. LangChain middleware can provide capabilities such as
dynamic prompts, tool selection, summarization, limits, retries, fallbacks,
human review, and sensitive-data handling. Available components and constructor
options vary across Python, TypeScript, and package versions, so verify the
installed release before selecting one.

Deep Agents is an opinionated agent harness assembled from LangChain middleware
and prompts. Current releases include filesystem tools, summarization,
synchronous subagents, and prompt caching. Todo planning remains opt-in. Inspect
the installed harness before adding a component that could duplicate or
conflict with its core stack.

Choose middleware from the behavior needed, not from the framework named in a
user prompt. In one application, the same LangChain middleware may wrap a base
agent or extend a Deep Agent, and either agent may run inside a LangGraph node.

Before adding a built-in component:

- identify the exact event or condition that should trigger it;
- verify required tools, state fields, runtime context, and package versions;
- check whether the current harness already implements the behavior;
- understand how it composes with surrounding middleware;
- test an invocation that triggers it and one that should bypass it.

## Selection guide

Start with the maintained component that owns the behavior:

| Need | Prefer |
| --- | --- |
| Retry transient model or tool failures | Model or tool retry middleware |
| Fail over between models | Model fallback middleware |
| Cap model, tool, or agent activity | Call-limit middleware |
| Compress long histories | Summarization middleware |
| Remove stale tool results from context | Context-editing middleware |
| Detect, redact, block, or review sensitive data | PII middleware |
| Limit the tools sent to the model | LLM tool-selection middleware |
| Give an agent file or shell capabilities | Filesystem, file-search, or shell middleware |
| Delegate bounded work | Subagent middleware |

Retry middleware can repeat an operation. Use it only where the operation is
read-only or idempotent, or where the underlying service accepts an
idempotency key. Put an explicit cap on retries.

Use the shared `langchain-human-in-the-loop` skill for tool-review middleware and resume
semantics. Use explicit LangGraph nodes and edges for application workflow or
deterministic control flow.

Tool selection changes what the model sees. It does not authorize an operation;
enforce access control inside the tool or downstream service.
