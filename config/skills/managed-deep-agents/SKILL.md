---
name: managed-deep-agents
description: "INVOKE THIS SKILL when building, testing, or deploying Managed Deep Agents in LangSmith. Walks a user through their first agent end to end — interviewing them about what they want to build, mapping it onto what MDA can actually do, then scaffolding and deploying it with the mda CLI. Routes to the official docs page for each capability: instructions, skills, tools, MCP, connections, middleware, sandboxes, browser use, memory, identity, subagents, schedules, channels, runtime, Context Hub, deploy, and evals."
---

# Managed Deep Agents

## Overview

Managed Deep Agents (MDA) is a hosted runtime for code-first Deep Agents in LangSmith. You author an agent in Python or TypeScript, test it locally with `mda dev`, and deploy it with `mda deploy`. It runs the open-source Deep Agents harness (see [[deep-agents-core]]) on LangSmith Agent Server, and adds managed sandboxes, browsers, memory, connections, schedules, and channels as project-file declarations.

The core idea is that **an agent is a directory**. A file's location determines its role, and the CLI compiles that directory into a managed LangGraph app.

MDA is in **public beta** on LangSmith Cloud and BYOC data planes.

## The docs are the source of truth

This skill stays thin on purpose. It tells you *what to build and where it goes*; the docs tell you *exactly how*. **Before writing a capability's file, fetch its docs page** from the [feature map](#feature-map) and follow it.

- Fetch the language-specific Markdown page: `https://docs.langchain.com/langsmith/<lang>/managed-deep-agents-<page>.md`, where `<lang>` is `python` or `javascript`. These pages contain only that language's examples.
- Load pages progressively — only the ones the current step needs.
- The full index is at `https://docs.langchain.com/llms.txt`.
- If the docs, this skill, and the installed package disagree, trust `mda --help` and the installed package's types, then the docs, then this skill.
- If you cannot fetch pages (no network), say so, work from this skill and the installed package, and tell the user which pages to check.

## When to use

Use this skill when the user wants to build a Deep Agent in code and run it on LangSmith without operating their own server, or to add a capability to an existing MDA project.

Use a standard LangSmith Deployment instead (see [[langgraph-cli]], `langgraph deploy`) when the user needs custom server routes, a custom LangGraph auth handler, application code around the agent, their own backend/store/checkpointer, or a Python `state_schema`. To convert an existing `create_deep_agent` project, follow the `migrate` page.

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

Then ask only the follow-ups that the answers raise:

- Does it need to remember anything between conversations — shared knowledge, or per-person preferences?
- Does it need to reach a private API, or a third-party account on the user's behalf?
- Should anything require a human to approve before it happens?
- Does it need to write files, run code, or use websites that have no API?

Stop asking once you can name the capabilities. Two or three questions is usually enough.

## 2. Check the answer against the limits

Check the request against **[What MDA cannot do](#what-mda-cannot-do)**. If part of it is out of scope, say so in one sentence, offer the nearest supported thing, and keep going with the rest. Do not quietly build a smaller agent and present it as what they asked for.

## 3. Map the answer onto capabilities

Use the [feature map](#feature-map) to turn each need into a file, then read that file's docs page.

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

Follow the `quickstart` page. Scaffold with flags that match the plan:

```bash
uvx --from managed-deepagents mda init research-assistant --model openai:gpt-5.5 --no-sandbox
cd research-assistant && uv sync
```

TypeScript: `npx managed-deepagents init research-assistant --model openai:gpt-5.5 --no-sandbox`, then `npm install`. Run `mda` from inside the project (`uv run mda …` / `npx mda …`).

Add **one** capability at a time and confirm each works before the next. Do not create files the plan did not call for: a `sandbox/` directory turns on a sandbox (`mda init` scaffolds one unless `--no-sandbox`), and a root `browser.py` turns on a browser.

## 6. Handle keys without touching their secrets

`mda init` writes a `.env` with empty placeholders. Fill in the *names* the project needs and let the user paste the *values*:

- Do not write live credential values into `.env`, copy keys from other projects, or echo key values.
- Confirm `.gitignore` covers `.env` and `.env.*` — `mda init` does this already.

The project needs `LANGSMITH_API_KEY` and its model provider key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, …) in `.env`, the shell, or LangSmith workspace secrets. Outside GCP US, set `LANGSMITH_ENDPOINT` before the first deploy (see `deploy`).

## 7. Run it locally, then deploy

```bash
uv run mda dev       # compiles, opens LangSmith Studio
uv run mda deploy    # syncs Context Hub, uploads, waits for DEPLOYED
```

Have the user send a message in Studio (or `mda chat` in the terminal) and confirm the agent calls its tool before deploying. `mda deploy` prints the deployment dashboard URL.

## What MDA cannot do

| Limit | Consequence |
| --- | --- |
| LangSmith Cloud and BYOC only | No self-hosted or hybrid MDA. The default Serverless deployment type needs GCP SaaS; elsewhere use `--deployment-type dedicated`. |
| No public management API | Create and update agents with `mda`. Do not invent a REST create/update flow. |
| Channels are Slack and HTTP | One Slack channel per deployment. Other services go through an HTTP channel adapter. GitHub and Linear channels are experimental. |
| Agent memory is deployment-shared | Every caller can read and write `/memories/agent/`. Per-person memory is the user layer and needs person identity. |
| No custom auth handler or routes | Use the built-in identity providers (LangSmith API key, Supabase, JWT, or your backend). |
| Workspace members see all threads | Per-user privacy holds against end users, not LangSmith workspace members. |
| One agent entry per project | Use `subagents=` for delegation. |
| Schedule files are static literals | Use the runtime schedules API for dynamic schedules. |
| Remote MCP only | Streamable HTTP or SSE; no stdio servers. |
| Build archive capped at 200 MB | Large fixtures or model weights fail the deploy. |
| Managed fields are runtime-owned | Do not set `backend`, `store`, `checkpointer`, `memory`, `skills`, or `system_prompt`. |

## Project layout

```text
my-agent/
  agent.py | agent.ts              # Required: exports the named `agent`
  instructions.md                  # System prompt -> Context Hub
  skills/<name>/SKILL.md           # On-demand procedures -> Context Hub
  tools/                           # Authored tools the agent imports
    mcp.py | mcp.ts                # Remote MCP servers (named `mcp`)
  middleware/                      # Authored middleware the agent imports
  identity.py | identity.ts        # Who may call the deployment
  memory.py | memory.ts            # Opt-in agent/user memory
  browser.py | browser.ts          # Opt-in browser
  channels/<name>.py               # Slack or HTTP channels
  schedules/<name>.py              # Managed cron schedules
  sandbox/__init__.py | index.ts   # Managed sandbox (+ optional setup.sh)
  pyproject.toml | package.json    # Dependencies
  .env                             # Auth + runtime secrets, never archived
  evals/<task>/                    # Harbor tasks, not deployed
```

Only the agent entry is required. See `project-structure` for what each path enables.

## Define the agent

The entry returns a definition, not a compiled graph. The runtime compiles it with `create_deep_agent`.

```python
# agent.py
from managed_deepagents import define_deep_agent

agent = define_deep_agent(name="research-assistant", model="openai:gpt-5.5")
```

```ts
// agent.ts
import { defineDeepAgent } from "managed-deepagents";

export const agent = defineDeepAgent({ name: "research-assistant", model: "openai:gpt-5.5" });
```

`name` is required: an inline string matching `[a-zA-Z][a-zA-Z0-9_-]*`. It is the graph ID and default deployment name. For parameters, model IDs, LLM Gateway, and per-run factories, read `agent-definition`.

## Feature map

Each row: what the feature is for, where it lives, and the `<page>` to fetch.

| Use it when the agent… | Feature | Lives in | Docs `<page>` |
| --- | --- | --- | --- |
| needs its model and core options | Agent definition | `agent.py` | `agent-definition` |
| needs different config per caller, repo, or tenant | Agent factory | `agent(runtime)` | `agent-definition` |
| needs always-on behavior, tone, rules | Instructions | `instructions.md` | `instructions` |
| follows a procedure only for some tasks | Skills | `skills/<name>/` | `skills` |
| calls your API, database, or service | Custom tools | `tools/` | `tools` |
| uses tools from a remote MCP server | MCP | `tools/mcp.*` | `mcp-connectors` |
| needs web search with no extra API key | Parallel search | `tools/mcp.*` | `search` |
| needs an API key or acts as the user in GitHub, Notion, … | Connections | `connections.get(...)` | `connections` |
| needs PII redaction, limits, retries, logging | Middleware | `middleware/` | `middleware` |
| asks a human before acting | Human-in-the-loop | `interrupt_on=` | `tools` |
| posts a Slack form and waits for the answer | Agent-owned interrupts | a tool | `agent-owned-interrupts` |
| delegates focused or long-running work | Subagents (sync or async) | `subagents=` | `subagents` |
| writes files, runs code or shell commands | Sandbox | `sandbox/` | `sandboxes` |
| uses websites with no API, logs in | Browser | `browser.py` | `browser-use` |
| learns shared knowledge or per-person preferences | Memory | `memory.py` | `memory` |
| must keep each signed-in user's chats private | Identity | `identity.py` | `identity` |
| runs on a timer, or sets reminders itself | Schedules | `schedules/` | `schedules` |
| lives in Slack | Slack channel | `channels/slack.py` | `channels-slack` |
| is triggered by a webhook from another system | HTTP channel | `channels/<name>.py` | `channels-http` |
| reads the caller, thread, or sandbox in code | Runtime | tools / middleware | `runtime` |
| is called from your own web or Python app | Custom frontend | client code | `custom-frontend` |
| is called as a tool from Claude Code / MCP clients | MCP endpoint | `<API URL>/mcp` | `mcp-endpoint` |
| is tested against tasks as it changes | Evals (Harbor) | `evals/` | `evals` |

Workflow pages: `quickstart`, `local-development`, `deploy` (regions, BYOC, secrets, Serverless vs Dedicated), `context-hub` (Hub edits vs project files), `cli` (every command and flag), `migrate`.

## CLI at a glance

`mda init`, `build`, `dev`, `chat`, `deploy`, `logs`, `delete` (alias `destroy`), `connections`, `channels init`, `evals init`. Confirm flags with `mda <command> --help`; see `cli` for details.

> `mda delete` removes the deployment and the LangSmith resources it created. **Confirm with the user first, and never pass `--yes` unprompted.** The same applies to `mda deploy --yes`.

`mda prepare` and `mda evals compile` are internal; never ask a user to run them.

## Gotchas

These are the mistakes agents make most often. Check the linked page for current details.

- **`name=` is required** and must be an inline string, even inside a factory.
- **Model IDs need a provider prefix** (`openai:gpt-5.5`). Gateway models use `langsmith:provider/model`. Do not pass the removed `mda init --gateway`.
- **Do not set managed fields** in the definition; use the project files instead.
- **Memory uses layers**: `define_memory(agent=MemoryLayer())` / `defineMemory({ agent: memoryLayer() })`. String `scope="agent"` is rejected.
- **User memory needs a signed-in person.** The default LangSmith API-key identity never mounts it.
- **MCP servers go in `tools/mcp.*`** with a named `mcp` export from `define_mcp(servers=...)`. The old `connectors` API was removed.
- **Agent-owned connections belong to a deployment**: create them after the first successful deploy.
- **Restart `mda dev` after adding a managed file** (`memory`, `identity`, `browser`, `tools/mcp`, `schedules/`, `channels/`).
- **`--no-wait` skips schedule reconciliation** and cannot be used with a Slack channel.
- **`runtime.channel` is deprecated**; use `runtime.thread.origin.channel`.
- **Do not set sandbox `scope`**; sandboxes are always one per thread.
- **`.env` is never archived** and must stay out of version control.
