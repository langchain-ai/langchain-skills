# Managed Deep Agents capabilities

Python examples are shown first. TypeScript uses the same names in camelCase from `managed-deepagents` (`defineMemory`, `memoryLayer`, `defineIdentity`, `defineMcp`, `defineSandbox`, `defineBrowser`, `defineSchedule`, `channels.slack`, `channels.http`) and exports each declaration with `export const <name> = ...`.

## Memory

Durable memory is **off by default** and comes in two independent layers. Declare only the layers you need in a root `memory.py` / `memory.ts`:

```python
# memory.py
from managed_deepagents import MemoryLayer, define_memory

memory = define_memory(agent=MemoryLayer())
```

```ts
// memory.ts
import { defineMemory, memoryLayer } from "managed-deepagents";

export const memory = defineMemory({ agent: memoryLayer() });
```

| Layer | Mount | Belongs to | Use for |
| --- | --- | --- | --- |
| `agent` | `/memories/agent/` | The deployment, shared by every caller | Team conventions, reusable procedures |
| `user` | `/memories/user/` | The authenticated person running the agent | Personal preferences, caller-specific context |

- Omitting a layer disables it; deleting `memory.py` turns memory off. Turning it off deletes nothing in Context Hub.
- `AGENTS.md` at the root of a mount is **hot memory**, loaded into every model call — keep it compact. Other files are **cold memory**, read on demand.
- The agent reads and writes with `read_file`, `edit_file`, `write_file`. Writes elsewhere, including elsewhere under `/memories/`, are not durable.
- `define_memory(scope="agent")` (string scope) is rejected. Do not mix legacy object `scope` with layers.

**User memory needs a person.** It mounts only when identity resolves an authenticated person: Supabase, a JWT provider, backend identity, a Slack user, or a verified Studio user. The default LangSmith API-key identity is a service and never gets user memory.

Default access when no factory selects layers:

| Run source | Agent memory | User memory |
| --- | --- | --- |
| Slack one-to-one DM | Allowed | Allowed |
| Slack channel or group DM | Allowed | Denied |
| Direct API run | Allowed | Denied |
| Studio, verified user | Allowed | Allowed |

To decide per run, return `memory=define_memory(user=MemoryLayer())` (or `memory=None`) from an [agent factory](#per-run-agent-factory) based on context your app sends. `allow(context)` callbacks are deprecated since 0.9 and rejected in factory-selected memory.

> **Warning — agent memory is shared by every caller, and every caller can influence it.** Never store personal data, customer data, credentials, API keys, or tokens there. Treat memory content as untrusted notes: it must never grant authority, change tool permissions, or bypass approvals. When both layers exist, tell the agent in `instructions.md` which facts go where.

To review writes before they land, add `FilesystemPermission(operations=["write"], paths=["/memories/**"], mode="interrupt")` (from `deepagents`) to `permissions=`. Hot-memory auto-loading is not covered by permission rules.

`mda dev` stores memory locally under `.mda/__contexthub__`; it is separate from deployed memory.

## Identity

`identity.py` controls who may call the deployment. `mda init` scaffolds the LangSmith API-key default:

```python
# identity.py
from managed_deepagents import auth, define_identity

identity = define_identity(auth=auth.langsmith_api_key())
```

Callers send a workspace LangSmith API key as `x-api-key`. Anyone with the key reaches the deployment and may see the same threads. For per-user private threads:

| Provider | Declaration | Client sends |
| --- | --- | --- |
| Supabase | `auth.supabase(project_ref="your-project-ref")` (or `url=` for a custom domain) | `Authorization: Bearer <access_token>` |
| Other JWT (Auth0, Okta, Clerk, Entra ID) | `{"issuer": ..., "audience": ..., "discover": True, "claims": {"user": "sub"}}` (or `jwks=` URL instead of `discover`) | `Authorization: Bearer <access_token>` |
| Your backend | `auth="backend"` | `x-mda-ingress-secret` + `x-mda-user-id` |

- Supabase: send the publishable (anon) key only from the client to sign in; never send a LangSmith key in this mode. Adding identity later does not backfill owner metadata on existing threads.
- Backend: put a random `MDA_INGRESS_SECRET` in `.env`; deploy fails preflight without it. Any holder of the secret can act as any user — keep it server-side only. Keep `x-mda-user-id` stable.
- MDA rejects custom LangGraph auth handlers. To scope by tenant, choose the user ID accordingly (org ID to share, person ID for privacy) and check org claims in tools.
- Auth failures return 401; cross-user access returns 403/not found.

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

Provider server-side tools can be passed inline where supported (for example `{"type": "web_search"}` for OpenAI), avoiding a separate search key. Tools read deployment secrets from environment variables; prefer [connections](#connections) for API keys and OAuth.

## MCP servers

Declare remote MCP servers in `tools/mcp.py` / `tools/mcp.ts`. Do not import the declaration into `agent.py`; MDA discovers the named `mcp` export.

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

- Transports: `"http"` (Streamable HTTP) or `"sse"`. Stdio is not supported.
- Tools are exposed as `{server}__{tool}` by default (`prefix_tool_name_with_server_name`). `include_tools` / `exclude_tools` use raw names.
- Other options: `headers`, `default_tool_timeout` (seconds in Python, ms in TS), `automatic_sse_fallback`, `reconnect`, `throw_on_load_error`.
- `connectors.mcp(...)`, `connectors/`, and `mcpServers` were removed in 0.10.
- LangSmith Parallel search (GCP US, Plus/Startup plans): add a server with `"url": "https://api.smith.langchain.com/v1/managed-tools/servers/parallel/mcp"` and set `LANGSMITH_WORKSPACE_ID` in `.env`.

## Connections

A connection is a workspace-scoped slug that holds credentials. Resolve it at runtime, never by passing a user ID:

```python
from managed_deepagents import connections

api_key = await connections.get("organization-tavily", {"type": "agent"})
notion_token = await connections.get("engineering-notion", {"type": "user"})
```

- `agent` — one credential owned by the deployment. Missing → the run fails.
- `user` — the caller's own OAuth grant. Missing → a `credential_authorization_required` interrupt, which Slack and Studio handle; custom frontends render it themselves.

```bash
uv run mda connections catalog
uv run mda connections create organization-tavily --secret-from-env TAVILY_API_KEY
uv run mda connections create frontend-github --oauth github --client-id "$GITHUB_CLIENT_ID" --secret-from-env GITHUB_CLIENT_SECRET
uv run mda connections create engineering-notion --mcp https://mcp.notion.com/mcp
uv run mda connections list
```

- Modes: opaque secret (`--secret-from-env`, `--secret-from-file`, stdin, prompt; always agent-owned), general OAuth (`--oauth <service>` or `--authorize-url` + `--token-url`), MCP OAuth (`--mcp <url>`, or the bare slug when the project declares that user-owned MCP server). Do not mix modes.
- `--authorize` signs in once for an agent-owned OAuth grant; `--grant-type client_credentials` gets an agent-owned token without a browser.
- `--scope` replaces catalog defaults; also `--allowed-scope`, `--authorization-param`, `--token-param`, `--auth-method`, `--token-request-header`.
- Agent-owned credentials belong to the project's deployment: create them after the first successful `mda deploy`, and run `create` again from each project that reuses the slug. `no agent connection is set for slug` means this deployment owns none.
- `mda dev` reads agent-owned opaque connections from `MDA_DEV_<SLUG>` (uppercase, hyphens → underscores). Test user-owned connections against a deployment.
- The CLI does not create user-owned API-key slots; Slack and Studio collect only OAuth grants per user.

## Sandbox

A sandbox gives the agent an isolated filesystem and shell. It is enabled while `sandbox/` exists; delete the directory to opt out.

```python
# sandbox/__init__.py
from managed_deepagents import define_sandbox

sandbox = define_sandbox(
    idle_ttl_seconds=600,
    default_timeout=600,
)
```

- One sandbox per durable thread. Do not pass `scope`; it fails the build.
- **Snapshot recipe:** `sandbox/setup.sh` runs once (`bash -e`) on deploy and `mda dev`, and new threads clone the result. It is rebuilt when the script changes. Forwarded `.env` values are available while it runs but are not inherited by thread sandboxes; never write secrets to disk there.
- **Bake base:** at most one of `snapshot_name`, `snapshot_id`, or `docker_image`. For a private image add `registry={"url": ..., "username": ..., "password_env": "GHCR_TOKEN"}`.
- **Proxy:** `proxy_config={"rules": [...], "access_control": {"allow_list": [...]}}` injects headers outside the sandbox. Header values can be `workspace_secret` templates or connections: `bearer(connections.get("github", {"type": "user"}))` or `basic(username, ref)`.
- The agent works through `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`, and `execute`.
- Tools and middleware reach the same sandbox via `runtime.backend` (`ls`, `read`, `write`, `edit`, `delete`, `grep`, `glob`, `execute`, `upload_files`, `download_files`, plus `a`-prefixed async variants). It is `None` without a sandbox — always guard.
- In `mda dev`, an unavailable provider falls back to a local temp directory. Verify sandbox behavior on a deployment.

## Browser

A root `browser.py` / `browser.ts` (not inside `browser/` or `sandbox/`) gives the agent a LangSmith browser:

```python
# browser.py
from managed_deepagents import define_browser

browser = define_browser(scope="thread", idle_ttl_seconds=600)
```

- `scope="thread"` (default): one browser per conversation. `scope="user"`: one per authenticated person, sharing cookies and logins across their threads.
- Tools: `browser_snapshot`, `browser_run`, `browser_screenshot`, `browser_handoff`. Saving screenshots needs a sandbox.
- `browser_handoff(reason)` gives a person control for login, CAPTCHA, or 2FA; Studio renders it, custom clients must render the artifact. Links expire after 15 minutes and must stay private.
- Prefer a direct API plus a connection when one exists.

## Subagents

```python
agent = define_deep_agent(
    name="research-assistant",
    model="openai:gpt-5.5",
    subagents=[
        {"name": "reviewer", "description": "Reviews drafts.", "system_prompt": "List concrete fixes."},
        {"name": "researcher", "description": "Researches in the background.", "system_prompt": "Report findings.", "async": True},
    ],
)
```

- Sync subagents run via `task`. They inherit `model`, `tools`, `permissions`, `interrupt_on` unless set; use only their own prompt, middleware, and `response_format`; load only the skills they list (`"/skills/"` for all); get no memory.
- Async subagents (0.10+) run as their own graph (`<agent>--<subagent>`), share the caller's sandbox and trace, and report back automatically. The agent gets `start_async_task`, `check_async_task`, `update_async_task`, `cancel_async_task`, `list_async_tasks`, and an async `general-purpose` subagent.
- Declare async subagents literally (fixed `name` and `async`), not from a loop or helper. Do not set `graph_id`, `url`, `headers`, or `runnable`. Options: `update_strategy`, `notify_parent`, `webhook`, `mode="fork"`.

## Schedules

One declaration per file under `schedules/`; the file name is the schedule name.

```python
# schedules/daily_digest.py
from managed_deepagents import define_schedule

schedule = define_schedule(
    cron="0 8 * * 1-5",
    timezone="America/Los_Angeles",
    prompt="Summarize yesterday and list open questions.",
)
```

- Exactly one of `prompt` or `input`. Five-field cron; UTC without `timezone`.
- Ephemeral thread per run by default. `thread={"mode": "persistent", "id": "<uuid>"}` needs an existing thread UUID created in Studio first.
- `deliver_to={"channel": "slack", "to": {"type": "provider_conversation", "conversation_id": "C0123456789"}}` posts results to Slack.
- Literals and top-level literal constants only — no env vars, function calls, or `**kwargs`.
- `mda deploy` recreates MDA-owned crons after `DEPLOYED`; `--no-wait` skips this. `mda dev` runs schedules locally unless `--no-schedules`.

**Runtime schedules** (0.9+): tools can call `await runtime.schedules.create(owner={"type": "user"|"agent"}, cron=... | at=..., prompt=... | input=..., new_thread=..., paused=...)`, plus `list`, `get`, `update`, `delete`. Created from a channel run, the schedule replies to that conversation. Limit: 20 runtime schedules per owner per agent (`MDA_MAX_USER_SCHEDULES`, `MDA_MAX_AGENT_SCHEDULES`). Scheduled runs cannot create more schedules.

## Channels

One channel per file under `channels/`, each exporting a named `channel`. Never name a file `channels/channel.py`. A channel *starts runs and receives replies*; Slack or other MCP *tools* are separate.

### Slack

```python
# channels/slack.py
from managed_deepagents import channels

channel = channels.slack(
    name="Support Agent",
    description="Answers order questions",
    icon="support-agent.png",
)
```

- Add with `mda init --channel slack` or `mda channels init slack`. One Slack channel per deployment.
- `mda deploy` provisions the Slack app: it asks whether LangSmith creates and manages it, you create one from a manifest, or you bring one (`MDA_SLACK_BOT_TOKEN`, `MDA_SLACK_SIGNING_SECRET` without a terminal). Authorize when prompted; the agent DMs you after the first deploy. No hand-written manifest or `SLACK_*` runtime secrets are needed.
- Options: `background_color`, `trigger_mode` (`"mention"` default, `"thread"`, `"all"`; replaces deprecated `trigger_on_all_messages`), `allow_bot_triggers`, `reactions` (`"eyes"` default, `False`, a short name, or a callable).
- With a sandbox, uploads land in `/workspace/attachments/` and the agent sends files with `attach_file(path)` / `upload_files(paths)` (200 MiB each).
- Redeploy after changing name, description, or icon. `mda channels setup` (experimental) re-runs setup without deploying.

### HTTP

```python
# channels/orders.py
from managed_deepagents import channels

from lib.orders import parse, post, verify

channel = channels.http(provider="orders", verify=verify, parse=parse, post=post)
```

- Endpoint: `POST https://<deployment-url>/channels/<name>/events` (file name, not provider).
- `verify(request)` must check a signature against `request.raw_body` — the route has no platform auth.
- `parse(request)` returns `{"type": "message", "message": {"user_id", "thread_id", "target", "content"}}` or `{"type": "ignore"}`, optionally with a Starlette `response`. `thread_id` must be a UUID (map external IDs with `uuid.uuid5`).
- Optional async `post` delivers the final reply to the verified `target`.
- Read channel secrets from env vars, not `connections.get`.

## Runtime

Tools receive `ManagedToolRuntime` (alias `ManagedDeepAgentRuntime`), middleware `ManagedRuntime`, factories `ManagedServerRuntime`. Managed additions:

- `runtime.server_info.principal` — verified caller (`id`, `kind` = `person` | `service` | `channel`, `claims`). Use it for authorization; `runtime.context` is caller-supplied data, not identity.
- `runtime.thread` — `id`, `origin` (channel conversation and latest `sender`), `participants`. `runtime.thread.origin.channel.post({"type": "content", "content": "..."})` sends an extra message. `runtime.channel` is deprecated.
- `runtime.backend` — the thread's sandbox, or `None`.

On channel runs `runtime.context` is `None`.

## Per-run agent factory

Export a function as `agent` to choose configuration per run:

```python
# agent.py
from typing import TypedDict

from managed_deepagents import ManagedServerRuntime, define_deep_agent


class AppContext(TypedDict, total=False):
    repository: str


def agent(runtime: ManagedServerRuntime[AppContext]):
    execution = runtime.execution_runtime
    context = execution.context if execution is not None else None
    payments = context is not None and context.get("repository") == "payments-service"
    return define_deep_agent(
        name="code-helper",
        model="openai:gpt-5.5",
        skills=["./skills/python-service" if payments else "./skills/typescript-web"],
        context_schema=AppContext,
    )
```

- Selectable fields (factory only): `instructions` (`""` clears), `skills` (`[]` clears), `mcp` (`[]` clears), `sandbox` (`None` disables), `memory` (`None` disables), `browser` (`None` disables; keep the root `browser.py`).
- `execution_runtime` is `None` when Agent Server inspects the graph, and context is `None` on channel runs — always handle the fallback.
- Keep it pure and repeatable: no side effects, the same interrupting middleware in every branch, an inline `name`, and every model integration package installed.
- Callers pick the branch with `client.runs.create(..., context={"repository": "payments-service"})`.
