---
name: managed-deep-agents
description: "INVOKE THIS SKILL when building, testing, or deploying Managed Deep Agents in LangSmith. Walks a user through their first agent end to end — interviewing them about what they want to build, mapping it onto what MDA can actually do, then scaffolding and deploying it. Covers the file-based project layout; define_deep_agent / defineDeepAgent and per-run agent factories; instructions, skills, agent and user memory, identity, tools, MCP servers, connections, middleware, sandboxes, browser use, subagents, schedules, Slack and HTTP channels, and evals; the mda CLI; regions and BYOC; and Context Hub."
---

# Managed Deep Agents

## Overview

Managed Deep Agents (MDA) is a hosted runtime for code-first Deep Agents in LangSmith. You author an agent in Python or TypeScript, test it locally with `mda dev`, and deploy it with `mda deploy`. It pairs the open-source Deep Agents harness (see [[deep-agents-core]]) with managed infrastructure: Agent Server deployments, sandboxes, browsers, Context Hub-backed instructions, skills, and memory, connections, schedules, channels, and traces.

The core idea is that **an agent is a directory**. A file's location determines its role, and the CLI compiles that directory into a managed LangGraph app.

MDA is in **public beta** on LangSmith Cloud (GCP US, GCP EU, GCP APAC, AWS US) and BYOC data planes. These instructions track SDK/CLI **0.10**.

Docs: <https://docs.langchain.com/langsmith/managed-deep-agents-overview>. When this skill and the installed package disagree, trust `mda --help` and the installed package.

## When to use

Use this skill when the user wants to build a Deep Agent in code and run it on LangSmith without operating their own server, or to add tools, MCP servers, connections, middleware, memory, identity, a sandbox, a browser, subagents, schedules, channels, skills, or evals to one.

Use a standard LangSmith Deployment instead (see [[langgraph-cli]], `langgraph deploy`) when the user needs custom server routes, a custom LangGraph auth handler, application code around the agent, a custom backend/store/checkpointer, or a Python `state_schema`. MDA can still sit behind a separately operated backend that authenticates callers (see backend identity in [references/capabilities.md](references/capabilities.md)).

# Guide the user through their first agent

When a user is new to MDA, or says anything like "help me build an agent", **do not scaffold immediately**. Run this flow. It costs two questions and prevents building something the platform cannot host.

```text
ask what they want to build -> check it against the limits -> confirm the shape
-> scaffold -> wire the smallest thing that runs -> mda dev -> deploy
```

## 1. Ask what they want to build

Ask in plain language, not in MDA vocabulary. The user does not yet know what a "channel" or a "sandbox" is.

Ask these two things first:

- **What should the agent do?** ("Answer questions about our docs", "triage incoming bugs", "post a summary every morning".)
- **Who or what talks to it, and from where?** (Them in a browser, their app's users, a Slack workspace, a webhook from another system, nobody — it runs on a timer.)

Then ask only the follow-ups that the answers actually raise:

- Does it need to remember anything between conversations — shared knowledge, or per-person preferences?
- Does it need to reach a private API, database, or a third-party account on the user's behalf?
- Should anything require a human to approve before it happens?
- Does it need to write files, run code, or use websites that have no API?

Stop asking once you can name the capabilities. Two or three questions is usually enough.

## 2. Check the answer against the limits

Before you promise anything, check the request against **[What MDA cannot do](#what-mda-cannot-do)** below. If part of the request is out of scope, say so in one sentence, offer the nearest supported thing, and keep going with the rest. Do not quietly build a smaller agent and present it as what they asked for.

The common redirect: if they need custom HTTP routes, a custom auth handler, or self-hosted/hybrid hosting, tell them MDA is the wrong layer and point at `langgraph deploy` ([[langgraph-cli]]).

## 3. Map the answer onto capabilities

| What the user describes | What to reach for | Where it lives |
| --- | --- | --- |
| How it should behave, its tone, its rules | Instructions | `instructions.md` |
| Calls our API / database / internal service | Authored tools | `tools/` |
| Uses a remote MCP server | MCP declaration | `tools/mcp.py` / `tools/mcp.ts` |
| Uses an API key or acts as the user in GitHub, Notion, … | Connection | `connections.get(...)` + `mda connections` |
| A procedure it should follow for certain tasks | Skills | `skills/<name>/SKILL.md` |
| Learns shared knowledge across conversations | Agent memory (read the warning) | `memory.py` |
| Remembers each person's preferences | User memory (needs person identity) | `memory.py` + `identity.py` |
| Signed-in users must not see each other's chats | Supabase, JWT, or backend identity | `identity.py` |
| Runs on a timer, no user message | Schedules | `schedules/<name>.py` |
| Lets the agent set reminders / follow-ups itself | Runtime schedules API | a tool calling `runtime.schedules` |
| Lives in Slack | Slack channel | `channels/slack.py` |
| Triggered by a webhook from another system | HTTP channel | `channels/<name>.py` |
| Writes files, runs code or shell commands | Sandbox | `sandbox/` |
| Uses websites with no API, logs in, fills forms | Browser | `browser.py` |
| Ask me before it does X | Human-in-the-loop | `interrupt_on=` / `permissions=` |
| Must return structured data, not prose | Structured output | `response_format=` |
| Hand off specialized or long-running work | Subagents (sync or `async`) | `subagents=` |
| Different config per caller, repo, or tenant | Agent factory | `agent(runtime)` in `agent.py` |
| PII redaction, call limits, retries, logging | Middleware | `middleware/` |
| Prove it still works as we change it | Harbor evals | `evals/<task>/` |
| Call it as a tool from Claude Code / MCP clients | Built-in MCP endpoint | `<deployment API URL>/mcp` |

## 4. Confirm the shape before writing files

State the plan back in one short block and get agreement. Name the model, and list only the capabilities you are actually going to create:

```text
research-assistant, Python, on openai:gpt-5.5
  instructions.md   how it researches and cites
  tools/search.py   web search
  schedules/        weekday 8am digest
  no memory, no sandbox, no channel
```

## 5. Scaffold and wire the smallest thing that runs

Scaffold with the flags that match the plan, so the project starts correct instead of being edited into shape:

```bash
uvx --from managed-deepagents mda init research-assistant --model openai:gpt-5.5 --no-sandbox
cd research-assistant
uv sync
```

TypeScript: `npx managed-deepagents init research-assistant --model openai:gpt-5.5 --no-sandbox`, then `npm install`.

Then add **one** capability at a time and confirm each one works before adding the next. A first agent that answers with good instructions and one real tool is a better starting point than a scaffold with every directory filled in.

Do not create files the plan did not call for. Empty `skills/`, `channels/`, or `schedules/` directories are noise; a `sandbox/` directory turns on a sandbox (`mda init` scaffolds one unless you pass `--no-sandbox`), and a root `browser.py` turns on a browser.

## 6. Handle keys without touching their secrets

`mda init` writes a `.env` with empty placeholders. Fill in the *names* the project needs and let the user paste the *values*:

- Do not write live credential values into `.env` yourself, and do not copy a key from another project directory.
- Do not echo key values to the terminal or into your reply.
- Confirm `.gitignore` covers `.env` and `.env.*` — `mda init` does this already.

The project needs a LangSmith API key (`LANGSMITH_API_KEY`) to deploy, and whatever credentials its model requires (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, …) in `.env`, the shell, or LangSmith workspace secrets. A `langsmith:` LLM Gateway model uses Gateway credits or a workspace provider secret instead of a provider key. For a non-default region or BYOC, also set `LANGSMITH_ENDPOINT` (see [Deploy](#deploy)).

## 7. Run it locally, then deploy

```bash
uv run mda dev       # compiles, opens LangSmith Studio
uv run mda deploy    # syncs Context Hub, uploads, waits for DEPLOYED
```

TypeScript: `npx mda dev` / `npx mda deploy`.

Have the user actually send a message in Studio (or `mda chat` in the terminal) and confirm the agent calls the tool before deploying. `mda deploy` prints the deployment dashboard URL; open it to inspect builds, revisions, and traces.

## What MDA cannot do

Check requests against this list *before* agreeing to build them. Being straight about a limit early is cheaper than discovering it at deploy time.

| Limit | Consequence |
| --- | --- |
| LangSmith Cloud and BYOC only | No self-hosted or hybrid MDA. Serverless deployments (the default) need GCP SaaS; elsewhere pass `--deployment-type dedicated`. LangSmith managed tools (for example Parallel search) are GCP US only. |
| No public management API | Use `mda` to create and update agents. Do not invent a public create/update REST flow. |
| Channels are Slack and HTTP | One Slack channel per deployment. Any other service (Discord, Teams, email, your app) goes through an HTTP channel adapter. GitHub and Linear channels are experimental. |
| Agent memory is deployment-shared | `/memories/agent/` is readable and writable by every caller. Per-person memory is the separate user layer and needs person identity. |
| No custom auth handler or routes | MDA's handler keys threads, credentials, and user memory on the user ID. Use Supabase, a JWT provider, or backend identity. |
| Workspace members see all threads | Studio/workspace API access can read every thread regardless of identity provider. Privacy holds against end users, not workspace members. |
| One agent entry per project | No multiple graphs in one project. Use `subagents=` for delegation. |
| Schedule files are static literals | No env vars, function calls, or computed values in `schedules/`. Use `runtime.schedules` for dynamic schedules. |
| Remote MCP only | Streamable HTTP or SSE. Stdio MCP servers are not supported. |
| Build archive capped at 200 MB | Large fixtures or model weights in the project will fail the deploy. |
| Managed fields are not yours to set | `backend`, `store`, `checkpointer`, `memory`, `skills`, and `system_prompt` are runtime-owned. Python `state_schema` is rejected. |
| Sandbox is one per thread | The sandbox `scope` option was removed; setting it fails the build. |

## Prerequisites

- A LangSmith workspace on LangSmith Cloud or a BYOC data plane, and a LangSmith API key for it.
- Python and [`uv`](https://docs.astral.sh/uv/) for Python projects; Node.js and npm (or pnpm/bun) for TypeScript.
- Credentials required by the selected model.

`mda init` declares `managed-deepagents` as a project dependency, so run `mda` from inside the project (`uv run mda …` / `npx mda …`) after `uv sync` / `npm install`. The installed package selects the scaffold language: PyPI writes Python, npm writes TypeScript.

## Project layout

```text
my-agent/
  agent.py | agent.ts | agent.tsx  # Required: exports the named `agent`

  instructions.md                  # System prompt -> Context Hub
  skills/<name>/SKILL.md           # On-demand procedures -> Context Hub

  tools/                           # Authored tools the agent imports
    mcp.py | mcp.ts                # Remote MCP server declaration (named `mcp`)
  middleware/                      # Authored middleware the agent imports

  identity.py | identity.ts        # Who may call the deployment
  memory.py | memory.ts            # Opt-in agent/user memory
  browser.py | browser.ts          # Opt-in browser
  channels/<name>.py               # Slack or HTTP channels (one per file)
  schedules/<name>.py              # Managed cron schedules (one per file)
  sandbox/__init__.py | index.ts   # Managed sandbox
  sandbox/setup.sh                 # Optional snapshot recipe

  pyproject.toml | package.json    # Dependencies
  .env                             # Auth + runtime secrets, never archived

  evals/<task>/                    # Harbor tasks, not deployed
```

Only the agent entry is required. `tools/` and `middleware/` are plain conventions — MDA copies project files verbatim, so any local module the agent imports works. For `channels/` and `schedules/`, only direct children are managed declarations. The build copies only the project directory; share sibling code as a local package (`uv add ../shared`).

## Define the agent

The agent entry returns a definition, not a compiled graph. The runtime compiles it with `create_deep_agent` / `createDeepAgent`.

```python
# agent.py
from managed_deepagents import define_deep_agent

from tools.search import web_search

agent = define_deep_agent(
    name="research-assistant",
    model="openai:gpt-5.5",
    tools=[web_search],
)
```

```ts
// agent.ts
import { defineDeepAgent } from "managed-deepagents";

import { webSearch } from "./tools/search";

export const agent = defineDeepAgent({
  name: "research-assistant",
  model: "openai:gpt-5.5",
  tools: [webSearch],
});
```

**`name` is required.** Pass an inline static string matching `[a-zA-Z][a-zA-Z0-9_-]*`. It becomes the graph ID / `assistant_id`, the MCP tool name, and the default deployment name; override the latter with `mda deploy --name`.

**Author-set fields:** `name`, `model`, `tools`, `middleware`, `subagents`, `permissions`, `interrupt_on` / `interruptOn`, `response_format` / `responseFormat`, `context_schema` / `contextSchema`, `cache`, `debug`, `metadata`.

**Managed fields — do not set:** `backend`, `store`, `checkpointer`, `memory`, `skills`, `system_prompt` / `systemPrompt`. A project with `sandbox/` runs with `permissions` cleared, because a permission rule disables the sandbox `execute` tool.

Model IDs use `{provider}:{model_id}` and resolve through `init_chat_model`. Python uses `google_genai:gemini-3.6-flash`; TypeScript uses `google:gemini-3.6-flash`. Pass a chat model instance (for example `AzureAIOpenAIApiChatModel` for Microsoft Foundry) when you need to configure it in code.

**LLM Gateway:** use `model="langsmith:<provider>/<model>"`, for example `langsmith:moonshotai/kimi-k3`. Gateway IDs use a slash after the provider; direct IDs use a colon. The old `mda init --gateway` flag was removed — do not pass it.

**Per-run configuration:** export a sync or async factory `agent(runtime)` that returns `define_deep_agent(...)` to select model, tools, `instructions`, `skills`, `mcp`, `sandbox`, `memory`, or `browser` per run from `runtime.execution_runtime.context`. Keep it side-effect free. See [references/capabilities.md](references/capabilities.md#per-run-agent-factory).

## Instructions and skills

`instructions.md` at the project root is the system prompt, inserted on every run. Skills live under `skills/<name>/SKILL.md` with `name` and `description` frontmatter; the agent sees only names and descriptions until a task matches, then reads the file. A skill directory may hold scripts, references, and templates.

Use **instructions** for always-on behavior, **skills** for procedures loaded on demand, and **memory** for knowledge the agent itself updates. The agent cannot modify instructions or skills.

`mda deploy` syncs both to Context Hub and deletes deployed skill files that no longer exist locally. Hub edits apply without a redeploy, but the project copy is the source of truth: if Hub changed since the last sync, deploy prompts to overwrite, and non-interactive shells must pass `--context-strategy overwrite|keep-hub`. `mda dev` uses a local Context Hub mock.

## Capabilities

Code, options, and caveats for each capability live in [references/capabilities.md](references/capabilities.md). Read the relevant section before writing that file. Highlights:

- **Memory** — `define_memory(agent=MemoryLayer())` / `defineMemory({ agent: memoryLayer() })`. Add `user=MemoryLayer()` for per-person memory at `/memories/user/`, which mounts only for an authenticated person. `define_memory(scope="agent")` is rejected.
- **Identity** — scaffolded default is `auth.langsmith_api_key()` (`x-api-key`, no per-user privacy). For private threads use `auth.supabase(...)`, a generic JWT provider dict, or `auth="backend"` with `MDA_INGRESS_SECRET`.
- **Tools, MCP, connections** — tools are imported normally; MCP servers go in `tools/mcp.*` via `define_mcp(servers=...)`; credentials come from `await connections.get(slug, {"type": "agent"|"user"})`.
- **Sandbox** — `define_sandbox(...)`, optional `sandbox/setup.sh` snapshot, proxy headers with connections, `runtime.backend` from tools.
- **Browser** — root `browser.py` with `define_browser(scope="thread"|"user")`; adds `browser_run`, `browser_snapshot`, `browser_screenshot`, `browser_handoff`.
- **Subagents** — sync subagents via `task`; `"async": True` subagents run as their own graph and report back.
- **Schedules** — static `schedules/<name>.py`, or `runtime.schedules.create(...)` from a tool.
- **Channels** — `channels.slack()` (LangSmith provisions the Slack app on deploy) or `channels.http(provider=..., verify=..., parse=...)`.
- **Runtime** — tools read the caller from `runtime.server_info.principal`, the conversation from `runtime.thread.origin`, and the sandbox from `runtime.backend`. `runtime.channel` is deprecated.

## Middleware

Middleware wraps model calls, tool calls, and lifecycle hooks. Order is explicit in the list; MDA never infers it. Use prebuilt LangChain middleware or author your own (see [[langchain-middleware]]).

```python
from langchain.agents.middleware import ModelCallLimitMiddleware, PIIMiddleware
from managed_deepagents import define_deep_agent

agent = define_deep_agent(
    name="support-agent",
    model="openai:gpt-5.5",
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        ModelCallLimitMiddleware(run_limit=50),
    ],
)
```

## Human-in-the-loop

Pause before sensitive tool calls with `interrupt_on`, or pause on filesystem paths with `permissions` in `mode="interrupt"`:

```python
agent = define_deep_agent(
    name="support-agent",
    model="openai:gpt-5.5",
    tools=[refund_customer],
    interrupt_on={"refund_customer": True},
)
```

`interrupt_on` behaves like LangChain's human-in-the-loop middleware; see [[langgraph-human-in-the-loop]]. The managed runtime owns the checkpointer, so no extra setup is required. Respond in Studio or `mda chat` during development; on a deployment, resume through the Agent Server API with `Command(resume=...)`. Slack approval cards offer only approve and reject.

## Evals

MDA evals are [Harbor](https://www.harborframework.com/docs/tasks) tasks. `evals/` is the authored dataset; put complete tasks under `evals/<task>/`. `.mda/evals/` is generated — do not edit or commit it.

```bash
uv run mda evals init -i
```

`mda evals init` writes `evals/harbor-job.json` and the generated adapter, then `-i` hands off to a coding agent with the `eval-engineering` skill ([[eval-engineering]]). It does not run trials; it prints the pinned `uv run --env-file .env … harbor run` command. Harbor needs Docker. Verifiers write a numeric reward to `/logs/verifier/reward.txt` or metrics to `/logs/verifier/reward.json`. `mda evals compile` is internal — do not tell users to run it. Agents with `async` subagents cannot be evaluated this way.

## CLI reference

| Command | Use |
| --- | --- |
| `mda init [name]` | Scaffold a project. Fails if the destination exists. |
| `mda build [path]` | Compile into a managed LangGraph app without deploying. |
| `mda dev [path]` | Compile and run the local dev server with LangSmith Studio. |
| `mda chat [path]` | Chat from the terminal against a local dev server (starts one if needed). |
| `mda deploy [path]` | Compile, sync Context Hub, upload, deploy, reconcile schedules, set up channels. |
| `mda logs [path]` | Tail Agent Server logs for a deployed agent. |
| `mda delete [path]` | Delete a deployment and the LangSmith resources it created. Alias: `destroy`. |
| `mda connections create\|list\|get\|delete\|catalog` | Manage workspace-scoped secrets and OAuth registrations. |
| `mda channels init slack` | Add a Slack channel declaration. |
| `mda channels setup` | Experimental: set up a deployed agent's channels without redeploying. |
| `mda evals init` | Initialize the Harbor eval workspace and print the run handoff. |

Key flags:

- `init`: `-i`, `--model SPEC`, `--instructions TEXT`, `--instructions-file PATH`, `--memory agent|none`, `--no-sandbox`, `-c` / `--channel slack`
- `build`: `--out OUT` (defaults to `<path>/.mda/build`)
- `dev`: `--port`, `--hostname`, `--no-browser`, `--no-reload`, `--tunnel`, `--no-schedules`, `--env-file`
- `deploy`: `--name`, `--deployment-type serverless|dedicated`, `--workspace-id`, `--context-strategy overwrite|keep-hub`, `--no-wait`, `--wait-timeout-seconds`, `--env-file`, `--yes`
- `logs`: `--name`, `--lines`, `--level`, `--follow` / `--no-follow`, `--workspace-id`
- `delete`: `--name`, `--workspace-id`, `--yes`

> `mda delete` is destructive and removes the deployment, its sandboxes, snapshots, and other LangSmith resources. **Confirm with the user before running it, and never pass `--yes` unprompted.** The same applies to `mda deploy --yes`, which overwrites same-name resources on a first deploy.

## Deploy

`mda deploy` creates a **Serverless** deployment by default (GCP SaaS only; can scale to zero). Pass `--deployment-type dedicated` for always-on capacity or for AWS US and BYOC. Existing deployments keep their type.

`LANGSMITH_ENDPOINT` selects the region; the default is GCP US. Set it before the first deploy, because it also selects where browser sign-in authenticates:

| Region | `LANGSMITH_ENDPOINT` |
| --- | --- |
| GCP US | `https://api.smith.langchain.com` |
| GCP EU | `https://eu.api.smith.langchain.com` |
| GCP APAC | `https://apac.api.smith.langchain.com` |
| AWS US | `https://aws.api.smith.langchain.com` |

For BYOC, set `LANGSMITH_ENDPOINT` to the data plane's API URL (Settings > Data Planes, without `/api-host`), plus `LANGSMITH_WORKSPACE_ID` or `--workspace-id`.

`mda deploy` routes local inputs to different managed surfaces:

```text
instructions.md + skills/**   -> Context Hub deploy-owned context
.env                          -> deploy auth + non-reserved hosted secrets (never archived)
project source                -> .mda/build archive -> hosted deployment
schedules/**                  -> LangSmith cron jobs, after the deployment is live
channels/**                   -> Slack/HTTP channel setup
```

The CLI reads `LANGGRAPH_HOST_API_KEY`, `LANGSMITH_API_KEY`, then `LANGCHAIN_API_KEY`. Shell values win over the project `.env` for these and for `LANGSMITH_ENDPOINT` / `LANGSMITH_WORKSPACE_ID`; `mda` warns when the two differ. In an interactive terminal with no key, deploy prompts for one or uses browser sign-in. CI needs `LANGSMITH_API_KEY` for the target region.

Non-reserved `.env` entries — provider keys, tool credentials, database URLs, `MDA_INGRESS_SECRET` — are forwarded as hosted deployment secrets. Reserved platform variables authenticate the deploy and are not uploaded. Prefer `.env` or LangSmith workspace secrets for anything the deployment needs.

Python deployments build on Python 3.11–3.14, newest allowed by `requires-python`; pin with `[tool.mda] python-version = "3.13"` in `pyproject.toml` or `MDA_PYTHON_VERSION`.

Every deployment also serves the Agent Server MCP endpoint at `<deployment API URL>/mcp` (copy the API URL from the dashboard), authenticated by the deployment's identity — use the LangSmith API-key default for MCP clients.

LangSmith can also build from a connected GitHub repository, running the hidden `mda prepare` step. Never ask a user to run `mda prepare`; in that flow Git is authoritative for `instructions.md` and `skills/**`.

Troubleshooting: `no agent entry file found` → add `agent.py` / `agent.ts` at the root. 401/403 → the key's workspace lacks deployment access or belongs to another region. Context Hub conflict → answer the prompt or pass `--context-strategy`. Missing model key → add it to `.env` or workspace secrets. Build over 200 MB → remove generated artifacts. `BUILD_FAILED` / `DEPLOY_FAILED` → open the printed URL and read the revision logs.

## Gotchas

- **`name=` is required** and must be an inline string, even in a factory.
- **Use `openai:gpt-5.5`-style IDs.** Python Gemini is `google_genai:`, TypeScript is `google:`, Gateway is `langsmith:provider/model`.
- **Memory uses layers.** `define_memory(agent=MemoryLayer())` / `user=MemoryLayer()`. String `scope` is rejected, `disable_memory` is legacy, and `allow` callbacks are deprecated in favor of factory selection.
- **User memory needs a person.** The LangSmith API-key identity is a service principal and never mounts `/memories/user/`.
- **MCP lives at `tools/mcp.*`** with a named `mcp` export and `servers`. `connectors.mcp(...)`, `connectors/`, and `mcpServers` were removed in 0.10 and fail the build.
- **Agent-owned connections belong to a deployment.** Create them after the first successful deploy, and once per project that uses the slug. `mda dev` reads agent-owned opaque connections from `MDA_DEV_<SLUG>`.
- **Restart `mda dev` after adding a managed file** (`memory.py`, `identity.py`, `browser.py`, `tools/mcp.py`, `schedules/`, `channels/`).
- **`--no-wait` skips schedule reconciliation** and cannot be used with a Slack channel.
- **`runtime.channel` is deprecated** (removed in 0.11). Read `runtime.thread.origin.channel`.
- **Do not set sandbox `scope`.** Sandboxes are always one per thread.
- **`.env` is never archived**, and `.gitignore` must keep it out of version control. Do not write live keys into it on a user's behalf.
- **The SDK moves quickly.** Verify flags with the installed `mda --help`. `mda prepare` and `mda evals compile` are internal.
