---
name: deepagents-deploy
description: "Deploy deep agents with the deepagents CLI — configure via deepagents.toml (model, sandbox), place AGENTS.md/skills/mcp.json alongside it, and ship to LangGraph Platform with deepagents deploy."
---

# deepagents deploy

## Overview

The Deep Agents CLI includes a `deploy` command that packages and deploys your agent to LangSmith Deployment in a single step. Define your agent's configuration in a `deepagents.toml` file and deploy directly from your project directory.

## When to use

Use this skill when the user wants to:
- Deploy a deep agent to LangGraph Platform (`deepagents deploy`)
- Understand or edit a `deepagents.toml`
- Set up the convention-based project layout (AGENTS.md, skills/, mcp.json)
- Configure a sandbox provider for code execution

## Commands

```bash
# Deploy to LangGraph Platform
deepagents deploy

# Use a specific config file
deepagents deploy --config path/to/deepagents.toml
```

By default, the command looks for `deepagents.toml` in the current directory.

Prereq: Install `langgraph-cli[inmem]` (`pip install 'langgraph-cli[inmem]'` or `uv add "langgraph-cli[inmem]"` depending on your package manager) and a LangSmith API key in the environment (or `.env` at the project root).

## Project layout

The deploy command uses a convention-based layout. Place these files alongside your `deepagents.toml` and they are automatically discovered:

```
my-agent/
├── deepagents.toml          # agent configuration (required)
├── AGENTS.md                # agent memory/context (required)
├── .env                     # environment variables (optional)
├── mcp.json                 # MCP server config (optional, http/sse only)
└── skills/                  # skill definitions (optional)
    ├── code-review/
    │   └── SKILL.md
    └── data-analysis/
        └── SKILL.md
```

| File/directory | Purpose | Required |
|---------------|---------|----------|
| `AGENTS.md` | Persistent context for the agent (project conventions, instructions, preferences). Always loaded at startup. | Yes |
| `skills/` | Directory of skill definitions. Each subdirectory contains a `SKILL.md`. | No |
| `mcp.json` | MCP server configuration. Only `http` and `sse` transports are supported in deployed contexts. | No |
| `.env` | Environment variables (API keys, secrets). Automatically picked up if present. | No |

## `deepagents.toml` reference

Only the `[agent]` section is required. The `[sandbox]` section is optional and defaults to no sandbox.

### Minimal config

```toml
[agent]
name = "my-agent"
model = "anthropic:claude-sonnet-4-6"
```

The `name` field is the only required value in the entire configuration file. Everything else has defaults.

### `[agent]` (required)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | string | (required) | Name for the deployed agent. Used as the assistant identifier in LangSmith. |
| `model` | string | `"anthropic:claude-sonnet-4-6"` | Model identifier in `provider:model` format. |

Supported model providers:

| Provider | Prefix | Example |
|----------|--------|---------|
| Anthropic | `anthropic:` | `anthropic:claude-sonnet-4-6` |
| OpenAI | `openai:` | `openai:gpt-4o` |
| Google | `google:` | `google:gemini-2.5-pro` |
| Amazon Bedrock | `bedrock:` | `bedrock:anthropic.claude-sonnet-4-6` |
| Azure OpenAI | `azure:` | `azure:gpt-4o` |
| Fireworks | `fireworks:` | `fireworks:accounts/fireworks/models/llama-v3p1-70b-instruct` |
| OpenRouter | `openrouter:` | `openrouter:anthropic/claude-sonnet-4-6` |

### `[sandbox]` (optional)

Configure the isolated execution environment where the agent runs code. Sandboxes provide a container with a filesystem and shell access. Only needed for code execution or skill script execution.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | string | `"none"` | Sandbox provider. Determines where the container runs. |
| `template` | string | `"deepagents-deploy"` | Provider-specific template name for the sandbox environment. |
| `image` | string | `"python:3"` | Base Docker image for the sandbox container. |
| `scope` | string | `"thread"` | Sandbox lifecycle: `"thread"` (one per conversation) or `"assistant"` (shared across all conversations). |

Supported sandbox providers:

| Provider | `provider` value | Description |
|----------|-----------------|-------------|
| None | `"none"` | No sandbox. Default. |
| LangSmith | `"langsmith"` | Managed sandbox hosted by LangSmith. Currently in private preview. |
| Daytona | `"daytona"` | Daytona cloud sandboxes. |
| Modal | `"modal"` | Modal serverless containers. |
| Runloop | `"runloop"` | Runloop dev sandboxes. |

### Full config example

```toml
[agent]
name = "coding-agent"
model = "anthropic:claude-sonnet-4-5"

[sandbox]
provider = "langsmith"
template = "coding-agent"
image = "python:3.12"
```

## Examples

A content writing agent (no code execution needed):

```toml
[agent]
name = "content-writer"
model = "anthropic:claude-sonnet-4-6"
```

A coding agent with a LangSmith sandbox:

```toml
[agent]
name = "coding-agent"
model = "anthropic:claude-sonnet-4-5"

[sandbox]
provider = "langsmith"
template = "coding-agent"
image = "python:3.12"
```

## Gotchas

- **MCP stdio transports are not supported** in deployed contexts — only `http` and `sse`. Convert stdio servers to http/sse before deploying.
- **`AGENTS.md` is required** — the deploy command expects it alongside `deepagents.toml`.
- **`.env` is auto-discovered** — place it alongside `deepagents.toml` at the project root. The deploy command picks it up automatically if present.
- **Sandbox scope** — `"thread"` (default) gives each conversation its own sandbox. `"assistant"` shares one sandbox across all conversations, useful for long-lived workspaces like a cloned repo.
