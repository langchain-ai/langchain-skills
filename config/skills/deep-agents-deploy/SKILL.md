---
name: deepagents-deploy
description: Build, run locally, and deploy deep agents with the `deepagents` CLI — configure an agent via `deepagents.toml` (model, memories, skills, tools, MCP, sandbox), iterate with `deepagents deploy dev`, then ship to LangGraph Platform with `deepagents deploy`.
---

# deepagents dev & deploy

## Overview

`deepagents` is a CLI for building stateful agents configured by a single `deepagents.toml` file. The CLI bundles the agent's system prompt, memories (AGENTS.md, user preferences), skills, Python tools, and MCP servers into a LangGraph deployment package. You iterate locally with `deepagents deploy dev` and ship the same bundle to LangGraph Platform with `deepagents deploy`.

There is no hand-written graph entrypoint — the bundler generates `deploy_graph.py`, `langgraph.json`, and `pyproject.toml` from the config.

## When to use

Use this skill when the user wants to:
- Scaffold a new deep agent project
- Understand or edit a `deepagents.toml`
- Run an agent locally for iteration (`deepagents deploy dev`)
- Deploy an agent to LangGraph Platform (`deepagents deploy`)
- Add skills, Python tools, or MCP servers to an agent
- Choose between `hub`- and `store`-backed agent memories, or configure a sandbox provider

## Commands

```bash
# Scaffold a starter deepagents.toml in cwd
deepagents deploy init [--force]

# Bundle + run locally on a LangGraph dev server (default http://localhost:2024)
deepagents deploy dev [--config ./deepagents.toml] [--port 2024]

# Bundle + deploy to LangGraph Platform
deepagents deploy [--config ./deepagents.toml] [--dry-run]
```

`--dry-run` writes the generated artifacts to a temp directory and prints the paths — useful for inspecting what will be shipped without actually deploying.

Prereq: Install `langgraph-cli[inmem]` (`pip install 'langgraph-cli[inmem]'` or `uv add "langgraph-cli[inmem]"` depending on your package manager) and a LangSmith API key in the environment (or `.env` referenced via `[deploy].env_file`).

## `deepagents.toml` reference

Minimal config:

```toml
[agent]
name = "my-agent"
model = "anthropic:claude-sonnet-4-5"
system_prompt = "You are a helpful assistant."
```

Full config with all sections:

```toml
[agent]
name = "my-agent"                      # unique identifier, also the hub repo name
model = "anthropic:claude-sonnet-4-5"  # any LangChain model string
system_prompt = "..."

# Shared across all users of this agent.
[agent_memories]
backend = "hub"                        # "hub" (LangSmith Prompt Hub) | "store" (LangGraph store)
sources = ["./AGENTS.md"]              # files bundled as agent context

# Per-user, always store-backed, namespaced (agent, user_id, "user_memories").
[user_memories]
sources = ["./preferences.md"]

[skills]
sources = ["./skills/"]                # directory of skill subdirs

[tools]
python_file = "./tools.py"             # module with @tool functions
functions = ["search", "write_file"]   # optional; auto-discovered if omitted

[mcp]
config = "./.mcp.json"                 # HTTP/SSE MCP servers only (no stdio)

[sandbox]
provider = "langsmith"                 # none | langsmith | agentcore | daytona | modal | runloop
template = "coding-agent"
image = "python:3.12"

[deploy]
python_version = "3.12"
dependencies = ["langchain-anthropic", "langchain-tavily"]
env_file = ".env"
```

## Memory backends

- **`backend = "hub"`** — `[agent_memories].sources` are pushed to a LangSmith Prompt Hub repo named after `[agent].name`. Read at runtime via `HubBackend`. Good default for shared context you want versioned outside the deployment.
- **`backend = "store"`** — sources are embedded in `_agent_memories_seed.json` and seeded into the LangGraph persistent store on first invocation under namespace `(agent_name, "agent_memories")`.
- **`[user_memories]`** — always store-backed, always per-user. The agent can rewrite these files (e.g. update `preferences.md` as it learns the user's style).

## Sandboxes

Each thread gets one sandbox, created lazily on first tool call. `provider = "none"` runs tools in-process (no shell, no filesystem). Other providers (`langsmith`, `daytona`, `modal`, ...) give the agent an isolated environment with a persistent filesystem — required for coding agents that read/write/execute code.

## Typical workflow

1. `deepagents deploy init` in a new directory.
2. Edit `deepagents.toml`: set model, system prompt, point at `AGENTS.md` / `tools.py` / `.mcp.json` as needed.
3. `deepagents deploy dev` — iterate against a local LangGraph server. Re-run after edits to rebundle.
4. `deepagents deploy --dry-run` — inspect generated `deploy_graph.py`, `langgraph.json`, `pyproject.toml`, `_bundle.json`.
5. `deepagents deploy` — ship to LangGraph Platform.

See `examples/deploy-coding-agent/` and `examples/deploy-content-writer/` in this repo for complete working configs.

## Gotchas

- MCP stdio transports are not supported in deployed contexts — use HTTP/SSE.
- `[deploy].dependencies` must include any LangChain provider package your model string references (e.g. `langchain-anthropic` for `anthropic:...`).
- `deepagents deploy dev` re-bundles on each run; there is no hot reload inside a running session.
- Switching `[agent_memories].backend` between `hub` and `store` changes where runtime reads happen — don't flip it on a deployed agent without migrating the content.
