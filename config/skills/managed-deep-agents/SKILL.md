---
name: managed-deep-agents
description: "INVOKE THIS SKILL when creating, deploying, running, or operating Managed Deep Agents in LangSmith. Covers deepagents-cli, the Python and TypeScript SDKs, React useStream, REST fallbacks, MCP tools, interrupts, backends, and the managed agent file tree."
---

# Managed Deep Agents

## Overview

Managed Deep Agents is a hosted runtime for creating, running, and operating Deep Agents in LangSmith. It packages the operational layer around the open-source Deep Agents harness: a versioned Context Hub agent repo, durable threads, streamed runs, MCP credential storage, managed files, and optional LangSmith sandboxes.

Use the Managed Deep Agents path when the user wants LangSmith to host and operate the agent. For self-hosted deployments, custom application routes, or the full Agent Server API surface, use a standard LangSmith Deployment via [[langgraph-cli]] instead.

## When to use

Use this skill when the user wants to:

- Deploy a Managed Deep Agent from local project files.
- Create or update a Managed Deep Agent from Python, TypeScript, or REST.
- Run an agent on a durable thread and stream output.
- Build a React chat UI with `@langchain/react` `useStream`.
- Register MCP servers, list MCP tools, or configure tool interrupts.
- Choose between Managed Deep Agents and a self-hosted LangSmith Deployment.

## Prerequisites

- Managed Deep Agents preview access in the target LangSmith workspace.
- A LangSmith API key for that workspace.
- One of the supported clients:

```bash
uv tool install "deepagents-cli>=0.2.2"
pip install managed-deepagents
npm install @langchain/managed-deepagents @langchain/react
```

Set the API key in the shell or server environment:

```bash
export LANGSMITH_API_KEY="<LANGSMITH_API_KEY>"
```

The SDKs default to `https://api.smith.langchain.com/v1/deepagents`. To use a different compatible endpoint, set `LANGSMITH_ENDPOINT` or pass `api_url` / `apiUrl` in the client.

For direct REST examples, set:

```bash
export DEEPAGENTS_BASE_URL="https://api.smith.langchain.com/v1/deepagents"
```

All REST requests authenticate with:

```text
X-Api-Key: <LANGSMITH_API_KEY>
```

Never expose a long-lived LangSmith API key in browser code. For browser apps, route requests through your own backend or provide a custom `fetch` implementation that proxies requests server-side.

## Choose an interface

| Interface | Use for |
| --- | --- |
| `deepagents-cli>=0.2.2` | Normal project-file workflow: scaffold, edit files, deploy, manage MCP servers. |
| Python SDK `managed-deepagents` | Server-side Python automation, tests, scripts, services, and streaming. |
| TypeScript SDK `@langchain/managed-deepagents` | Server-side TypeScript automation and LangGraph-compatible streaming. |
| React `useStream` | Chat UIs that should let LangGraph own thread/run/projection state. |
| REST `/v1/deepagents` | Low-level fallback when a client does not expose a field yet. |

Prefer the CLI for local agent projects. Prefer the SDKs for application code. Use REST only when you need exact request control.

## Resource groups

| Group | Purpose |
| --- | --- |
| Agents | Create, list, get, update, clone, delete, and health-check Managed Deep Agents. |
| Threads | Create, list, search, count, inspect, update, and delete durable thread state. |
| Runs | Start and stream runs on a thread. |
| MCP servers | Register, list, update, delete, and connect MCP servers. |
| MCP tools | List tools exposed by a registered MCP server for `tools.json`. |
| Auth sessions | Start and inspect OAuth authorization sessions. |

## Project file tree

The CLI uses a local project directory and deploys it into the managed Context Hub agent repo.

```text
my-agent/
  agent.json
  AGENTS.md
  tools.json
  skills/<name>/SKILL.md
  subagents/<name>/agent.json
  subagents/<name>/AGENTS.md
  subagents/<name>/tools.json
```

| File / directory | Purpose |
| --- | --- |
| `agent.json` | Agent name, description, model, backend, permissions, and optional target `agent_id`. |
| `AGENTS.md` | Main agent instructions. |
| `tools.json` | MCP-backed tools plus `interrupt_config`. |
| `skills/` | Reusable instructions and files the agent can load. |
| `subagents/` | Delegated worker definitions and optional subagent-scoped tools. |

At runtime, the agent can read and write managed files, including memory files created by the Deep Agents harness.

## Backends

New projects should use the canonical backend names from `deepagents-cli>=0.2.2`.

Use `state` when the agent does not need sandbox-specific backend behavior:

```json
{
  "backend": {
    "type": "state"
  }
}
```

Use `sandbox` when the agent needs a LangSmith sandbox for code execution, filesystem work, or long-running tasks:

```json
{
  "backend": {
    "type": "sandbox",
    "sandbox_config": {
      "scope": "thread",
      "policy_ids": ["policy-id"],
      "idle_ttl_seconds": 900,
      "delete_after_stop_seconds": 300
    }
  }
}
```

`sandbox_config.scope` must be `thread` or `agent`.

## CLI workflow

Use the CLI for most deploy workflows.

```bash
deepagents init research-assistant
cd research-assistant
```

Edit `agent.json`:

```json
{
  "name": "research-assistant",
  "description": "Research assistant that can search the web and summarize sources.",
  "model": "openai:gpt-5.5",
  "backend": {
    "type": "state"
  }
}
```

Edit `AGENTS.md` with the main instructions, then deploy:

```bash
deepagents deploy
```

Useful CLI commands:

| Command | Use |
| --- | --- |
| `deepagents --version` | Confirm `deepagents-cli>=0.2.2`. |
| `deepagents deploy --dry-run` | Print the agent payload and managed file tree without deploying. |
| `deepagents agents list` | List Managed Deep Agents in the workspace. |
| `deepagents agents get <agent_id> --include-files` | Inspect an agent and its managed files. |
| `deepagents mcp-servers add --url URL --name NAME` | Register a static-header MCP server. |
| `deepagents mcp-servers add --url URL --auth-type oauth --connect` | Register and connect an OAuth MCP server. |
| `deepagents mcp-servers tools <id|name|url>` | List tools and print a paste-ready `tools.json` snippet. |
| `deepagents mcp-servers connect <id|name|url>` | Complete OAuth for a registered OAuth MCP server. |

For shared repositories, put the target `agent_id` in `agent.json`; the CLI asks for confirmation before updating that remote agent. Use `--yes` only when the target is intentional.

## MCP tools

Tools are configured with a `tools` array and an `interrupt_config` map. The same shape is used in `tools.json` and inline SDK/REST create or update payloads.

```json
{
  "tools": [
    {
      "name": "read_url_content",
      "mcp_server_url": "https://example.com/mcp",
      "mcp_server_name": "my-tools",
      "display_name": "read_url_content"
    }
  ],
  "interrupt_config": {
    "https://example.com/mcp::read_url_content": false
  }
}
```

- `tools[].mcp_server_url` must match a registered workspace MCP server URL.
- `tools[].name` is the tool name exposed by the MCP server, not the workspace MCP-server display name.
- Use `deepagents mcp-servers tools <server>` or the SDK tool-listing methods to confirm exact tool names.
- `interrupt_config` keys use `{mcp_server_url}::{tool_name}`. Additional `::` parts are accepted for compatibility, but do not rely on them for new configs.
- Set the interrupt value to `true` to require human approval before the tool runs.

Python SDK tool listing:

```python
from managed_deepagents import Client

with Client() as client:
    tools = client.mcp_servers.list_tools(
        url="https://example.com/mcp",
        force_refresh=True,
    )
    print(tools["tools"])
```

TypeScript SDK tool listing:

```ts
import { Client } from "@langchain/managed-deepagents";

const client = new Client({ apiKey: process.env.LANGSMITH_API_KEY });
const tools = await client.mcpServers.listTools({
  url: "https://example.com/mcp",
  forceRefresh: true,
});
console.log(tools.tools);
```

## Python SDK workflow

Use the Python SDK for server-side automation and streaming.

```python
from managed_deepagents import Client

with Client() as client:
    agent = client.agents.create(
        name="research-assistant",
        description="Research assistant that can search the web and summarize sources.",
        model="openai:gpt-5.5",
        backend={"type": "state"},
        instructions=(
            "You are a careful research assistant. Search for sources, "
            "keep notes, and return concise answers with citations."
        ),
    )

    thread = client.threads.create(
        agent_id=agent["id"],
        options={
            "test_run": False,
            "skip_memory_write_protection": False,
        },
    )

    for event in client.threads.stream(
        thread["id"],
        agent_id=agent["id"],
        messages=[
            {
                "role": "user",
                "content": "Research recent approaches to agent memory and summarize the main tradeoffs.",
            }
        ],
        stream_mode=["values", "updates", "messages-tuple"],
        stream_subgraphs=True,
        user_timezone="America/Los_Angeles",
    ):
        print(event.event, event.data)
```

Async Python clients are available as `AsyncClient` with matching resource names.

## TypeScript SDK workflow

Use the TypeScript SDK for server-side automation and LangGraph-compatible streaming.

```ts
import { Client } from "@langchain/managed-deepagents";

const client = new Client({
  apiKey: process.env.LANGSMITH_API_KEY,
});

const agent = await client.agents.create({
  name: "research-assistant",
  description: "Research assistant that can search the web and summarize sources.",
  model: "openai:gpt-5.5",
  backend: { type: "state" },
  instructions:
    "You are a careful research assistant. Search for sources, keep notes, and return concise answers with citations.",
});

const thread = await client.threads.create({
  agent_id: agent.id,
  options: {
    test_run: false,
    skip_memory_write_protection: false,
  },
});

const langGraphClient = client.getLangGraphClient({ agentId: agent.id });
const stream = langGraphClient.runs.stream(thread.id, agent.id, {
  input: {
    messages: [
      {
        role: "user",
        content:
          "Research recent approaches to agent memory and summarize the main tradeoffs.",
      },
    ],
  },
  streamMode: ["values", "updates", "messages-tuple"],
  streamSubgraphs: true,
});

for await (const event of stream) {
  console.log(event.event, event.data);
}
```

The adapter translates LangGraph SDK request fields into Managed Deep Agents routes, headers, and payload fields.

## React `useStream`

For React applications, use the TypeScript SDK's LangGraph client adapter with `@langchain/react`. `useStream` owns the thread, run, and state projection behavior while the Managed Deep Agents SDK handles auth, routes, and payload translation.

```tsx
import { Client } from "@langchain/managed-deepagents";
import { useStream } from "@langchain/react";

const agentId = "<agent_id>";

const managedDeepAgents = new Client({
  // Server-only or browser-safe proxy configuration.
  // Do not ship LANGSMITH_API_KEY to browser clients.
  apiKey: process.env.LANGSMITH_API_KEY,
});

const client = managedDeepAgents.getLangGraphClient({ agentId });

export function ManagedDeepAgentStream() {
  const stream = useStream({
    client,
    assistantId: agentId,
    fetchStateHistory: false,
  });

  return (
    <section>
      <button
        type="button"
        disabled={stream.isLoading}
        onClick={() => {
          void stream.submit({
            messages: [
              { role: "user", content: "Write a short status update." },
            ],
          });
        }}
      >
        Run agent
      </button>

      {stream.messages.map((message, index) => (
        <p key={message.id ?? index}>{String(message.content)}</p>
      ))}
    </section>
  );
}
```

`stream.submit({ messages })` is the correct UI-level shape. The SDK adapter rewrites it to the Managed Deep Agents stream route as `input.messages`.

## REST fallback

Use REST when a client does not expose a field yet or when debugging raw payloads. Prefer SDK helpers in normal application code.

Create an agent:

```python
import os
import httpx

BASE_URL = os.environ["DEEPAGENTS_BASE_URL"]
HEADERS = {"X-Api-Key": os.environ["LANGSMITH_API_KEY"]}

response = httpx.post(
    f"{BASE_URL}/agents",
    headers=HEADERS,
    json={
        "name": "research-assistant",
        "description": "Research assistant that can search the web and summarize sources.",
        "runtime": {"model": {"model_id": "openai:gpt-5.5"}},
        "backend": {"type": "state"},
        "instructions": (
            "You are a careful research assistant. Search for sources, "
            "keep notes, and return concise answers with citations."
        ),
    },
)
response.raise_for_status()
agent_id = response.json()["id"]
```

Create a thread:

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

Stream a run:

```python
payload = {
    "agent_id": agent_id,
    "input": {
        "messages": [
            {
                "role": "user",
                "content": "Research recent approaches to agent memory and summarize the main tradeoffs.",
            }
        ]
    },
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

Set `Accept: text/event-stream` for raw REST streaming. `stream_mode` accepts LangGraph stream modes such as `values`, `updates`, and `messages-tuple`. `stream_subgraphs: true` emits subagent events as well as parent events.

## Human-in-the-loop interrupts

When `interrupt_config` flags a tool with `true`, the run pauses before the tool executes and emits an interrupt payload inside a `values` or `updates` event:

```json
{
  "__interrupt__": [
    {
      "value": {
        "action_requests": [
          {
            "name": "read_url_content",
            "args": { "url": "https://example.com" },
            "description": "Tool execution requires approval"
          }
        ],
        "review_configs": [
          {
            "action_name": "read_url_content",
            "allowed_decisions": ["approve", "edit", "reject", "respond"]
          }
        ]
      },
      "id": "interrupt-id"
    }
  ]
}
```

The stream closes after the interrupt is emitted. To act on it, post a follow-up run with `command.resume` on the same thread.

Python SDK resume:

```python
for event in client.threads.stream(
    thread_id,
    agent_id=agent_id,
    messages=[{"role": "system", "content": ""}],
    command={"resume": {"decisions": [{"type": "approve"}]}},
    stream_mode=["values", "updates", "messages-tuple"],
    stream_subgraphs=True,
):
    print(event.event, event.data)
```

REST resume:

```python
payload = {
    "agent_id": agent_id,
    "input": {"messages": [{"role": "system", "content": ""}]},
    "command": {
        "resume": {
            "decisions": [{"type": "approve"}]
        }
    },
    "stream_mode": ["values", "updates", "messages-tuple"],
    "stream_subgraphs": True,
}
```

The resume value must be the HITL response object `{"decisions": [...]}`, not a bare decision list. Send exactly one decision per `action_request`, in the same order.

| Decision | Shape | Effect |
| --- | --- | --- |
| Approve | `{"type": "approve"}` | Run the tool with the proposed args. |
| Edit | `{"type": "edit", "edited_action": {"name": "...", "args": {...}}}` | Run the tool with modified name/args. |
| Reject | `{"type": "reject", "message": "..."}` | Block the tool and return an error `ToolMessage` to the model. |
| Respond | `{"type": "respond", "message": "..."}` | Skip the tool and return a synthetic successful tool reply. |

Each decision `type` must be allowed by the matching `review_configs[i].allowed_decisions`.

### Resolve interrupt endpoint

`POST /v1/deepagents/threads/{thread_id}/resolve-interrupt` takes no body and returns `204`. It terminates the paused run at the interrupt; it is not an approve shortcut. Use `command.resume` on `/runs/stream` for approve, edit, reject, or respond decisions.

## When NOT to use Managed Deep Agents

Use a standard LangSmith Deployment via [[langgraph-cli]] (`langgraph deploy`) instead when you need:

- Custom application code or custom routes around the agent.
- Advanced authentication around your own app server.
- The full Agent Server API surface.
- Stronger isolation controls or maximum scalability.
- A region other than supported LangSmith Cloud regions, or self-hosted/Hybrid.

## Gotchas

- **Use `deepagents-cli>=0.2.2`** - older CLI versions generate stale backend names.
- **Use canonical backends** - new examples should use `state` or `sandbox` with `sandbox_config.scope`.
- **REST stream payloads use `input.messages`** - SDK helpers accept `messages` and normalize the request body.
- **Do not ship API keys to browsers** - proxy browser requests through your backend or custom `fetch`.
- **`PATCH` can replace nested fields wholesale** - when updating tools, pass the full desired tool set.
- **Tool names must match MCP tool names** - if `tools[].name` is wrong, the model will not see the tool.
- **List tools before wiring `tools.json`** - use the CLI or SDK tool-listing methods to avoid name mismatches.
- **Resume interrupts with `command.resume = {"decisions": [...]}`** - a bare list is invalid.
- **Resume runs still need a non-empty message list** - use `[ {"role": "system", "content": ""} ]` as a no-op message when needed.
- **`resolve-interrupt` cancels/finalizes** - it does not approve a pending action.
- **Model IDs should include provider prefix** - use `openai:gpt-5.5`, not a bare model name.
- **MCP credentials are sensitive** - avoid logging headers or raw credential payloads.
- **Deleting an agent does not delete its threads** - track and clean up threads explicitly.
- **API stability** - `/v1/deepagents` is still evolving; prefer SDK and CLI surfaces for user-facing workflows.
