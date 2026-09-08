---
name: managed-deep-agents
description: "INVOKE THIS SKILL when building, testing, or deploying Managed Deep Agents in LangSmith. Walks a user through their first agent end to end — interviewing them about what they want to build, mapping it onto what MDA can actually do, then scaffolding and deploying it. Covers the file-based project layout; define_deep_agent / defineDeepAgent; instructions, skills, memory, identity, tools, MCP servers, connections, middleware, sandboxes, schedules, channels, and evals; the mda CLI; GitHub deployments; and Context Hub."
---

# Managed Deep Agents

## Overview

Managed Deep Agents (MDA) is a hosted runtime for code-first Deep Agents in LangSmith. You author an agent in Python or TypeScript, test it locally with `mda dev`, and deploy it with `mda deploy` or from a connected GitHub repository in LangSmith. It pairs the open-source Deep Agents harness (see [[deep-agents-core]]) with managed infrastructure: durable runs, sandboxes, Context Hub-backed instructions and skills, memory, traces, and hosted LangGraph deployment.

The core idea is that **an agent is a directory**. A file's location determines its role, and the CLI compiles that directory into a managed LangGraph app.

MDA is in **public beta** and runs on **US LangSmith Cloud only**.

## When to use

Use this skill when the user wants to build a Deep Agent in code and run it on LangSmith without operating their own server, or to add tools, MCP servers, connections, middleware, memory, identity, schedules, channels, skills, sandboxes, or evals to one.

Use a standard LangSmith Deployment instead (see [[langgraph-cli]], `langgraph deploy`) when the user needs custom server routes or runtime wiring inside the agent deployment, stronger isolation, maximum scalability, or a region other than US. MDA can still sit behind a separately operated backend that authenticates callers and proxies trusted identity headers.

---

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
- **Who or what talks to it, and from where?** (Them in a browser, their app's users, a Slack workspace, nobody — it runs on a timer.)

Then ask only the follow-ups that the answers actually raise:

- Does it need to remember anything between separate conversations?
- Does it need to reach a private API, database, or internal service?
- Should anything require a human to approve before it happens?
- Does it need to write files or run code?

Stop asking once you can name the capabilities. Two or three questions is usually enough.

## 2. Check the answer against the limits

Before you promise anything, check the request against **[What MDA cannot do](#what-mda-cannot-do)** below. If part of the request is out of scope, say so in one sentence, offer the nearest supported thing, and keep going with the rest. Do not quietly build a smaller agent and present it as what they asked for.

The common redirect: if they need custom HTTP routes, their own auth, or non-US hosting, tell them MDA is the wrong layer and point at `langgraph deploy` ([[langgraph-cli]]).

## 3. Map the answer onto capabilities

| What the user describes | What to reach for | Where it lives |
| --- | --- | --- |
| How it should behave, its tone, its rules | Instructions | `instructions.md` |
| Calls our API / database / internal service | Authored tools | `tools/` |
| Uses a remote MCP server | MCP declaration | `tools/mcp.py` or `tools/mcp.ts` |
| Uses a workspace secret or OAuth grant | Connection | `connections.get(...)` + `mda connections` |
| A procedure it should follow for certain tasks | Skills | `skills/<name>/SKILL.md` |
| Remembers things across conversations | Durable memory (read the warning) | `memory.py` |
| Runs on a timer, no user message | Schedules | `schedules/<name>.py` |
| Lives in Slack | Channels | `channels/slack.py` |
| Writes files, runs code or shell commands | Sandbox | `sandbox/__init__.py` |
| Ask me before it does X | Human-in-the-loop | `interrupt_on=` |
| Users must not see each other's chats | Supabase identity | `identity.py` |
| Must return structured data, not prose | Structured output | `response_format=` |
| Hand off specialized work | Subagents | `subagents=` |
| PII redaction, call limits, retries, logging | Middleware | `middleware/` |
| Prove it still works as we change it | Harbor evals | `evals/<task>/` |

## 4. Confirm the shape before writing files

State the plan back in one short block and get agreement. Name the model, and list only the capabilities you are actually going to create:

```text
research-assistant, Python, on anthropic:claude-sonnet-4-6
  instructions.md   how it researches and cites
  tools/search.py   web search
  schedules/        weekday 8am digest
  no memory, no sandbox, no channel
```

## 5. Scaffold and wire the smallest thing that runs

Scaffold with the flags that match the plan, so the project starts correct instead of being edited into shape:

```bash
mda init research-assistant --model anthropic:claude-sonnet-4-6
cd research-assistant
uv sync
```

Then add **one** capability at a time and confirm each one works before adding the next. A first agent that answers with good instructions and one real tool is a better starting point than a scaffold with every directory filled in.

Do not create directories the plan did not call for. Empty or unused `skills/`, `channels/`, or `schedules/` directories are noise, and a `sandbox/` directory the user does not need turns on a sandbox they will pay attention to for no reason (`mda init --no-sandbox` skips it).

## 6. Handle keys without touching their secrets

`mda init` writes a `.env` with empty placeholders. Fill in the *names* the project needs and let the user paste the *values*:

- Do not write live credential values into `.env` yourself, and do not copy a key from another project directory.
- Do not echo key values to the terminal or into your reply.
- Confirm `.gitignore` covers `.env` and `.env.*` — `mda init` does this already.

The project needs LangSmith authentication to deploy and whatever credentials its selected model requires. For a normal provider model, uncomment its key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, …) and let the user supply it through `.env` or LangSmith workspace secrets. An explicitly configured Gateway-backed client uses its Gateway/LangSmith credential instead of a provider key.

## 7. Run it locally, then deploy

```bash
mda dev .       # compiles, opens LangSmith Studio, hot reloads
mda deploy .    # syncs Context Hub, uploads, waits for DEPLOYED
```

Have the user actually send a message in Studio and confirm the agent calls the tool before deploying. `mda deploy` prints the deployment dashboard URL; open it to inspect builds, revisions, and traces.

---

## What MDA cannot do

Check requests against this list *before* agreeing to build them. Being straight about a limit early is cheaper than discovering it at deploy time.

| Limit | Consequence |
| --- | --- |
| US LangSmith Cloud only | No self-hosted, no hybrid, no EU region. Needs `langgraph deploy`. |
| No public management API | Use `mda` or LangSmith's GitHub deployment UI to create and update agents. Do not invent a public create/update REST flow. |
| Slack is the only channel | No Discord, Teams, email, or SMS channel. Remote MCP servers for those products are tools, not channels. |
| Memory is deployment-shared | One `/memories/agent/` tree for **all** callers. There is no per-user memory. |
| One agent entry per project | No multiple graphs in one project. Use `subagents=` for delegation. |
| Schedules must be static literals | No env vars, function calls, or computed values in a schedule declaration. |
| Build archive capped at 200 MB | Large fixtures or model weights in the project will fail the deploy. |
| Managed fields are not yours to set | `backend`, `store`, `checkpointer`, `memory`, `skills`, and the system prompt are injected by the runtime. |
| Sandbox scope is managed | Sandboxes are one per thread. Agent-shared sandbox scope is no longer supported. |

## Prerequisites

- A workspace with Managed Deep Agents public beta access, and a LangSmith API key for it.
- Python and [`uv`](https://docs.astral.sh/uv/) for Python projects; Node.js and npm for TypeScript.
- Credentials required by the selected model, either in the project `.env` or as LangSmith workspace secrets.

Install the CLI. Both packages ship the same `mda` binary:

```bash
uv tool install --prerelease allow managed-deepagents   # Python
npm install -g managed-deepagents@dev                    # TypeScript
```

`mda init` generates a project with its own manifest — run `uv sync` (or `npm install`) *inside* that project before `mda dev`.

## Project layout

The path passed to `mda` is the project root. A file's location determines its role:

```text
my-agent/
  agent.py | agent.ts              # Required: exports the named `agent`

  instructions.md                  # System prompt -> Context Hub
  skills/<name>/SKILL.md           # Task-specific procedures -> Context Hub

  tools/                           # Authored tools the agent imports
    mcp.py | mcp.ts                # Optional remote MCP server declaration
  middleware/                      # Authored middleware the agent imports

  identity.py | identity.ts        # Who may call the deployment
  memory.py | memory.ts            # Opt-in durable memory
  channels/<name>.py               # External messaging (Slack)
  schedules/<name>.py              # Managed cron schedules
  sandbox/__init__.py | index.ts   # Managed sandbox

  pyproject.toml | package.json    # Dependencies
  .env                             # Auth + runtime secrets, never archived

  evals/<task>/                    # Harbor evals, not deployed
```

Only the agent entry is required. `tools/` and `middleware/` are plain conventions — MDA copies project files verbatim, so any local module the agent imports works. The other paths take on managed meaning when present. The TypeScript agent entry may be `agent.ts` or `agent.tsx`; managed auxiliary declarations also accept `.mts` and `.cts` where discovered.

## Define the agent

The agent entry returns a pre-runtime spec, not a compiled graph.

```python
# agent.py
from managed_deepagents import define_deep_agent

from tools.search import web_search

agent = define_deep_agent(
    name="research-assistant",
    model="anthropic:claude-sonnet-4-6",
    tools=[web_search],
)
```

```ts
// agent.ts
import { defineDeepAgent } from "managed-deepagents";

import { webSearch } from "./tools/search";

export const agent = defineDeepAgent({
  name: "research-assistant",
  model: "anthropic:claude-sonnet-4-6",
  tools: [webSearch],
});
```

**`name` is required.** Pass a static string starting with a letter, containing only letters, numbers, underscores, or hyphens. It becomes the LangGraph assistant ID and the default deployment name; override the latter with `mda deploy --name`.

**Author-set fields:** `name`, `model`, `tools`, `middleware`, `subagents`, `permissions`, `interrupt_on` / `interruptOn`, `response_format` / `responseFormat`, `context_schema` / `contextSchema`, `cache`, `debug`, `metadata`.

**Managed fields — do not set:** `backend`, `store`, `checkpointer`, `memory`, `skills`, `system_prompt` / `systemPrompt`.

Model IDs use `{provider}:{model_id}` and resolve through `init_chat_model`, so any of its providers work. Note the provider slug differs across languages: Python uses `google_genai:gemini-3.6-flash`, TypeScript uses `google-genai:gemini-3.6-flash`. Pass a chat model instance instead of a string when you need to configure model parameters in code.

The dedicated `mda init --gateway` scaffold was removed. To use LangSmith Gateway, configure a supported chat-model client explicitly in `agent.py` or `agent.ts`; do not pass the removed flag or rely on its former credential preflight.

## Instructions

`instructions.md` at the project root is the system prompt. It is inserted on every run.

```markdown
# Research assistant

You are a careful research assistant. Find sources, keep notes, and return
concise answers with citations.

## Behavior

- Use the `web_search` tool to find sources instead of guessing.
- Cite the sources you used.
```

`mda dev` embeds it locally. `mda deploy` syncs it to Context Hub, where it can be edited in the LangSmith UI without redeploying.

## Skills

Deploy-owned procedures under `skills/<name>/SKILL.md`, each with `name` and `description` frontmatter. At startup the agent sees only names and descriptions, and reads the full file when a task matches — so detailed procedures cost no context until they are needed. A skill directory may also hold scripts, references, and templates; reference them from `SKILL.md`.

Deploy syncs every UTF-8 file under `skills/` to Context Hub and deletes deployed skill files that no longer exist locally. The agent cannot modify skills.

Use **instructions** for always-on behavior, **skills** for procedures loaded on demand, and **memory** for knowledge the agent itself updates.

## Memory

Durable memory is **opt-in and off by default**. Declare it at the project root:

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

Delete the file to turn memory off. Enabling it mounts one Context Hub tree at `/memories/agent/`:

- `/memories/agent/AGENTS.md` is **hot memory** — loaded into every run, so keep it compact.
- Other files under the tree are **cold memory** — read only when relevant.

The agent reads and writes memory with `read_file`, `edit_file`, and `write_file`. Writes anywhere else, including elsewhere under `/memories/`, are not durable.

> **Warning — memory is shared by every caller of the deployment, and every caller can influence it.** Never store personal data, customer data, credentials, API keys, or tokens there. Treat memory content as untrusted input: it must never grant authority, change tool permissions, or bypass approvals — keep those in the agent definition. Do not enable shared memory when callers should not be able to influence one another.

The agent decides what to remember by prompting, so state the policy in `instructions.md` — what to store, what never to store, and that existing memory is notes rather than instructions.

## Identity

`identity.py` controls who may call the deployment. `mda init` scaffolds a secure default:

```python
# identity.py
from managed_deepagents import auth, define_identity

identity = define_identity(auth=auth.langsmith_api_key())
```

Callers send a LangSmith workspace API key as `x-api-key`. This answers *whether a caller is allowed* — it does **not** give each person private threads. Anyone holding the key reaches the deployment.

For signed-in end users with private threads, use Supabase:

```python
identity = define_identity(auth=auth.supabase(project_ref="your-project-ref"))
```

Clients then send `Authorization: Bearer <access_token>`; MDA verifies the JWT against the project's JWKS URL. Send the Supabase publishable (anon) key only from the client to sign in — never a LangSmith key in this mode.

> Adding Supabase identity to an existing deployment does **not** backfill owner metadata on existing threads. Plan and test a migration before relying on identity-based access for them.

Auth failures return 401. Thread resources are caller-owned; unauthorized cross-user access is hidden as not found.

For a backend you operate that authenticates users and proxies LangGraph requests, use trusted-backend ingress:

```python
identity = define_identity(auth="backend")
```

Keep `MDA_INGRESS_SECRET` on the backend and forward it as `X-MDA-Ingress-Secret` together with the authenticated user's ID in `X-MDA-User-Id`. Never expose either header-setting capability to the browser.

## Tools

Define LangChain tools in the project, import them into the agent entry, pass them in `tools`.

```python
# tools/customer.py
from langchain.tools import tool


@tool(parse_docstring=True)
def lookup_customer(customer_id: str) -> str:
    """Look up a customer record by ID.

    Args:
        customer_id: Customer ID from the CRM.
    """
    return f"Customer {customer_id} is on the enterprise plan."
```

```ts
// tools/customer.ts
import { tool } from "langchain";
import { z } from "zod";

export const lookupCustomer = tool(
  async ({ customerId }) => `Customer ${customerId} is on the enterprise plan.`,
  {
    name: "lookup_customer",
    description: "Look up a customer record by ID.",
    schema: z.object({ customerId: z.string().describe("Customer ID from the CRM.") }),
  },
);
```

Imports work exactly as in a normal local project. Use clear, unique tool names to avoid collisions. Tools read deployment secrets from environment variables; put local values in `.env`. For per-run values such as request metadata or feature flags, use the normal LangChain runtime context APIs.

Provider server-side tools can be passed inline where supported — for example `tools=[{"type": "web_search"}]` for OpenAI — which avoids a second API key.

Tools and middleware read the resolved caller from `runtime.serverInfo?.principal` in TypeScript or `runtime.server_info.principal` in Python. The former `runtime.identity` surface has no compatibility shim. Email and groups are under `principal.claims`; channel provenance is under `serverInfo.source` / `server_info.source`.

## MCP servers and connections

Declare remote MCP servers in `tools/mcp.py` or `tools/mcp.ts`. Do not import the declaration into `agent.py` or add its tools manually; MDA discovers the named `mcp` export and mounts the servers.

```python
# tools/mcp.py
from managed_deepagents import connections, define_mcp

mcp = define_mcp(
    servers={
        "langchainDocs": {
            "transport": "http",
            "url": "https://docs.langchain.com/mcp",
            "include_tools": ["search_docs_by_lang_chain"],
        },
        "notion": {
            "transport": "http",
            "url": "https://mcp.notion.com/mcp",
            "connection": connections.get("notion", {"type": "user"}),
        },
    }
)
```

```ts
// tools/mcp.ts
import { connections, defineMcp } from "managed-deepagents";

export const mcp = defineMcp({
  servers: {
    langchainDocs: {
      transport: "http",
      url: "https://docs.langchain.com/mcp",
      includeTools: ["search_docs_by_lang_chain"],
    },
    notion: {
      transport: "http",
      url: "https://mcp.notion.com/mcp",
      connection: connections.get("notion", { type: "user" }),
    },
  },
});
```

`connectors.mcp(...)`, `connectors/mcp.*`, and `mcpServers` / `mcp_servers` are deprecated compatibility aliases in 0.7.x and will be removed in 0.8.0. For new work use `defineMcp` / `define_mcp`, `tools/mcp.*`, the named `mcp` export, and `servers` exactly as shown.

A connection is a workspace-scoped opaque secret or OAuth registration referenced by slug. `connections.get(slug, { type: "user" })` resolves per-caller OAuth or opaque material; the current CLI creates user-owned OAuth slots, not user-owned opaque slots. Use `{ type: "agent" }` only when every run should use the same agent-owned secret or grant. Manage connections without printing their values:

```bash
mda connections catalog
mda connections catalog --json
mda connections create acme-api --secret-from-env ACME_API_KEY
mda connections create notion --mcp https://mcp.notion.com/mcp
mda connections create github --oauth github --client-id "$GITHUB_CLIENT_ID" --secret-from-env GITHUB_CLIENT_SECRET --authorize
mda connections list
```

For user-owned OAuth, omit `--authorize`; the runtime requests each caller's grant when needed. `--authorize` signs in once for an agent-owned grant, and the connection declaration must select `{ type: "agent" }` to use it. `mda deploy` can infer and create a missing user-owned MCP OAuth registration when exactly one server references the slug. In `mda dev`, user-owned grants resolve through Agent Auth and require a personal LangSmith key or browser sign-in for Studio; other service principals cannot own user OAuth grants. Agent-owned opaque connections resolve from `MDA_DEV_<SLUG>`.

The OAuth catalog supplies provider endpoints, methods, default scopes, and authorization parameters — not your app's client credentials. Use `--auth-method`, repeatable `--scope` / `--allowed-scope`, and `--authorization-param` for overrides; `--scope` replaces rather than extends catalog defaults.

## Middleware

Middleware wraps model calls, tool calls, and lifecycle hooks. Order is explicit in the list; MDA never infers it. Use prebuilt LangChain middleware or author your own (see [[langchain-middleware]]).

```python
from langchain.agents.middleware import ModelCallLimitMiddleware, PIIMiddleware
from managed_deepagents import define_deep_agent

agent = define_deep_agent(
    name="support-agent",
    model="anthropic:claude-sonnet-4-6",
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        ModelCallLimitMiddleware(run_limit=50),
    ],
)
```

Middleware is the right place for PII handling, rate limits, retries, model fallbacks, dynamic model selection, and tool-call monitoring.

## Sandboxes

A sandbox gives the agent an isolated filesystem and shell. `mda init` scaffolds one; **delete the `sandbox/` directory to opt out**, which is right for an agent that only needs its prompt, tools, and memory.

```python
# sandbox/__init__.py
from managed_deepagents import define_sandbox

sandbox = define_sandbox(
    idle_ttl_seconds=600,
    default_timeout=600,
)
```

```ts
// sandbox/index.ts
import { defineSandbox } from "managed-deepagents";

export const sandbox = defineSandbox({
  idleTtlSeconds: 600,
  defaultTimeout: 600,
});
```

Sandbox reuse is managed as one sandbox per durable thread. Omit `scope`; the legacy value `"thread"` is tolerated, but `"agent"` is rejected. Set at most one bake base: `snapshot_name`, `snapshot_id`, or `docker_image`. For a private Docker image, add `registry` and name the password environment variable; do not put the password in source.

The agent works through `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, and `execute`. Use `instructions.md` to say where it should work and what it must not touch. `mda delete` also deletes the managed sandboxes.

During `mda dev`, if the provider is unavailable the runtime falls back to a local temp directory and prints the path. That fallback is for development only — verify sandbox behavior in a dev deployment.

## Schedules

One schedule per file under `schedules/`, each exporting a named `schedule`. The file name becomes the schedule name.

```python
# schedules/daily_digest.py
from managed_deepagents import define_schedule

schedule = define_schedule(
    cron="0 8 * * 1-5",
    timezone="America/Los_Angeles",
    prompt="Summarize what you learned yesterday and list open questions.",
)
```

Define **exactly one** of `prompt` (turned into a user message) or `input` (a structured LangGraph input). `cron` must be a standard five-field expression; without `timezone`, crons run UTC.

Schedules use ephemeral threads by default — a fresh thread per run, deleted afterward. Pass `thread={"mode": "persistent", "id": "..."}` only when runs should accumulate durable thread state. Set `deliver_to` to post results through a configured Slack channel.

Declarations are extracted at compile time **without running your code**: use literals and top-level literal constants only. No env vars, function calls, or `**kwargs`.

`mda deploy` reconciles schedules after the deployment is live — it deletes MDA-owned crons and recreates them from the current files, so deleting a file and redeploying removes the cron. **`--no-wait` skips reconciliation entirely**, so never use it when adding, changing, or removing schedules.

## Channels

A channel connects the agent to an external messaging service: inbound events start runs, and responses go back to the same conversation. **Slack is the only supported provider.** One channel per file under `channels/`, each exporting a named `channel`.

```python
# channels/slack.py
from managed_deepagents import channels

channel = channels.slack()
```

The file name sets the channel name and its inbound route — `channels/slack.py` receives events at `POST /channels/slack/events`. Names must be unique; never name a file `channels/channel.py`.

Channel-originated runs expose `runtime.channel` to tools and middleware, carrying the normalized event and conversation address plus methods to post and update messages. Ordinary HTTP runs and scheduled runs have no originating channel, so `runtime.channel` is absent.

Slack setup needs a project-root `slack-app-manifest.json` and `SLACK_SIGNING_SECRET` + `SLACK_BOT_TOKEN` in `.env`. Treat the manifest as the source of truth; files generated under `.mda/` are build artifacts and must not be committed. `runtime.channel` never exposes the bot token.

A channel *receives* messages that start runs. It is not the same as giving the agent Slack *tools* for initiating operations — a project may want either or both.

Channel threads are owned by their source conversation, while credentials and store access remain scoped to the delivering caller. When upgrading from a version that owned channel threads by the first principal, existing Slack conversations cannot migrate; start a new conversation or thread after redeploying.

## Evals

MDA evals are [Harbor](https://www.harborframework.com/docs/tasks) evals. `evals/` is the canonical authored dataset; put complete Harbor tasks directly under `evals/<task>/`. `.mda/evals/` is generated and must not be edited or committed.

```bash
mda evals init -i
```

`mda evals init` initializes the workspace and prints the pinned `harbor run` handoff; it does not run trials. `mda evals compile` is now an internal Harbor plugin entrypoint, so do not tell users to invoke it. Harbor needs Docker for its default environment and **does not read `.env`** — export the LangSmith, model, and tool variables in the shell that runs Harbor. Verifiers write a numeric reward to `/logs/verifier/reward.txt` or metrics to `/logs/verifier/reward.json`. For deeper eval design, see [[eval-engineering]].

## CLI reference

| Command | Use |
| --- | --- |
| `mda init <name>` | Scaffold a project. Fails if the destination exists. |
| `mda build [path]` | Compile into a managed LangGraph app without deploying. |
| `mda dev [path]` | Compile and run the local dev server in LangSmith Studio. |
| `mda deploy [path]` | Compile, sync Context Hub, upload, deploy, reconcile schedules. |
| `mda logs [path]` | Tail Agent Server logs for a deployed agent. |
| `mda delete [path]` | Delete a deployment and the LangSmith resources it created. Alias: `destroy`. |
| `mda connections create\|list\|get\|delete\|catalog` | Manage workspace-scoped opaque secrets and OAuth registrations. Alias: `connection`. |
| `mda channels init slack` | Add a Slack channel declaration to the current project. Alias: `channel`. |
| `mda evals init` | Initialize the Harbor eval workspace and print the run handoff. Alias: `eval`. |

Key flags:

- `init`: `-i` / `--interactive`, `--model SPEC`, `--instructions TEXT`, `--instructions-file PATH`, `--memory agent|none`, `--no-sandbox`, `-c` / `--channel slack`
- `build`: `--out OUT` (defaults to `<path>/.mda/build`; only a missing, empty, or prior MDA build directory is accepted)
- `dev`: `--port`, `--hostname`, `--no-browser`, `--no-reload`, `--tunnel`
- `deploy`: `--name`, `--deployment-type dev|prod`, `--workspace-id`, `--no-wait`, `--context-strategy`, `--wait-timeout-seconds`
- `connections`: `--project PATH` plus verb-specific secret and OAuth flags
- `logs`: `--name`, `--lines`, `--level`, `--follow` / `--no-follow`, `--workspace-id`
- `delete`: `--name`, `--workspace-id`, `--yes`

The installed package selects the language: the PyPI `mda` scaffolds Python and the npm `mda` scaffolds TypeScript. It does not infer language from the current directory. `mda dev` requires `uv` for Python and resolves the LangGraph dev server itself.

> `mda delete` is destructive and removes the deployment plus its LangSmith resources. **Confirm with the user before running it, and never pass `--yes` unprompted** — that flag exists to skip the confirmation you should be getting.

## Deploy and Context Hub

Authentication uses `LANGSMITH_API_KEY` from the project `.env` or shell. In an interactive terminal with no key found, `mda deploy` can prompt for a key or use browser sign-in; browser sign-in caches a short-lived personal token on the machine rather than writing it to `.env`. Use `--workspace-id` or `LANGSMITH_WORKSPACE_ID` when the key requires workspace selection.

`mda deploy` routes local inputs to different managed surfaces:

```text
instructions.md + skills/**   -> Context Hub deploy-owned context
.env                          -> deploy auth + non-reserved hosted secrets (never archived)
project source                -> .mda/build archive -> hosted deployment
schedules/**                  -> LangSmith cron jobs, after the deployment is live
```

Non-reserved `.env` entries — provider keys, tool credentials, database URLs — are forwarded as hosted deployment secrets. Reserved platform variables such as `LANGSMITH_API_KEY` authenticate or configure the deploy and are not uploaded as user-managed secrets. For deployment secrets, `mda deploy` deliberately does **not** copy values from the process environment: put the provider or tool key in the project `.env`, or configure it as a LangSmith workspace secret. The shell remains appropriate for local `mda dev`.

Context Hub holds `/instructions.md` and `/skills/**` (deploy-owned, resynced each deploy) and `/memories/agent/**` (runtime-owned, preserved across deploys).

### Deploy from GitHub

LangSmith can deploy an MDA project from a connected GitHub repository. Select the repository, branch or tag, and the repo-relative project directory containing `agent.py` or `agent.ts`; `langgraph.json` is generated and should not be committed. The platform runs the hidden `mda prepare` build step to compile the project, sync instructions and skills to Context Hub, bake `sandbox/setup.sh`, and reconcile schedules and channels. Enable build-on-push when revisions should rebuild automatically.

For GitHub-sourced deployments, the repository is authoritative for deploy-owned Context Hub content. Edit `instructions.md` and `skills/**` in Git and rebuild rather than treating the Hub copy as independently editable. Supply runtime credentials through the deployment's secrets or secret references; the build does not consume a repository `.env`. Preview builds compile and bake but do not reconcile schedules or channels.

`mda prepare` is platform-internal and hidden from CLI help. Never ask a user to run it manually.

Troubleshooting: `no agent entry file found` → add `agent.py` at the root. 401/403 → the key's workspace lacks beta access. Context Hub conflict → re-run the deploy. Build over 200 MB → remove generated artifacts. `BUILD_FAILED` / `DEPLOY_FAILED` → open the printed URL and read the revision logs.

## Human-in-the-loop

Pause before sensitive tool calls with `interrupt_on`, and gate filesystem paths with `permissions`:

```python
agent = define_deep_agent(
    name="support-agent",
    model="anthropic:claude-sonnet-4-6",
    tools=[refund_customer],
    interrupt_on={"refund_customer": True},
)
```

`interrupt_on` applies the same behavior as LangChain's human-in-the-loop middleware; see [[langgraph-human-in-the-loop]] for approve/edit/reject semantics. Interrupts need durable thread state, and the managed runtime owns the checkpointer, so no extra setup is required.

Respond to interrupts in Studio during `mda dev`. On a deployed agent, resume through the Agent Server/LangGraph API with a `Command(resume=...)` payload; `mda deploy` prints the Agent Server URL.

## Gotchas

- **`name=` is required** in `define_deep_agent` / `defineDeepAgent`. A definition without it fails.
- **Model IDs need the provider prefix**: `anthropic:claude-sonnet-4-6`, not a bare model name. Python uses `google_genai:`, TypeScript uses `google-genai:`, and Gateway uses `provider/model`.
- **Do not set managed fields** (`backend`, `store`, `checkpointer`, `memory`, `skills`, system prompt) in the agent definition.
- **Memory is opt-in via `memory.py`**, not a constructor argument. `disable_memory` is legacy — declare or delete `memory.py` instead.
- **MCP declarations live at `tools/mcp.*`.** Export `mcp` from `defineMcp({ servers: ... })` / `define_mcp(servers=...)`. `connectors.mcp`, `connectors/mcp.*`, and `mcpServers` are deprecated 0.7.x compatibility surfaces, not the pattern for new code.
- **Connections are workspace-scoped.** A connection slug is not private to one agent, and `mda connections list` lists the workspace, not only the current deployment.
- **Restart `mda dev` after adding a managed file.** New `memory.py`, `identity.py`, `tools/mcp.py`, `schedules/`, or `channels/` declarations are discovered at compile time, not by hot reload.
- **`--no-wait` skips schedule reconciliation** and exits before `DEPLOYED`.
- **Schedule declarations must be static literals** — the compiler extracts them without running your code.
- **`.env` is never archived**, and `.gitignore` must keep it out of version control. Do not write live keys into it on a user's behalf. Shell-only provider keys work for local dev but are not persisted into a deployment.
- **The installed package selects Python or TypeScript.** Do not claim `mda init` infers language from nearby manifests.
- **`--gateway` was removed.** Configure a Gateway-backed model explicitly instead of using the former scaffold flag.
- **The SDK moves quickly.** Verify flags with the installed `mda --help` and authoring surfaces against the installed package. Use `define_sandbox(...)`, not `sandboxes.langsmith(...)`; `identity.py` is scaffolded by default; and `mda prepare` plus `mda evals compile` are internal entrypoints.
