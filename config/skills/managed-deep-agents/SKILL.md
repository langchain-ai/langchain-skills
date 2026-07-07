---
name: managed-deep-agents
description: "INVOKE THIS SKILL when building, testing, or deploying Managed Deep Agents in LangSmith with the mda CLI. Covers the code-first, file-based project layout; define_deep_agent / defineDeepAgent; authored tools and middleware; MCP connectors; cron schedules; skills; sandboxes; mda init/dev/deploy; Context Hub; and human-in-the-loop interrupts in Python and TypeScript."
---

# Managed Deep Agents

## Overview

Managed Deep Agents is a hosted runtime for deploying and operating code-first Deep Agents in LangSmith. You author an agent in Python or TypeScript, then use the `mda` CLI to test it locally and deploy it to the managed runtime. It pairs the open-source Deep Agents harness (see [[deep-agents-core]]) with managed infrastructure: durable runs, LangSmith sandboxes, Context Hub-backed instructions, skills, memory, traces, and hosted LangGraph deployment.

The core idea is that **an agent is a directory**. A file's location determines its role, and the CLI compiles that directory into a managed LangGraph app. There is no API-driven create/update/invoke flow during private beta: you write code and run `mda deploy`.

## When to use

Use this skill when the user wants to:

- Build a Deep Agent in code (Python or TypeScript) and deploy it to LangSmith without standing up their own server.
- Add authored tools, middleware, MCP connectors, cron schedules, skills, or a sandbox to a managed agent.
- Test an agent locally with `mda dev` and deploy it with `mda deploy`.
- Understand what the managed runtime owns versus what the author configures.

Use a standard LangSmith Deployment (see [[langgraph-cli]], `langgraph deploy`) instead when the user needs custom application code, custom routes, advanced authentication, stronger isolation, maximum scalability, or a region other than US LangSmith Cloud.

## Prerequisites

- Managed Deep Agents private beta access in the target LangSmith workspace.
- A LangSmith API key for that workspace.
- Python and `uv` for Python projects, or Node.js and npm for TypeScript projects.
- A model provider API key.

Install the `mda` CLI. Both packages ship the same CLI:

```bash
pip install --pre managed-deepagents        # Python
npm install -g managed-deepagents@dev        # TypeScript
```

Set the LangSmith API key in the project `.env` or the shell:

```bash
export LANGSMITH_API_KEY="<LANGSMITH_API_KEY>"
```

Managed Deep Agents is CLI-first during private beta and runs on US LangSmith Cloud only. Self-hosted and Hybrid are not supported.

## Project layout

The path passed to `mda dev` or `mda deploy` is the project root. A file's location determines its role:

```text
my-agent/
  agent.py | agent.ts | agent.tsx          # Required: exports the named `agent`
  instructions.md                          # Managed system prompt, synced to Context Hub
  pyproject.toml | package.json            # Project dependencies
  .env                                     # Deploy auth + runtime secrets (never archived)
  tools/                                   # Authored LangChain tools the agent imports
  middleware/                              # Authored middleware the agent imports
  connectors/mcp.py | connectors/mcp.ts    # Remote MCP server declarations
  schedules/<name>.py | <name>.ts          # Managed cron schedules
  skills/<name>/SKILL.md                   # Deploy-owned skills, synced to Context Hub
  sandbox/__init__.py | sandbox/index.ts   # Managed sandbox configuration
  sandbox/setup.sh                         # Sandbox provisioning script (runs once)
```

Only the agent entry is required. It must export a named `agent` created with `define_deep_agent` / `defineDeepAgent`. The `tools/` and `middleware/` folders are conventions, not special registries: MDA copies project files verbatim, so any local module the agent imports works. The other files take on managed meanings when present.

Scaffold a project with `mda init <name>`; the CLI detects the language from `pyproject.toml` or `package.json`, or prompts.

## Define the agent

The agent entry returns a pre-runtime spec, not a compiled graph. The managed runtime injects the backend, store, checkpointer, memory, skills, and system prompt at deploy time, so do not set those.

```python
# agent.py
from managed_deepagents import define_deep_agent

from tools.query_db import query_db

agent = define_deep_agent(
    model="openai:gpt-5.5",
    tools=[query_db],
)
```

```ts
// agent.ts
import { defineDeepAgent } from "managed-deepagents";

import { queryDB } from "./tools/query-db";

export const agent = defineDeepAgent({
  model: "openai:gpt-5.5",
  tools: [queryDB],
});
```

**Author-set fields:** `model`, `tools`, `middleware`, `subagents`, `permissions`, `interrupt_on` / `interruptOn`, `response_format` / `responseFormat`, `context_schema` / `contextSchema`, `name`, `cache`, `debug`, `disable_memory` / `disableMemory`.

**Managed fields (do not set):** `backend`, `store`, `checkpointer`, `memory`, `skills`, `system_prompt` / `systemPrompt`. Configure the system prompt in `instructions.md`, connectors in `connectors/mcp.*`, schedules in `schedules/**`, skills in `skills/**`, and the sandbox under `sandbox/`.

Model identifiers use the `{provider}:{model_id}` form, for example `openai:gpt-5.5`. The runtime resolves them with `init_chat_model`, so any `init_chat_model` provider works.

## Instructions

Put the system prompt in `instructions.md` next to the agent entry:

```markdown
# Research assistant

You are a careful research assistant. Find sources, keep notes, and return
concise answers with citations.
```

`mda dev` embeds it into the generated local entry. `mda deploy` syncs it to Context Hub, and the deployed runtime reads it from there.

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
  model: "openai:gpt-5.5",
  middleware: [
    piiMiddleware("email", { strategy: "redact" }),
    modelCallLimitMiddleware({ runLimit: 50 }),
  ],
});
```

## MCP connectors

Declare remote MCP servers in `connectors/mcp.py` or `connectors/mcp.ts` with a named `mcp` export. MDA loads their tools at runtime and appends them to authored tools, prefixing tool names with the server name by default.

```python
# connectors/mcp.py
from managed_deepagents.connectors import define_mcp_servers

mcp = define_mcp_servers(
    mcp_servers={
        "langchainDocs": {"transport": "http", "url": "https://docs.langchain.com/mcp"},
    },
)
```

```ts
// connectors/mcp.ts
import { defineMcpServers } from "managed-deepagents";

export const mcp = defineMcpServers({
  mcpServers: {
    langchainDocs: { transport: "http", url: "https://docs.langchain.com/mcp" },
  },
});
```

Only remote `http` and `sse` transports are supported. Stdio servers are rejected. Configuration is validated eagerly at build or dev startup. Store any OAuth or header tokens in `.env` and reference them from the connector.

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

Provide either `prompt` or a structured `input`, not both. Set `thread.mode` to `ephemeral` (cleaned up after the run) or `persistent` (reuses a stable `thread.id` so state accumulates). Schedule declarations must be static literals, not values computed from env vars or function calls.

## Sandboxes

Configure a sandbox when the agent needs isolated code execution or filesystem work. Export `sandbox` from `sandbox/index.ts` or `sandbox/__init__.py`.

```python
# sandbox/__init__.py
from managed_deepagents import define_sandbox
from deepagents.backends import LangSmithSandbox

sandbox = define_sandbox(
    LangSmithSandbox,
    scope="thread",
    idle_ttl_seconds=600,
    default_timeout=600,
)
```

```ts
// sandbox/index.ts
import { defineSandbox } from "managed-deepagents";
import { LangSmithSandbox } from "deepagents";

export const sandbox = defineSandbox(LangSmithSandbox, {
  scope: "thread",
  idleTtlSeconds: 600,
  defaultTimeout: 600,
});
```

`scope` is `thread` (one sandbox per conversation) or `agent`. If `sandbox/setup.sh` exists, MDA runs it once when a new sandbox is provisioned. During `mda dev`, the runtime falls back to a local temp-directory sandbox when provider credentials are unavailable; the fallback is for development only.

## Skills

Put deploy-owned skills under `skills/<name>/SKILL.md`. Deploy syncs `skills/**` to Context Hub and deletes deployed skills that no longer exist locally. Each skill is a markdown file with `name` and `description` frontmatter that the agent loads on demand.

## CLI commands

| Command | Use |
| --- | --- |
| `mda init <name>` | Scaffold a Python or TypeScript project. |
| `mda dev [path]` | Compile into `.mda/build` and run the local LangGraph dev server in LangSmith Studio. Flags: `--port`, `--hostname`, `--browser`, `--no-reload`. |
| `mda deploy [path]` | Compile, sync Context Hub, upload, and deploy. Flags: `--name`, `--deployment-type dev\|prod`, `--tenant-id`, `--host-url`, `--no-wait`. |

For Python projects, run `uv sync` inside the generated project before `mda dev`. Authentication resolves in order: `LANGGRAPH_HOST_API_KEY`, `LANGSMITH_API_KEY`, `LANGCHAIN_API_KEY`, read from `.env` first, then the shell.

## Deploy and Context Hub

`mda deploy` compiles the project into `.mda/build` (copying your code verbatim, generating a managed LangGraph entry, excluding `node_modules`, `.git`, `.mda`, `memories`, `dist`, `build`, and `.env*`), then:

1. Resolves the LangSmith key and verifies the model provider key is available.
2. Forwards non-reserved `.env` values (provider keys, MCP tokens, database URLs) as hosted deployment secrets. The `.env` file is never uploaded.
3. Syncs `instructions.md` and `skills/**` to the deployment's Context Hub repo, preserving runtime memory.
4. Uploads the build, triggers a hosted build, and waits until the revision is `DEPLOYED` (unless `--no-wait`).
5. Reconciles managed cron jobs from `schedules/**`.

Context Hub stores `/instructions.md` and `/skills/**` (deploy-owned) and `/memories/AGENTS.md` (runtime-owned, durable across deploys). Set `disable_memory=True` / `disableMemory: true` to turn off managed agent memory.

Inspect build status, revisions, and traces on the deployment page in LangSmith.

## Human-in-the-loop

Pause before sensitive tool calls with `interrupt_on` / `interruptOn` (and gate access with `permissions`). See [[langgraph-human-in-the-loop]] for interrupt and resume semantics.

```python
agent = define_deep_agent(
    model="openai:gpt-5.5",
    tools=[query_db],
    interrupt_on={"query_db": True},
)
```

```ts
export const agent = defineDeepAgent({
  model: "openai:gpt-5.5",
  tools: [queryDB],
  interruptOn: { query_db: true },
});
```

When a run hits an interrupt, it pauses. During `mda dev`, respond to it in LangSmith Studio. On a deployed agent, resume through the LangGraph server API with a `Command(resume=...)` payload. During private beta, programmatic invocation from your own application is contact-your-team.

## Gotchas

- **Use the `mda` CLI**, not the older `deepagents` CLI or the removed `Client` SDK / `/v1/deepagents` REST surface. During private beta there is no public create/update/invoke API.
- **Do not set managed fields** (`backend`, `store`, `checkpointer`, `memory`, `skills`, system prompt) in the agent definition; the runtime owns them.
- **Model IDs need the provider prefix**: `openai:gpt-5.5`, not a bare model name.
- **MCP connectors support `http` and `sse` only**; stdio is rejected, and misconfiguration surfaces at build or dev startup.
- **`.env` is never archived**; deploy forwards non-reserved values as hosted secrets. Do not commit real secrets.
- **Schedule declarations must be static literals**; the compiler extracts them without running your code.
- **Private beta scope**: US LangSmith Cloud only, CLI-first. Self-hosted and Hybrid are not supported.
