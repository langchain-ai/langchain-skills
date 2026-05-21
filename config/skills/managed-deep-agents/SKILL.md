---
name: managed-deep-agents
description: "INVOKE THIS SKILL when creating, running, or operating a Managed Deep Agent against the LangSmith /v1/deepagents private-preview REST API. Covers the agent → MCP server → thread → streamed run flow, tool/interrupt configuration, and the agent file tree (AGENTS.md, skills/, subagents/, tools.json)."
---

# Managed Deep Agents

## Overview

Managed Deep Agents is an API-first hosted runtime for creating, running, and operating Deep Agents in LangSmith. It packages the operational layer around the open-source Deep Agents harness — versioned agent repo in the Context Hub, durable threads, streamed runs, managed file tree, MCP credential storage — so you don't have to stand up your own agent server.

For self-hosted deployments or full Agent Server APIs, use a standard LangSmith Deployment via [[langgraph-cli]] instead.

## When to use

Use this skill when the user wants to:
- Create or update a Managed Deep Agent (`POST` / `PATCH /v1/deepagents/agents`)
- Run an agent on a durable thread and stream the result
- Register or rotate MCP server credentials for an agent's tools
- Configure per-tool human-in-the-loop interrupts on a managed agent
- Decide between Managed Deep Agents and a self-hosted LangSmith Deployment

## Prerequisites

- A LangSmith API key for that workspace
- The HTTP client of your choice (`httpx` in Python, built-in `fetch` in JS/Node 18+)

```bash
export LANGSMITH_API_KEY="<LANGSMITH_API_KEY>"
export DEEPAGENTS_BASE_URL="https://api.smith.langchain.com/v1/deepagents"
```

All requests authenticate via the `X-Api-Key` header:

```
X-Api-Key: <LANGSMITH_API_KEY>
```

## End-to-end flow

```
1. Register MCP server(s) →  POST /v1/deepagents/mcp-servers
2. Create the agent       →  POST /v1/deepagents/agents
3. Create a thread        →  POST /v1/deepagents/threads
4. Stream a run           →  POST /v1/deepagents/threads/{thread_id}/runs/stream
5. Inspect in LangSmith   →  Traces UI
```

Each step is independent — register MCP servers once per workspace, then point any number of agents at them.

## Resource groups

| Group | Purpose |
|-------|---------|
| **Agents** (`/agents`) | Create, list, get, update (`PATCH`), and delete Managed Deep Agents. |
| **Threads** (`/threads`) | Create, search, count, and inspect durable thread state. |
| **Runs** (`/threads/{thread_id}/runs/stream`) | Start and stream runs on a thread (server-sent events). |
| **MCP servers** (`/mcp-servers`) | Register, list, rotate credentials, and delete MCP servers referenced by agent tools. |

## Agent file tree

Managed Deep Agents keeps the familiar Deep Agents project shape. Keep these in your source repo (so updates are reviewable) and submit them in `POST` / `PATCH /agents` payloads. The platform stores them as a versioned agent repo in the Context Hub, returns a `revision` on each update, and serves the tree to the agent on every run.

| File / directory | Purpose |
|------------------|---------|
| `AGENTS.md` | Agent instructions. |
| `skills/` | Skill definitions the agent can use. |
| `subagents/` | Subagent definitions for delegated work. |
| `tools.json` | Tool configuration (`tools` + `interrupt_config`). |

At runtime, the agent can read and write files — including a `/memories/` directory for durable cross-run state.

## `tools` configuration

Tools are configured with a `tools` array and an `interrupt_config` map. The same shape is used in `tools.json` and inline in agent create/update payloads:

```json
{
  "tools": [
    {
      "name": "tavily-search",
      "mcp_server_url": "https://mcp.tavily.com/mcp/",
      "mcp_server_name": "tavily",
      "display_name": "tavily-search"
    }
  ],
  "interrupt_config": {
    "https://mcp.tavily.com/mcp/::tavily-search::tavily": false
  }
}
```

- Each `tools[].mcp_server_url` must match an MCP server already registered for the workspace; credentials are attached automatically at invocation time.
- `interrupt_config` keys use the form `{mcp_server_url}::{tool_name}` (two colons, trailing slashes on the URL stripped before matching). Additional `::`-separated parts (e.g. the MCP server display name) are accepted but ignored when matching.
- Set the value to `true` to require human approval before the tool runs, `false` to allow it without interrupt.

## Step 1 — Register an MCP server

Tools that need credentials (custom MCP servers, private endpoints, any bearer-authenticated API) are registered once per workspace via `POST /v1/deepagents/mcp-servers`. The platform stores the URL and credential headers (encrypted at rest) and re-attaches them on every invocation whose `tools[].mcp_server_url` matches.

```python
import os, httpx

BASE_URL = os.environ["DEEPAGENTS_BASE_URL"]
HEADERS = {"X-Api-Key": os.environ["LANGSMITH_API_KEY"]}

response = httpx.post(
    f"{BASE_URL}/mcp-servers",
    headers=HEADERS,
    json={
        "name": "tavily",
        "url": "https://mcp.tavily.com/mcp/",
        "headers": [
            {"key": "Authorization", "value": "Bearer tvly-..."},
        ],
    },
)
response.raise_for_status()
mcp_server_id = response.json()["id"]
```

Other operations on the same resource:

| Action | Method + path |
|--------|---------------|
| List | `GET /mcp-servers` |
| Get one | `GET /mcp-servers/{mcp_server_id}` |
| Rotate credentials | `PATCH /mcp-servers/{mcp_server_id}` (replaces the **entire** `headers` array — partial diffs not supported) |
| Delete | `DELETE /mcp-servers/{mcp_server_id}` |

**Only static-header auth** (bearer tokens, custom API-key headers) is supported during preview. OAuth-backed MCP servers are planned.

## Step 2 — Create the managed agent

```python
response = httpx.post(
    f"{BASE_URL}/agents",
    headers=HEADERS,
    json={
        "name": "research-assistant",
        "description": "Research assistant that can search the web and summarize sources.",
        "runtime": {"model": {"model_id": "anthropic:claude-sonnet-4-6"}},
        "instructions": (
            "You are a careful research assistant. Search for sources, "
            "keep notes, and return concise answers with citations."
        ),
        "tools": {
            "tools": [
                {
                    "name": "tavily-search",
                    "mcp_server_url": "https://mcp.tavily.com/mcp/",
                    "mcp_server_name": "tavily",
                    "display_name": "tavily-search",
                },
            ],
            "interrupt_config": {
                "https://mcp.tavily.com/mcp/::tavily-search::tavily": False,
            },
        },
    },
)
response.raise_for_status()
agent_id = response.json()["id"]
```

Response includes the agent `id` (store it as `AGENT_ID`).

Other operations:

| Action | Method + path |
|--------|---------------|
| List | `GET /agents` |
| Get one | `GET /agents/{agent_id}` |
| Update | `PATCH /agents/{agent_id}` |
| Delete | `DELETE /agents/{agent_id}` |

**`PATCH` replaces `tools` wholesale** — to add a tool, pass the full new tool set, not just the additions. Each `PATCH` also creates a new `revision` on the agent's Context Hub repo.

**Deleting an agent does NOT cascade to its threads.** Existing threads remain queryable but starting new runs returns `502`. Track and delete threads explicitly when cleaning up.

### Supported models

Pass model identifiers in `{provider}:{model_id}` form (e.g. `anthropic:claude-sonnet-4-6`, `openai:gpt-5.4-mini`). The runtime resolves models with `init_chat_model`, so any provider supported by `init_chat_model` works.

Values **without** a colon are interpreted as references to a saved Playground configuration, not a model ID — always supply the full `{provider}:{model_id}` form when configuring a model directly.

## Step 3 — Create a thread

Threads preserve conversation and execution state for long-running work.

```python
response = httpx.post(
    f"{BASE_URL}/threads",
    headers=HEADERS,
    json={
        "agent_id": agent_id,
        "options": {
            "test_run": False,
            "skip_memory_write_protection": False,
        },
    },
)
response.raise_for_status()
thread_id = response.json()["id"]
```

## Step 4 — Stream a run

```python
payload = {
    "agent_id": agent_id,
    "messages": [
        {
            "role": "user",
            "content": "Research recent approaches to agent memory and summarize the main tradeoffs.",
        }
    ],
    "stream_mode": ["values", "updates", "messages-tuple"],
    "stream_subgraphs": True,
    "user_timezone": "America/Los_Angeles",
}

with httpx.stream(
    "POST",
    f"{BASE_URL}/threads/{thread_id}/runs/stream",
    headers={**HEADERS, "Accept": "text/event-stream"},
    json=payload,
    timeout=None,
) as response:
    response.raise_for_status()
    for line in response.iter_lines():
        if line:
            print(line)
```

Set `Accept: text/event-stream` so the client receives progress as SSE. `stream_mode` accepts the same values as the LangGraph runtime (`values`, `updates`, `messages-tuple`, etc.). `stream_subgraphs: true` emits events from subagent graphs as well as the parent.

Every run is traced in LangSmith — model calls, tool calls, subagent activity, files, and runtime state are all inspectable from the trace UI.

## JavaScript / cURL equivalents

The same flow works with `fetch` (Node 18+ or browser) or `curl`. Replace `httpx.post(url, headers=HEADERS, json=...)` with:

```javascript
const BASE_URL = process.env.DEEPAGENTS_BASE_URL;
const HEADERS = {
  "X-Api-Key": process.env.LANGSMITH_API_KEY,
  "Content-Type": "application/json",
};

const response = await fetch(`${BASE_URL}/agents`, {
  method: "POST",
  headers: HEADERS,
  body: JSON.stringify({ /* same payload */ }),
});
if (!response.ok) throw new Error(await response.text());
const { id: agentId } = await response.json();
```

For streaming, read from `response.body.pipeThrough(new TextDecoderStream()).getReader()`.

For `curl`, set `--header "X-Api-Key: $LANGSMITH_API_KEY"` and `--header 'Content-Type: application/json'`.

## When NOT to use Managed Deep Agents

Use a standard LangSmith Deployment via [[langgraph-cli]] (`langgraph deploy`) instead when you need:
- Custom application code or custom routes around the agent
- Advanced authentication
- The full Agent Server API surface
- Stronger isolation controls or maximum scalability
- A region other than US LangSmith Cloud, or self-hosted/Hybrid

## Gotchas

- **No SDK** — REST is the only supported interface. Python/JS/`useStream` SDK wrappers are in progress.
- **No rate limits during preview** — but quotas may be introduced before GA; don't design around the absence of limits.
- **`PATCH` is wholesale, not partial** — both for `agents` (`tools` field is replaced) and for `mcp-servers` (`headers` array is replaced). Always send the full new value.
- **`interrupt_config` key format** — `{mcp_server_url}::{tool_name}` with two colons. Trailing slashes on the URL are stripped before matching.
- **Model IDs must include the provider prefix** — `anthropic:claude-sonnet-4-6`, not `claude-sonnet-4-6` (the latter is treated as a Playground config reference).
- **MCP credentials are sensitive** — `headers` is omitted from response bodies for callers without invoke permission; treat list/get responses as sensitive and avoid logging them verbatim.
- **MCP auth limited to static headers** — bearer tokens and custom API-key headers only during preview. OAuth-backed registration is planned.
- **Deleting an agent does not delete its threads** — and new runs on orphaned threads return `502`. Clean up threads explicitly.
- **API stability** — routes live under `/v1/deepagents` but the surface may change in backwards-incompatible ways before GA. Breaking changes are communicated directly to preview customers.
