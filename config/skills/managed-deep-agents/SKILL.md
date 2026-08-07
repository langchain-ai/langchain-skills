---
name: managed-deep-agents
description: "INVOKE THIS SKILL when building, testing, or deploying Managed Deep Agents in LangSmith with the mda CLI. Covers the code-first, file-based project layout; define_deep_agent / defineDeepAgent; identity; opt-in memory; channels; connectors.mcp; cron schedules; skills; sandboxes; authored tools and middleware; mda init/build/dev/deploy/logs/delete/channel/evals; Context Hub; and human-in-the-loop interrupts in Python and TypeScript."
---

# Managed Deep Agents

## Overview

Managed Deep Agents is a hosted runtime for deploying and operating code-first Deep Agents in LangSmith. You author an agent in Python or TypeScript, then use the `mda` CLI to test it locally and deploy it to the managed runtime. It pairs the open-source Deep Agents harness (see [[deep-agents-core]]) with managed infrastructure: durable runs, LangSmith sandboxes, Context Hub-backed instructions, skills, memory, traces, and hosted LangGraph deployment.

The core idea is that **an agent is a directory**. A file's location determines its role, and the CLI compiles that directory into a managed LangGraph app. There is no API-driven create/update/invoke flow during private beta: you write code and run `mda deploy`.

## When to use

Use this skill when the user wants to:

- Build a Deep Agent in code (Python or TypeScript) and deploy it to LangSmith without standing up their own server.
- Add authored tools, middleware, identity, memory, Slack channels, remote MCP connectors, cron schedules, skills, or a sandbox to a managed agent.
- Test an agent locally with `mda dev` and deploy it with `mda deploy`.
- Understand what the managed runtime owns versus what the author configures.

Use a standard LangSmith Deployment (see [[langgraph-cli]], `langgraph deploy`) instead when the user needs custom application code, custom routes, advanced authentication, stronger isolation, maximum scalability, or a region other than US LangSmith Cloud.

## Prerequisites

- Managed Deep Agents private beta access in the target LangSmith workspace.
- A LangSmith API key for that workspace.
- Python and `uv` for Python projects, or Node.js 22+ and npm for TypeScript projects.
- A model provider API key (unless using LangSmith Gateway).

Install the `mda` CLI. Both packages ship the same CLI binary, but each installer is language-locked:

```bash
pip install --pre managed-deepagents        # Python projects only
npm install -g managed-deepagents@dev        # TypeScript projects only
```

Set the LangSmith API key in the project `.env` or the shell:

```bash
export LANGSMITH_API_KEY="<LANGSMITH_API_KEY>"
```

Authentication also resolves from a short-lived cached PAT or interactive browser login when no key is set. Managed Deep Agents is CLI-first during private beta and runs on US LangSmith Cloud only. Self-hosted and Hybrid are not supported.

## Project layout

The path passed to `mda dev` or `mda deploy` is the project root. A file's location determines its role:

```text
my-agent/
  agent.py | agent.ts | agent.tsx          # Required: exports the named `agent`
  identity.py | identity.ts                # Auth; always scaffolded by `mda init`
  memory.py | memory.ts                    # Optional: opt-in durable memory
  instructions.md                          # Managed system prompt, synced to Context Hub
  pyproject.toml | package.json            # Project dependencies
  .env                                     # Deploy auth + runtime secrets (never archived)
  tools/                                   # Authored LangChain tools the agent imports
  middleware/                              # Authored middleware the agent imports
  connectors/<name>.py | <name>.ts         # Integrations (e.g. connectors.mcp)
  channels/<name>.py | <name>.ts           # Messaging ingress (for example Slack)
  schedules/<name>.py | <name>.ts          # Managed cron schedules
  skills/<name>/SKILL.md                   # Deploy-owned skills, synced to Context Hub
  sandbox/__init__.py | sandbox/index.ts   # Managed sandbox configuration
  sandbox/setup.sh                         # Sandbox provisioning script (runs once)
  evals/                                   # Harbor evals (not copied into the managed build)
```

Only the agent entry is required to compile. It must export a named `agent` created with `define_deep_agent` / `defineDeepAgent`. The `tools/` and `middleware/` folders are conventions, not special registries: MDA copies project files verbatim, so any local module the agent imports works. The other files take on managed meanings when present.

Scaffold a project with `mda init <name>`:

```bash
mda init my-agent
mda init my-agent --memory agent --model openai:gpt-5.5
mda init my-agent --gateway --no-sandbox
mda init my-agent --instructions "You are a careful research assistant."
```

Useful init flags: `--instructions`, `--instructions-file` (`-` = stdin), `--memory agent|none`, `--model`, `--gateway` (xor `--model`), `--no-sandbox`. Every new project includes an identity file that selects `auth.langsmithApiKey()` / `auth.langsmith_api_key()`.

## Define the agent

The agent entry returns a pre-runtime spec, not a compiled graph. The managed runtime injects the backend, store, checkpointer, memory mounts, skills, and system prompt at deploy time, so do not set those.

```python
# agent.py
from managed_deepagents import define_deep_agent

from tools.query_db import query_db

agent = define_deep_agent(
    name="research-assistant",
    model="openai:gpt-5.5",
    tools=[query_db],
)
```

```ts
// agent.ts
import { defineDeepAgent } from "managed-deepagents";

import { queryDB } from "./tools/query-db";

export const agent = defineDeepAgent({
  name: "research-assistant",
  model: "openai:gpt-5.5",
  tools: [queryDB],
});
```

**Required:** `name` — a static string matching `[A-Za-z][A-Za-z0-9_-]*`. MDA uses it as the LangGraph assistant id and the default LangSmith deployment name.

**Author-set fields:** `model`, `tools`, `middleware`, `subagents`, `permissions`, `interrupt_on` / `interruptOn`, `response_format` / `responseFormat`, `context_schema` / `contextSchema`, `cache`, `debug`, `metadata`.

**Managed fields (do not set):** `backend`, `store`, `checkpointer`, `memory`, `skills`, `system_prompt` / `systemPrompt`. Configure the system prompt in `instructions.md`, memory in root `memory.*`, MCP servers in `connectors/**`, schedules in `schedules/**`, skills in `skills/**`, channels in `channels/**`, and the sandbox under `sandbox/`.

**Removed:** `disable_memory` / `disableMemory`. Durable memory is opt-in via root `memory.py` / `memory.ts` (see Memory below). Passing the old flag raises an error.

Model identifiers use the `{provider}:{model_id}` form, for example `openai:gpt-5.5`. The runtime resolves them with `init_chat_model`, so any `init_chat_model` provider works. `mda init --gateway` uses [LangSmith Gateway](https://docs.langchain.com/langsmith/gateway) instead of a provider key you hold.

## Identity

Declare authentication in root `identity.py` / `identity.ts` with a named `identity` export. Threads are always per-caller. Durable memory is **not** an identity concern — it has its own root declaration.

```python
# identity.py
from managed_deepagents import auth, define_identity

identity = define_identity(auth=auth.langsmith_api_key())
```

```ts
// identity.ts
import { auth, defineIdentity } from "managed-deepagents";

export const identity = defineIdentity({
  auth: auth.langsmithApiKey(),
});
```

Clients send a LangSmith workspace key as `x-api-key`. Also supported:

- `auth.supabase({ project_ref | url, ... })` / `auth.supabase({ projectRef | url, ... })` — validate caller JWTs.
- `auth="backend"` / `auth: "backend"` — a backend you operate asserts the caller over reserved ingress headers (deploy needs `MDA_INGRESS_SECRET`).

`mda init` always scaffolds LangSmith API-key auth. Identity is required when channels (or other ingress) are present.

**Do not set** removed options on `defineIdentity` / `define_identity`: `scope`, `connect`, or `credentials`. Connect-with-X is not available in this release.

Tools that need the caller can type the runtime as `ManagedDeepAgentRuntime` and read `runtime.identity` (and `runtime.channel` on channel-driven runs).

## Memory

Durable memory is opt-in and declared once in root `memory.py` / `memory.ts`. A project without that file mounts nothing.

```python
# memory.py
from managed_deepagents import define_memory

memory = define_memory(scope="agent")
```

```ts
// memory.ts
import { defineMemory } from "managed-deepagents";

export const memory = defineMemory({ scope: "agent" });
```

| Scope                | Effect                                                                  |
| -------------------- | ----------------------------------------------------------------------- |
| omit file / `"none"` | No durable memory (default)                                             |
| `"agent"`            | Mount R/W `/memories/agent/`; hot memory is `/memories/agent/AGENTS.md` |

Deploy seeds an empty hot file only when memory is enabled and the file is absent, and **never overwrites** existing memories. Memory is independent of identity.

The shared agent slice is a trust boundary: ordinary runs can write hot memory, and that content is injected into every later run. Prefer `"none"` when callers are mutually untrusted. Treat memory as data rather than orders, and never let memory grant authority a tool permission would otherwise gate. Never print memory contents in CLI output, logs, or summaries.

## Instructions

Put the system prompt in `instructions.md` next to the agent entry:

```markdown
# Research assistant

You are a careful research assistant. Find sources, keep notes, and return
concise answers with citations.
```

`mda deploy` syncs it to Context Hub, and the deployed runtime reads it from there. `mda dev` uses the local Context Hub mock under `.mda/__contexthub__/`.

## Authored tools

Define tools in the project and import them into the agent entry. The runtime keeps authored tools in the bounded agent execution surface.

```python
# tools/query_db.py
from langchain.tools import tool


@tool(parse_docstring=True)
def query_db(query: str) -> str:
    """Run a read-only SQL query against the application database.

    Args:
        query: A read-only SQL query to execute.
    """
    return f"Ran query: {query}"
```

```ts
// tools/query-db.ts
import { tool } from "langchain";
import { z } from "zod";

export const queryDB = tool(
  async ({ query }) => `Ran query: ${query}`,
  {
    name: "query_db",
    description: "Run a read-only SQL query against the application database.",
    schema: z.object({ query: z.string().describe("A read-only SQL query.") }),
  },
);
```

Tools read deployment secrets from environment variables. Put local values in `.env`; deploy forwards non-reserved `.env` values as hosted secrets.

## Middleware

Middleware wraps model and tool calls for cross-cutting behavior (logging, PII redaction, retries, limits). Order is explicit in the `middleware` list; MDA never infers it. Pass prebuilt LangChain middleware or author your own (see [[langchain-middleware]]).

```python
# agent.py
from langchain.agents.middleware import ModelCallLimitMiddleware, PIIMiddleware
from managed_deepagents import define_deep_agent

agent = define_deep_agent(
    name="research-assistant",
    model="openai:gpt-5.5",
    middleware=[
        PIIMiddleware("email", strategy="redact"),
        ModelCallLimitMiddleware(run_limit=50),
    ],
)
```

```ts
// agent.ts
import { defineDeepAgent } from "managed-deepagents";
import { modelCallLimitMiddleware, piiMiddleware } from "langchain";

export const agent = defineDeepAgent({
  name: "research-assistant",
  model: "openai:gpt-5.5",
  middleware: [
    piiMiddleware("email", { strategy: "redact" }),
    modelCallLimitMiddleware({ runLimit: 50 }),
  ],
});
```

## Channels

Declare messaging ingress under `channels/`, one named `channel` export per file. Slack is the supported provider. Bring your own Slack app — MDA does not provision it.

```python
# channels/slack.py
from managed_deepagents import channels

channel = channels.slack()
```

```ts
// channels/slack.ts
import { channels } from "managed-deepagents";

export const channel = channels.slack();
```

The file stem becomes the channel name and mounts `POST /channels/{name}/events` on the Agent Server. Required env: `SLACK_SIGNING_SECRET`, `SLACK_BOT_TOKEN`. Channels require a root identity declaration. After deploy, generate a Slack app manifest with `mda channel add slack`.

Do not pass a removed `on` option — subscribe to bot events under Event Subscriptions on your Slack app. Slack *tool-server* tools (`connectors.slack`) are not part of this release — use Events ingress via `channels.slack` for messaging.

## MCP connectors

Declare remote MCP servers under `connectors/`, one named `connector` export per file. The supported public connector is `connectors.mcp(...)`. MDA loads their tools at runtime and appends them to authored tools, prefixing tool names with the server name by default (for example `docs__search`).

```python
# connectors/mcp.py
from managed_deepagents import connectors

connector = connectors.mcp(
    mcp_servers={
        "langchainDocs": {
            "transport": "http",
            "url": "https://docs.langchain.com/mcp",
        },
    },
)
```

```ts
// connectors/mcp.ts
import { connectors } from "managed-deepagents";

export const connector = connectors.mcp({
  mcpServers: {
    langchainDocs: {
      transport: "http",
      url: "https://docs.langchain.com/mcp",
    },
  },
});
```

Only remote `http` and `sse` transports are supported. Stdio servers are rejected. Configuration is validated eagerly at build or dev startup. Optional per-server `include_tools` / `includeTools` or `exclude_tools` / `excludeTools` select a subset by raw MCP tool name (before the managed `{server}__` prefix). Store any OAuth or header tokens in `.env` and reference them from the connector (`headers` on a server config).

Do not use the removed `defineMcpServers` / `define_mcp_servers` helpers or a named `mcp` export — the module must export `connector`.

## Schedules

Declare managed cron schedules under `schedules/`, one named `schedule` export per file. Deploy reconciles them into LangSmith cron jobs after the deployment is live.

```python
# schedules/daily_digest.py
from managed_deepagents import define_schedule

schedule = define_schedule(
    cron="0 8 * * 1-5",
    timezone="America/Los_Angeles",
    prompt="Summarize what you learned yesterday and list open questions.",
)
```

```ts
// schedules/daily-digest.ts
import { defineSchedule } from "managed-deepagents";

export const schedule = defineSchedule({
  cron: "0 8 * * 1-5",
  timezone: "America/Los_Angeles",
  prompt: "Summarize what you learned yesterday and list open questions.",
});
```

Provide either `prompt` or a structured `input`, not both. Set `thread.mode` to `ephemeral` (cleaned up after the run) or `persistent` (reuses a stable `thread.id` so state accumulates). Optional `deliver_to` / `deliverTo` can target a Slack conversation for delivery. Schedule declarations must be static literals, not values computed from env vars or function calls.

## Sandboxes

Configure a sandbox when the agent needs isolated code execution or filesystem work. Export `sandbox` from `sandbox/index.ts` or `sandbox/__init__.py`. `mda init` includes a sandbox by default; delete `sandbox/` or pass `--no-sandbox` to opt out.

```python
# sandbox/__init__.py
from managed_deepagents import define_sandbox

sandbox = define_sandbox(
    scope="thread",
    idle_ttl_seconds=600,
    default_timeout=600,
)
```

```ts
// sandbox/index.ts
import { defineSandbox } from "managed-deepagents";

export const sandbox = defineSandbox({
  scope: "thread",
  idleTtlSeconds: 600,
  defaultTimeout: 600,
});
```

`scope` is `thread` (one sandbox per conversation) or `agent`. Do **not** pass a backend class such as `LangSmithSandbox` — MDA owns provider construction, naming, image/snapshot selection, and lifecycle. If `sandbox/setup.sh` exists, MDA runs it once when a new sandbox is provisioned. When a sandbox is present, authored path `permissions` are cleared so shell execution is not disabled.

## Skills

Put deploy-owned skills under `skills/<name>/SKILL.md`. Deploy syncs `skills/**` to Context Hub and deletes deployed skills that no longer exist locally. Each skill is a markdown file with `name` and `description` frontmatter that the agent loads on demand.

## CLI commands

| Command                    | Use                                                                                                                                                      |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mda init <name>`          | Scaffold a Python or TypeScript project. Flags: `--instructions`, `--instructions-file`, `--memory agent\|none`, `--model`, `--gateway`, `--no-sandbox`. |
| `mda build [path]`         | Compile into `.mda/build` without deploying. Flag: `--out`.                                                                                              |
| `mda dev [path]`           | Compile and run the local LangGraph dev server in LangSmith Studio. Flags: `--port`, `--hostname`, `--no-browser`, `--no-reload`.                        |
| `mda deploy [path]`        | Compile, sync Context Hub, upload, and deploy. Flags: `--name`, `--deployment-type dev\|prod`, `--workspace-id`, `--no-wait`.                            |
| `mda logs [path]`          | Tail Agent Server logs. Flags: `--lines`, `--level`, `--follow` / `--no-follow`, `--workspace-id`.                                                       |
| `mda channel add slack`    | Generate a Slack app manifest for a deployed agent.                                                                                                      |
| `mda delete` / `destroy`   | Tear down the deployment, tracing project, Context Hub (including memories), and managed sandboxes. Flag: `--yes`.                                       |
| `mda evals init <task>`    | Scaffold a Harbor task under `evals/scaffold/`.                                                                                                          |
| `mda evals compile [path]` | Package a Harbor-ready artifact. Flags: `--model` (repeatable), `--task` (repeatable).                                                                   |

For Python projects, run `uv sync` inside the generated project before `mda dev`. Authentication resolves from `.env` first, then the shell, then a cached PAT or interactive browser login.

## Deploy and Context Hub

`mda deploy` compiles the project into `.mda/build` (copying your code verbatim, generating a managed LangGraph entry, excluding `node_modules`, `.git`, `.mda`, `evals`, `memories`, `dist`, `build`, and `.env*`), then:

1. Resolves the LangSmith key and verifies the model provider key or Gateway credentials are available.
2. Forwards non-reserved `.env` values (provider keys, Slack tokens, database URLs) as hosted deployment secrets. The `.env` file is never uploaded.
3. Syncs `instructions.md` and `skills/**` to the deployment's Context Hub repo. When memory is enabled, seeds empty `/memories/agent/AGENTS.md` only if absent; never overwrites existing memories.
4. Uploads the build, triggers a hosted build, and waits until the revision is `DEPLOYED` (unless `--no-wait`).
5. Reconciles managed cron jobs from `schedules/**`.

Context Hub stores `/instructions.md` and `/skills/**` (deploy-owned). When memory is enabled, runtime-owned durable content lives under `/memories/agent/` (hot file `/memories/agent/AGENTS.md`).

Inspect build status, revisions, and traces on the deployment page in LangSmith.

## Human-in-the-loop

Pause before sensitive tool calls with `interrupt_on` / `interruptOn` (and gate access with `permissions`). See [[langgraph-human-in-the-loop]] for interrupt and resume semantics.

```python
agent = define_deep_agent(
    name="research-assistant",
    model="openai:gpt-5.5",
    tools=[query_db],
    interrupt_on={"query_db": True},
)
```

```ts
export const agent = defineDeepAgent({
  name: "research-assistant",
  model: "openai:gpt-5.5",
  tools: [queryDB],
  interruptOn: { query_db: true },
});
```

When a run hits an interrupt, it pauses. During `mda dev`, respond to it in LangSmith Studio. On a deployed agent, resume through the LangGraph server API with a `Command(resume=...)` payload. During private beta, programmatic invocation from your own application is contact-your-team.

## Gotchas

- **Use the `mda` CLI**, not the older `deepagents` CLI or the removed `Client` SDK / `/v1/deepagents` REST surface. During private beta there is no public create/update/invoke API.
- **`name` is required** on `defineDeepAgent` / `define_deep_agent`.
- **Do not set managed fields** (`backend`, `store`, `checkpointer`, `memory`, `skills`, system prompt) in the agent definition; the runtime owns them.
- **Memory is opt-in** via root `memory.*`.
- **Model IDs need the provider prefix**: `openai:gpt-5.5`, not a bare model name.
- **Sandbox takes options only** — no `LangSmithSandbox` constructor argument.
- **MCP connectors support `http` and `sse` only**; stdio is rejected, and misconfiguration surfaces at build or dev startup. Export `connector` from `connectors/*`, not a named `mcp`.
- **npm CLI vs PyPI CLI** are language-locked; the installed CLI language must match the project, and the bundled runtime version must match the project package.
- **`.env` is never archived**; deploy forwards non-reserved values as hosted secrets. Do not commit real secrets.
- **Schedule, memory, identity, and agent `name` declarations must be static literals**; the compiler extracts them without running your code.
- **`mda delete` is destructive** and not recoverable (deployment, Hub, memories, sandboxes).
- **Private beta scope**: US LangSmith Cloud only, CLI-first. Self-hosted and Hybrid are not supported.
