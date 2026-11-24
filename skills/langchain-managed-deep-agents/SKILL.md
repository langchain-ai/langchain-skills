---
name: langchain-managed-deep-agents
description: "Use when building, configuring, testing, migrating to, or deploying a Managed Deep Agent in LangSmith with the mda CLI (Python or TypeScript). Gives an overview of Managed Deep Agents and routes to the official documentation and installed CLI for current capabilities, project layout, hosting options, and syntax."
---

# Managed Deep Agents

Managed Deep Agents (MDA) is LangSmith's hosted runtime for code-first Deep
Agents in Python and TypeScript. You author an agent as a project directory and
use the `mda` CLI to develop it locally and deploy it to LangSmith Agent
Server, without building or operating the server stack yourself.

Under the hood, MDA runs the open-source Deep Agents harness (see
`langchain-build-agent`) rather than a separate framework. Instead of compiling
an agent in your own process and wiring up its infrastructure, your project
defines the agent (model and configuration, instructions, skills, tools, MCP
connectors, middleware, and subagents) alongside opt-in managed capabilities
such as sandboxes, browser use, durable memory, caller identity, channels,
schedules, and Harbor evals, plus connections whose credentials live in your
LangSmith workspace. The managed runtime compiles the agent, stores
instructions, skills, and optional durable memory in Context Hub, and hosts the
result on LangSmith Agent Server.

## When to use Managed Deep Agents

Use this skill when the user wants to build, configure, test, migrate to, or
deploy a Deep Agent with Managed Deep Agents and the `mda` CLI, or work inside
an existing MDA project.

Use the open-source Deep Agents SDK directly or a custom LangSmith Agent Server
deployment instead (see `langchain-build-agent`) when the user needs to own the
server, custom routes, surrounding application code, or custom persistence or
default backend infrastructure. To convert an existing Deep Agents project,
follow the official MDA migration guide in the docs.

Hand off to sibling skills when the task crosses into their scope:

- **`langchain-build-agent`:** choosing between Deep Agents, LangGraph, and
  LangChain, or building a self-managed agent.
- **`langchain-eval-engineering`:** designing and building Harbor eval tasks
  for the agent.
- **`langchain-agent-tracing`, `langchain-agent-monitoring`, and
  `langchain-agent-experiments`:** tracing, production monitoring, and offline
  LangSmith experiments.

## Read the docs before building

This skill stays intentionally thin. Managed Deep Agents evolves quickly: its
hosting options, supported capabilities, project-file conventions, SDK APIs,
and CLI flags all change across releases. **Do not rely on memory for what MDA
supports, what limits apply, which files enable a capability, or exact
syntax.** Consult the official documentation and the installed CLI/package
before recommending an approach or writing project files (see
[Use current tools](#use-current-tools)).

### Starting a new agent

When the user wants to build a new agent from scratch, clarify the shape before
scaffolding:

1. **Understand the goal in plain language.** Ask what the agent should do, who
   or what interacts with it, which language they want (Python or TypeScript),
   and only the follow-ups their answers raise (for example: external services,
   persistent memory, code or browser execution, schedules, messaging channels,
   human approval, or where they plan to host it). Keep it brief: two or three
   questions is usually enough.
2. **Check the docs for current support and constraints.** Verify the requested
   capabilities and target hosting environment against the official docs before
   promising them. If part of the request is not currently supported, say so
   directly and offer the closest supported alternative rather than silently
   dropping it.
3. **Confirm the plan, then follow the docs incrementally.** Summarize the
   proposed language, model choice, and capabilities, then follow the official
   quickstart and only the capability guides the plan calls for. Add one
   capability at a time and omit files or directories for capabilities the user
   did not ask for.

### Modifying an existing project

Inspect the existing directory, language, manifest, and installed `mda` and
`managed-deepagents` versions first. Match the project's existing layout and
installed SDK version, and load only the docs pages for the capabilities being
added or changed.

### Testing, deploying, and safety

- **Verify locally before deploying.** Follow the official local-development
  guide to run the agent locally and test realistic inputs, confirming tools
  and new capabilities work, before deploying.
- **Keep secrets out of code and commits.** Never fabricate, copy from other
  projects, print, or commit live API keys or tokens. Write only placeholder
  variable names or ask the user to supply secret values themselves, and keep
  `.env` files out of version control.
- **Confirm destructive or non-interactive actions.** Before deleting a
  deployment or passing flags that skip confirmation prompts, confirm with the
  user.

## Use current tools

Load only the docs needed for the current step, in the user's language (Python
or TypeScript):

- **Documentation MCP (preferred):** Use `langchain-docs` →
  `search_docs_by_lang_chain` and `query_docs_filesystem_docs_by_lang_chain` to
  find and read current Managed Deep Agents guides. Useful starting searches:
  "Managed Deep Agents overview", "Managed Deep Agents quickstart",
  "Managed Deep Agents project structure", "Develop locally with LangSmith
  Studio", "Deploy a Managed Deep Agent", "Managed Deep Agents CLI reference",
  "Move from Deep Agents to Managed Deep Agents", plus the specific capability
  needed (such as tools, MCP connectors, web search, connections, middleware,
  sandboxes, browser use, memory, identity, channels, schedules, subagents,
  runtime, Context Hub, custom frontend, MCP endpoint, or evals).
- **Official web docs (when MCP is unavailable):** Follow
  https://docs.langchain.com/llms.txt to the language-specific Build index,
  which lists every current Managed Deep Agents page and its Markdown URL:
  - Python: https://docs.langchain.com/_llms/agent-runtime/build/python.txt
  - TypeScript: https://docs.langchain.com/_llms/agent-runtime/build/type-script.txt

  Language-specific Markdown pages follow
  `https://docs.langchain.com/langsmith/<lang>/managed-deep-agents-<page>.md`
  (where `<lang>` is `python` or `javascript`; start with `overview`,
  `quickstart`, `project-structure`, `local-development`, `deploy`, `cli`, or
  `migrate`).
- **Underlying library APIs:** When writing custom tools, middleware,
  subagents, or client code against Deep Agents, LangChain, LangGraph, or
  LangSmith SDKs, use `langchain-reference` → `search_api`, then `get_symbol`
  (or https://reference.langchain.com/llms.txt).
- **Installed CLI and package:** Reconcile documentation against the project's
  installed version using `mda --help`, `mda <command> --help`, and the
  installed `managed-deepagents` package source or types. When the docs and the
  installed package disagree, trust `mda --help` and the installed package
  types for what the local version supports, then the current docs.
- **Offline fallback:** If you cannot reach the documentation MCP or web docs,
  say so explicitly, work from the installed CLI help and package source/types,
  and tell the user which official docs pages to verify.
