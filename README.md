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
including Deep Agents Code, Claude Code, Cursor, and Windsurf, the skills can
also be installed without the plugin via
[`npx skills`](https://github.com/vercel-labs/skills).

## Installation

### Plugin install (recommended)

The plugin bundles the skills with the official LangChain documentation and
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

#### Deep Agents Code

```bash
dcode plugin marketplace add langchain-ai/langchain-skills
dcode plugin install langchain-skills@langchain-skills
```

These commands install from the repository's default branch. To test an
unmerged branch, add its local checkout as a Claude Code marketplace source or
use Codex's `--ref` option when adding the marketplace. Deep Agents Code also
accepts a local marketplace directory.

#### Updates

Plugin updates use the same marketplace source as the initial install. After a
new release, start a new agent session to load the updated skills.

- **Claude Code:** Open `/plugin` → **Marketplaces**, select
  `langchain-skills`, and choose **Enable auto-update**. Claude Code leaves
  auto-update off for third-party marketplaces until you enable it. For an
  immediate update, run `/plugin marketplace update langchain-skills`.
- **Codex local install:** Run
  `codex plugin marketplace upgrade langchain-skills` to refresh the Git
  marketplace and its installed plugin. Local Git marketplace installs do not
  currently have a documented auto-update setting.
- **Managed ChatGPT/Codex workspace:** A workspace admin can import this GitHub
  marketplace from **Admin → Plugins**. Imported marketplaces sync daily, and
  admins can select **Sync now** for an immediate refresh.
- **Deep Agents Code:** The plugin opts in to background updates. After an
  update, run `/reload` or start a new session. Users can disable background
  updates in their Deep Agents Code configuration.

Each release that changes a bundled skill or plugin file increases the plugin
version. CI checks that the versions in `plugin.json`, both compatibility
manifests, and `pyproject.toml` agree and that changed plugin content has a new
version. A new version on `main` automatically creates a GitHub release with
generated release notes. Skills-only installs follow their own update paths:

- **`npx skills`:** Run `npx skills update`, then start a new agent session.
- **Cloned checkout, default linked install:** Run `git pull` in the checkout,
  then start a new agent session. Existing linked skills update immediately;
  rerun the installer to add newly introduced skills. Keep the checkout at the
  same path so the installed links remain valid.
- **Cloned checkout, copied install:** Run `git pull`, rerun the installer with
  `--copy --force` (or `-Force` on Windows), then start a new agent session.

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
CLI help to verify implementation details.

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
To link skills to a specific agent:

```bash
# Claude Code
npx skills add langchain-ai/langchain-skills --agent claude-code --skill '*' --yes --global

# Codex
npx skills add langchain-ai/langchain-skills --agent codex --skill '*' --yes --global

# GitHub Copilot (including Copilot in VS Code)
npx skills add langchain-ai/langchain-skills --agent github-copilot --skill '*' --yes --global

# Deep Agents Code
npx skills add langchain-ai/langchain-skills --agent deepagents --skill '*' --yes --global
```

Codex also supports installing repository-hosted skills with its built-in skill installer; see the [official Codex skills documentation](https://developers.openai.com/codex/skills/).

`npx skills` installs the skills but does not register MCP servers. Allow web
access to official documentation or rely on installed package source, types,
and CLI help when working offline.

---

### Install from a cloned checkout

Alternatively, clone the repo and use an installer. On macOS/Linux, it links
the skills to the checkout by default. Use `--copy` when the checkout
will not remain on the machine. The installers do not register the
documentation MCP servers:

```bash
# Install for Claude Code in the current project (default)
./install.sh

# Install for Claude Code in a specific project
./install.sh ~/my-project

# Install for Codex or Cursor
./install.sh --codex ~/my-project
./install.sh --cursor ~/my-project

# Install for Deep Agents Code
./install.sh --dcode ~/my-project

# Install globally
./install.sh --global

# Install into a custom Deep Agents Code agent with a bundled persona
./install.sh --deepagents --global
```

On Windows, PowerShell copies skills by default. Use `-Link` to link them
instead; Windows Developer Mode or an elevated shell may be required:

```powershell
.\install.ps1 -Project C:\path\to\my-project -Agent codex -Yes
.\install.ps1 -Global -Agent dcode -Link -Yes
```

Deep Agents Code may ask you to trust a linked skill whose checkout is outside
the project. Use a copied install for headless sessions that cannot show that
prompt.

| Flag / Argument | Description |
|------|-------------|
| `DIRECTORY` | Target project directory (default: current directory, ignored with `--global`) |
| `--claude` | Install for Claude Code (default) |
| `--codex`, `--cursor` | Install skills for Codex or Cursor |
| `--dcode` | Install for the default Deep Agents Code agent |
| `--deepagents` | Install for a custom Deep Agents Code agent named `langchain_agent` |
| `--global`, `-g` | Install globally instead of current directory |
| `--copy` | Copy skills instead of linking to the checkout |
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

For the current inventory, browse the [skills directory](skills/) or list the
skills in your agent. Remove superseded skill folders from older installations
so the agent does not keep loading outdated guidance.
