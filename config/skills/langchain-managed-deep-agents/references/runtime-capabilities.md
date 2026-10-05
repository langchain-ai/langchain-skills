# Managed Deep Agents runtime capabilities

## Memory

Durable memory is opt-in and has independent deployment-shared and user layers.
Current Python releases declare them with `MemoryLayer`:

```python
from managed_deepagents import MemoryLayer, define_memory

memory = define_memory(
    agent=MemoryLayer(),
    user=MemoryLayer(),
)
```

```typescript
import { defineMemory, memoryLayer } from "managed-deepagents";

export const memory = defineMemory({
  agent: memoryLayer(),
  user: memoryLayer(),
});
```

The agent layer mounts at `/memories/agent/`; the authenticated user's layer
mounts at `/memories/user/`. `AGENTS.md` at either root is hot memory loaded on
every run; other files are cold memory read on demand. Omit a layer to disable
it, or delete the memory declaration to disable durable memory entirely.

Agent memory is shared by all callers. Never store personal or customer data,
credentials, API keys, or tokens there. User memory requires a caller whom the
deployment authenticates as a person; a LangSmith service API key does not
establish an end-user identity. Treat both layers as untrusted notes, never as
authority or policy. State the memory policy in `instructions.md` and use layer
`allow` policies when the default run-source behavior is too broad or narrow.

## Identity

The scaffolded LangSmith-key identity controls whether a workspace caller may
reach the deployment. It authenticates a service, not an individual person, so
it does not provide private end-user threads or user memory. For end-user
ownership, use a supported identity provider such as Supabase and send the
end-user bearer token. Test migration before relying on identity for threads
created before ownership metadata existed.

Authentication failures should remain distinct from cross-user authorization
failures. Authorize thread reads, writes, interrupts, and resumes by owner.

## Tools

Define ordinary LangChain tools in project modules and pass them to the agent.
Give each tool a unique name, precise description, and validated schema. Read
deployment secrets from environment variables. Use runtime context for per-run
values rather than global state.

Provider-hosted tools may be passed in the format supported by the selected
model. Verify that they do not require an undeclared credential or broaden the
agent's authority.

## MCP connectors

Declare every managed MCP server in `tools/mcp.py` or `tools/mcp.ts` and export
one module-level `mcp` created with `define_mcp` or `defineMcp`. Current managed
support includes Streamable HTTP and legacy SSE; stdio is not supported.

Prefer managed connections for authentication, especially user-owned OAuth
when each caller should authorize their own account. Never hard-code tokens.
Prefer an allowlist of tool names. Server-name prefixing changes the exposed
tool name; approval rules must use the actual exposed name or they will not
match.

Validate connector URLs against the application's approved services. A static
deployment token cannot substitute for a server that requires per-user OAuth,
and a connection cannot expand the identity's authorized scope.

## Middleware

Managed agents accept LangChain middleware in explicit list order:

```python
import os

from langchain.agents.middleware import ModelCallLimitMiddleware, PIIMiddleware
from managed_deepagents import define_deep_agent

agent = define_deep_agent(
    name="support-agent",
    model=os.environ["MODEL"],
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        ModelCallLimitMiddleware(run_limit=50),
    ],
)
```

Use the shared `langchain-middleware` skill for hook behavior and ordering decisions.

## Sandboxes

```python
from managed_deepagents import define_sandbox

sandbox = define_sandbox(
    scope="thread",
    idle_ttl_seconds=600,
    default_timeout=600,
)
```

Thread scope isolates files between durable threads. Agent scope shares one
filesystem across threads and should be used only for deliberately shared state.
Choose either a template or snapshot source when supported, never both. Delete
the sandbox directory when the agent needs only prompts and tools.

Local fallback sandboxes are development behavior. Verify isolation and command
execution in a managed development deployment before production.

## Schedules

Each file under `schedules/` declares one schedule. Define exactly one of a user
prompt or structured graph input. Use a five-field cron and an explicit timezone
unless UTC is intentional.

Schedules use fresh ephemeral threads by default. Use a fixed persistent thread
only when runs should intentionally accumulate state. Declarations must be
static literals because the compiler extracts them without executing code.

Deployment reconciles MDA-owned schedules after the deployment is live. Do not
use `--no-wait` when adding, changing, or removing schedules because it skips
that reconciliation.

## Channels

Current channel support must be verified against the installed release. For
Slack, keep the signing secret and bot token in `.env`, keep generated `.mda/`
artifacts out of version control, and validate inbound signatures. Channel
runtime context must not expose the bot token.

A channel receives events that start runs. It is separate from giving the agent
tools that can initiate operations in the messaging service.

## Human approval

Configure `interrupt_on`/`interruptOn` for tools that require approval. The
managed runtime owns durable thread state, but the application must still show
the pending action, authorize the reviewer, and resume the correct thread.
Consult the shared `langchain-human-in-the-loop` skill for decision semantics.
