# LangChain Skills

> **⚠️** — This project is in early development. APIs and skill content may change.

Opinionated skills for building applications with Deep Agents, LangGraph, and
LangChain; evaluating them with LangSmith; and engineering Harbor
benchmarks. The plugin also connects to the official
documentation and API reference.

See [Skills philosophy](SKILLS_PHILOSOPHY.md) for how we decide what belongs in
a skill and keep the guidance current.

## Supported Coding Agents

For agents that support the [Agent Skills specification](https://skills.sh),
including Claude Code, Cursor, and Windsurf, the skills can also be installed
without the plugin via [`npx skills`](https://github.com/vercel-labs/skills).

## Installation

### Plugin install (recommended)

The plugin bundles all four skills with the official LangChain documentation and
API-reference MCP connections. The skills also work when MCP is unavailable.

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

These commands install from the repository's default branch. To test an
unmerged branch, add its local checkout as a Claude Code marketplace source or
use Codex's `--ref` option when adding the marketplace.

Plugin installation registers two documentation MCP servers:

- `langchain-docs` — guides and product documentation at
  `https://docs.langchain.com/mcp`
- `langchain-reference` — API reference at
  `https://reference.langchain.com/mcp`

`langchain-docs` also exposes `submit_feedback`, which sends feedback to the
documentation team; use it only with the user's agreement. The plugin does not
register LangSmith Remote MCP. Skills-only installation does not register MCP
servers.

Plugin installation loads the skills, but not `config/AGENTS.md`. That file is
copied only by `./install.sh --deepagents --global`.

#### LangSmith CLI setup (optional)

The plugin does not install or authenticate the LangSmith CLI. To let a local
coding agent query or manage an authorized LangSmith workspace, install the CLI
on the same machine using the [official CLI guide](https://docs.langchain.com/langsmith/langsmith-cli),
then authenticate with `langsmith auth login`. Choose the intended workspace
during authentication. The guide also covers self-hosted instances and profile
selection. The CLI is optional when you only need the documentation MCP or work
through the SDK.

The user's coding-agent or workspace policy may disable MCP servers. In that
case, use official web documentation, installed package source and types, and
CLI help to verify implementation details. `langchain-eval-engineering` also
retains its bundled workflow references.

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

`npx skills` installs the skills but does not register MCP servers. Allow web
access to official documentation or rely on installed package source, types,
and CLI help when working offline.

---

### Install Script (Claude Code & Deep Agents CLI only)

Alternatively, clone the repo and use the install script. This copies the four
skills but does not register the documentation MCP servers:

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

Plugin installation and public documentation access do not require model-provider
API keys. To run an application you build, configure credentials for the model
provider that application uses. LangSmith workspace actions require access to
the intended workspace through an authenticated CLI profile or SDK configuration.
Use the documentation MCPs for general product questions, the
[LangSmith CLI](https://docs.langchain.com/langsmith/langsmith-cli) for supported
workspace queries and resource operations, and the SDK for application tracing
and evaluation runs.

Run your coding agent from the directory where you installed the skills (for
local installs), or from anywhere (for global installs).

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

## Available Skills (4)

- **langchain-build-agent** - Latest guidance for building or modifying applications with Deep Agents, LangGraph, and LangChain: architecture, middleware, memory, human review, composition, and retrieval. Uses current documentation for implementation details.
- **langchain-eval-engineering** - Design and audit Harbor Tasks while building reusable project World knowledge with human review.
- **langsmith-agent-ia** - Place traces, datasets, online evaluations, and deployments under the right LangSmith agent and environment; diagnose visibility and migration issues.
- **langsmith-online-evaluation** - Design and operate production evaluations, including broad decision-model checks and optional targeted LLM judging.

For LangSmith Custom Apps, use the bundled documentation MCP and the CLI
scaffold’s generated `AGENTS.md` for the current app contract.

The framework, Deep Agents, LangGraph, memory, human-in-the-loop, composition,
middleware, and retrieval skills are consolidated into `langchain-build-agent`.
When updating an existing skills-only installation, remove the superseded skill
folders so the coding agent does not continue loading their older guidance.
Remove an older `langsmith-skills` installation when switching to this combined
plugin so its previous skill copies do not compete with the new guidance.
Remove an existing `langchain-langsmith` skill installation as well; it is no
longer bundled with this plugin.
Remove an existing `langsmith-experiment-diagnosis` skill installation too.
