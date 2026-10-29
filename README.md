# LangChain Skills

> **⚠️** — This project is in early development. APIs and skill content may change.

Agent skills for building agents with LangChain, LangGraph, and Deep Agents.

> For LangSmith-specific trace and dataset workflows, use [langsmith-skills](https://github.com/langchain-ai/langsmith-skills).

## Supported Coding Agents

These skills can be installed via [`npx skills`](https://github.com/vercel-labs/skills) for any agent that supports the [Agent Skills specification](https://skills.sh), including Claude Code, Cursor, Windsurf, and more.

## Installation

### Plugin install (recommended)

The plugin bundles all skills with the official LangChain guide and API-reference
MCP connections. The skills still work when an MCP connection is unavailable.

#### Claude Code

```bash
/plugin marketplace add langchain-ai/langchain-skills
/plugin install langchain-skills@langchain-skills
```

#### Codex

```bash
codex plugin marketplace add langchain-ai/langchain-skills
codex plugin add langchain-skills@langchain-skills
```

Plugin installation registers these read-only documentation endpoints:

- `langchain-docs` — guides and product documentation at
  `https://docs.langchain.com/mcp`
- `langchain-reference` — API reference at
  `https://reference.langchain.com/mcp`

The user's coding-agent or workspace policy may still disable MCP servers. In
that case, the installed skills fall back to official web documentation,
installed package metadata and types, CLI help, and their lightweight local
references.

### Skills-only install

Using [`npx skills`](https://github.com/vercel-labs/skills):

**Local** (current project):

```bash
npx skills add langchain-ai/langchain-skills --skill '*' --yes
```
**Global** (all projects):

```bash
npx skills add langchain-ai/langchain-skills --skill '*' --yes --global
```
To link skills to a specific agent (e.g. Claude Code):

```bash
npx skills add langchain-ai/langchain-skills --agent claude-code --skill '*' --yes --global
```

`npx skills` installs the skills but does not register MCP servers. Each skill
contains the same docs/runtime fallback policy, so this remains a supported
installation path.

---

### Install Script (Claude Code & Deep Agents CLI only)

Alternatively, clone the repo and use the install script:

```bash
# Install for Claude Code in current directory (default)
./install.sh

# Install for Claude Code in a specific project directory
./install.sh ~/my-project

# Install for Claude Code globally
./install.sh --global

# Install for Deep Agents CLI in a specific project directory
./install.sh --deepagents ~/my-project

# Install for Deep Agents CLI globally (includes agent persona)
./install.sh --deepagents --global
```

| Flag / Argument | Description |
|------|-------------|
| `DIRECTORY` | Target project directory (default: current directory, ignored with `--global`) |
| `--claude` | Install for Claude Code (default) |
| `--deepagents` | Install for Deep Agents CLI |
| `--global`, `-g` | Install globally instead of current directory |
| `--force`, `-f` | Overwrite skills with same names as this package |
| `--yes`, `-y` | Skip confirmation prompts |

## Usage

After installation, set your API keys:

```bash
export OPENAI_API_KEY=<your-key>      # For OpenAI models
export ANTHROPIC_API_KEY=<your-key>   # For Anthropic models
```

Then run your coding agent from the directory where you installed (for local installs) or from anywhere (for global installs).

### Eval Engineering

To install only the langchain-eval-engineering skill:

```bash
npx skills add langchain-ai/langchain-skills --skill langchain-eval-engineering --yes
```

Or ask Codex: “Install the `langchain-eval-engineering` skill from `langchain-ai/langchain-skills`.”

Eval tasks require [Harbor](https://www.harborframework.com/docs). Run Harbor locally with Docker or use a supported cloud environment.

Then ask your coding agent:

```text
Use the langchain-eval-engineering skill to create a new eval Task for this project. Review the current repository and existing evals. Traces for this agent can be found here [optional Tracing Project/Location].
```

## Available Skills (5)

- **langchain-build-agent** - Latest guidance for building or modifying applications with Deep Agents, LangGraph, and LangChain: architecture, middleware, memory, human review, composition, and retrieval. Uses current documentation for implementation details.
- **langchain-managed-deep-agents** - Managed Deep Agents: deploy with the CLI, use the SDKs, stream runs, connect MCP tools, and build React `useStream` UIs
- **langchain-langgraph-cli** - CLI lifecycle: scaffold, dev, build, deploy, langgraph.json config
- **langchain-eval-engineering** - Design and audit Harbor Tasks while building reusable project World knowledge with human review
- **langchain-swarm** - Dispatch independent work items in parallel and aggregate the results

The framework, Deep Agents, LangGraph, memory, human-in-the-loop, composition,
middleware, and retrieval skills are consolidated into `langchain-build-agent`.
When updating an existing skills-only installation, remove the superseded skill
folders so the coding agent does not continue loading their older guidance.
