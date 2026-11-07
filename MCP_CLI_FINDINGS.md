# MCP and CLI findings for skill review

Review notes for branch `feat/skill-tool-guidance`, based on `skill-restructure`
at `32c04ab`. This file explains how the bundled MCP servers and the LangSmith
CLI behave at runtime, what the coding agent actually sees, and why the skill
edits on this branch take the shape they do. Observations were made on
2026-11-06/07 against the live servers and `langsmith` CLI 0.3.13. Treat this
file as review context; drop it before merge if it should not ship.

## Summary

- The plugin bundles two read-only documentation MCP servers. Before this
  branch, no skill named their tools or explained how to sequence them; only
  `langsmith-agent-ia` used the LangSmith CLI.
- In Claude Code, the agent sees MCP **server instructions** and **tool names**
  at session start; full tool descriptions and schemas load only when a tool is
  fetched. The docs server already explains its own mechanics in detail, so
  skills should not repeat them. Skills should carry what the servers cannot:
  which server to use for what, cross-server order, precedence, and fallback.
- The docs MCP also serves an auto-generated `langchain` skill resource that
  contradicts this repo's Deep Agents-first default. The server's instructions
  tell agents to read it.
- LangSmith skills should treat the CLI as an external dependency: check it is
  installed and authenticated, pin the workspace, parse JSON output, and defer
  to `--help` for flags.

## The bundled MCP servers

`.mcp.json` registers two remote HTTP servers. Claude Code loads `.mcp.json`
from the plugin root by default; `.codex-plugin/plugin.json` points Codex to
the same file. The root `mcp.json` (agent-plugins.org schema) duplicates the
config with `"type": "streamable-http"` instead of `"http"`.

| Server | Endpoint | Tools | Server instructions |
| --- | --- | --- | --- |
| `langchain-docs` | `https://docs.langchain.com/mcp` (Mintlify-hosted) | `search_docs_by_lang_chain`, `query_docs_filesystem_docs_by_lang_chain`, `submit_feedback` | Yes, about 1,100 characters |
| `langchain-reference` | `https://reference.langchain.com/mcp` | `search_api`, `get_symbol` | None |

What each tool does, from its own description:

- `search_docs_by_lang_chain`: semantic search over guides; returns excerpts
  with page links. Its description tells the agent to read full pages through
  the filesystem tool.
- `query_docs_filesystem_docs_by_lang_chain`: a read-only virtual filesystem of
  the docs (`rg`, `cat`, `head`, `tree`, `jq`, and similar). Pages are read as
  `<url-path>.mdx`. It also mounts the LangSmith platform and Agent Server
  OpenAPI specs. Its description (about 3,900 characters) already covers the
  workflow: search first, never guess paths, calls are stateless, output is
  capped at 30 KB.
- `submit_feedback`: sends a report to the docs team. It is the only tool that
  sends anything outbound.
- `search_api` and `get_symbol`: symbol search and full signature, parameters,
  and examples from the API reference. Descriptions are one line each.

All tools are read-only except `submit_feedback`. None require authentication.

## What the coding agent sees at runtime

In Claude Code, with tool search on by default:

| When | What enters context |
| --- | --- |
| Session start | Each server's `instructions` text, always |
| Session start | Tool **names** only, in a deferred list |
| When the agent fetches a tool | That tool's full description and input schema |
| When a skill triggers | The skill's `SKILL.md` body; its `description` is present from session start |

The `langchain-docs` instructions say to prefer server content over prior
knowledge, cite results, read the server's skill resources when relevant, and
use `submit_feedback` for documentation problems. `langchain-reference` sends no
instructions, so before the agent fetches its tools it sees only the names
`search_api` and `get_symbol`.

Other hosts may load full schemas up front; this was not verified for Codex.
`npx skills` installs register no MCP servers, so those agents depend on each
skill's fallback (llms.txt indexes, installed source, CLI help).

### What is and is not duplicative

Duplicative, and therefore left out of the skills:

- How to read a docs page, path rules, and the search-then-read pattern within
  `langchain-docs`. The tool description already teaches this.
- What each tool returns.

Not duplicative, and therefore added:

- Tool names. Before fetching, names are all the agent has, and naming them in
  the skill helps it pick the right deferred tool.
- **Cross-server order**: guides for the intended pattern, then the reference
  for exact contracts, then the installed package version. No server states
  this.
- **Precedence**: the reference is authoritative for signatures; the installed
  version wins over current docs; this skill wins on architecture.
- **Consent** before `submit_feedback`, because it sends content outside the
  session.

## The Mintlify skill resource

`langchain-docs` exposes one MCP resource, `mintlify://skills/langchain`. It is
an auto-generated `SKILL.md` of about 11,000 characters. Its instructions tell
the agent to "read the relevant resources when they apply to the task."

The resource conflicts with `langchain-build-agent`:

- It presents `create_agent()` as the way to build agents and sends
  planning, filesystem, and subagent needs to Deep Agents. This repo makes Deep
  Agents the default for any new tool-calling agent.
- Its example uses `model="openai:gpt-4"`, an outdated model of the kind
  `SKILLS_PHILOSOPHY.md` says to avoid.

This branch adds one line to `langchain-build-agent` saying the skill wins on
architecture and the docs win on API details. The durable fix is upstream:
align or remove the Mintlify resource, or change the server's instruction to
read it.

## Tool naming across hosts

Anthropic's skill guidance recommends fully qualified MCP tool names. In a
Claude Code plugin, tools are named `mcp__plugin_<plugin>_<server>__<tool>`,
for example
`mcp__plugin_langchain-skills_langchain-docs__search_docs_by_lang_chain`. The
prefix differs in other hosts, and users who connected the docs server
themselves may have named it differently (for example `docs-langchain`).

The skill bodies therefore refer to tools as `<server>` → `<tool>`, which reads
correctly in any host. Only `allowed-tools` frontmatter uses the full Claude
Code names. Other hosts ignore names that do not match.

`allowed-tools` in Claude Code pre-approves tools for the turn in which the
skill is invoked; it does not restrict which tools are available. Verify the
exact names with `/mcp` after installing the plugin.

## The LangSmith CLI

The plugin does not install or authenticate the CLI; `SKILLS_PHILOSOPHY.md`
states this. Before this branch, no user-facing setup text mentioned the CLI.

Every command cited in `langsmith-agent-ia` exists in CLI 0.3.13:

- `agents list` and `agents retrieve --agent-id <id> --include runtime_bindings`.
  `agents list` never embeds bindings.
- `sessions resolve --kind AGENT --id <id> --environment <ENV>`, which returns
  the session ID that project-scoped commands need.
- `evaluators rule list --project-id <id>` and `projects list`.

Other CLI facts relevant to skills:

- `langsmith auth info` shows authentication state without printing secrets.
  `langsmith auth token` prints the OAuth token; skills should never call it.
- Global flags include `--format json`, `--workspace`, `--profile`, and
  `--api-url`.
- `LANGSMITH_PROJECT` acts as a default project for trace and run queries. That
  is why name-based `--project` lookups can silently target the wrong place,
  as the skill already warns.
- `runs list`, `runs export` (JSONL), `threads list`, and `threads get` support
  trace review for evals.
- `https://docs.langchain.com/langsmith/cli` is the **LangGraph** CLI page. The
  LangSmith CLI page is `https://docs.langchain.com/langsmith/langsmith-cli`.

## Review findings by skill, before this branch

| Skill | MCP use | CLI use | Gap |
| --- | --- | --- | --- |
| `langchain-build-agent` | Generic: "guides MCP", "API-reference MCP" | None | No server or tool names, no cross-server order, no `submit_feedback` policy |
| `langsmith-agent-ia` | One fallback mention; hardcoded doc URLs | Good: specific, verified commands and pitfalls | No install or auth preflight, no JSON guidance, tool policy scattered through prose |
| `langchain-eval-engineering` | None | None | Traces come from an unspecified source; no LangSmith export path |

Packaging observations:

- Three plugin manifests (root `plugin.json`, `.claude-plugin/`,
  `.codex-plugin/`) and two MCP configs (`.mcp.json`, `mcp.json`) must stay in
  sync. The linter runs only Claude's validator.
- No skill used `allowed-tools`.
- `config/AGENTS.md` listed model keys but not the LangSmith CLI.

## Changes on this branch

1. **`langchain-build-agent`**
   - Names the docs and reference tools and sets a three-step order: pattern,
     then contract, then installed version.
   - Adds the architecture-precedence line and requires consent before
     `submit_feedback`.
   - Pre-approves the four read-only docs tools in `allowed-tools`.
     `submit_feedback` is not pre-approved.
2. **`langsmith-agent-ia`**
   - Adds a Tools section: check the CLI exists, check auth and workspace with
     `auth info`, pass `--workspace`, use `--format json`, and defer to
     `--help` for flags.
   - Requires the user to approve each create, update, attach, archive, or
     delete.
   - Pre-approves only read-only inventory commands.
   - Points feature lookups to `langchain-docs`, with the links as fallback,
     and removes the duplicated tool-policy prose.
3. **`langchain-eval-engineering/references/discovery.md`**
   - For LangSmith traces, sample with `runs` or `threads` and export with
     `runs export`.
   - Resolve agent environments to session IDs instead of passing project
     names.
   - Keep exported user data out of Tasks.
4. **`config/AGENTS.md`**: states that the plugin does not install the CLI and
   gives the install link and authentication options.

`uv run scripts/lint_skills.py` passes with 0 blocking findings and 0 warnings.

## Open questions and unverified items

- **Live testing.** The edited skills have not been run on realistic requests.
  Per `SKILLS_PHILOSOPHY.md`, check trajectories: does the agent go docs, then
  reference, then installed version, and does it run the CLI preflight once
  rather than every turn?
- **Rule matching.** Unverified whether `Bash(langsmith agents list *)` also
  matches the bare command with no arguments.
- **Codex.** Unverified whether Codex loads MCP tool schemas up front, which
  would affect context cost.
- **Repo split.** The README routes broader LangSmith work to
  `langsmith-skills`. If more CLI-backed LangSmith skills land here, consider a
  shared Tools block convention: MCP sequence, CLI preflight, fallback.
- **Config drift.** Consider consolidating or linting the duplicated manifests
  and MCP configs.
- **Upstream.** Raise the Mintlify skill resource with the docs team.

## Sources

- [Claude Code: Extend Claude Code](https://code.claude.com/docs/en/features-overview): context cost by feature, deferred MCP schemas, the Skill + MCP pattern
- [Claude Code: Skills](https://code.claude.com/docs/en/skills): `allowed-tools`, plugin path variables, `!` injection limits, portability of frontmatter fields
- [Claude Code: Plugin manifest reference](https://code.claude.com/docs/en/plugins-reference): `.mcp.json`, `bin/`, `userConfig`
- [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices): fully qualified MCP names, not assuming tools are installed
- [plugin-dev `mcp-integration` skill](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/mcp-integration/SKILL.md): plugin MCP tool naming, pre-allowing specific tools
- Live `initialize`, `tools/list`, and `resources/list` calls against both MCP endpoints, and `langsmith --help` output from CLI 0.3.13
