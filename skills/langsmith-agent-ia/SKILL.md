---
name: langsmith-agent-ia
description: Work in a LangSmith agent-based workspace when traces, datasets, evaluations, or deployments need to be placed under the right agent and environment. Use for IA setup, navigation problems, and migration from project-based tracing, including when "projects became agents", datasets or evaluators seem to have disappeared, there are duplicate agents per tier or script ("agent sprawl"), or the user asks about LANGSMITH_AGENT_ID, LANGSMITH_AGENT_ENVIRONMENT, agent addressing, or binding a deployment to an environment. Not for unrelated evaluation design or workspaces that still use project-based IA.
allowed-tools:
  - Bash(langsmith --version)
  - Bash(langsmith auth info *)
  - Bash(langsmith agents list *)
  - Bash(langsmith agents retrieve *)
  - Bash(langsmith sessions resolve *)
  - Bash(langsmith evaluators rule list *)
  - Bash(langsmith datasets list *)
---

# LangSmith agent-first IA

LangSmith's agent-first information architecture (IA) organizes a workspace
around agents instead of user-named tracing projects. Each agent has environments
for where it runs, so traces, online evaluations, and deployments can be associated
with the same application and the right runtime tier. Datasets attach to the
agent across tiers. This makes an agent's work easier to find and helps keep
production activity separate from staging and local development.

## Tools

Inspect and change the workspace with the `langsmith` CLI; use the SDK for
application tracing and evaluation runs. Before the first workspace command:

1. Run `langsmith --version`. If it is missing, give the user the install link
   from the [CLI docs](https://docs.langchain.com/langsmith/langsmith-cli) and continue
   with the UI or the API reference; do not install it without asking.
2. Run `langsmith auth info` and confirm the workspace and region match the
   user's target. Pass `--workspace <id>` rather than relying on a default. Do
   not print tokens or API keys.
3. Request `--format json` when parsing output, and check `<command> --help`
   for flags; the CLI changes faster than this skill.

Inventory commands are read-only. Run commands that create, update, attach,
archive, or delete only after the user approves the specific change.

For feature behavior, search the `langchain-docs` MCP server; the links below
are the fallback when it is unavailable.

## Locate the workspace and agent

Confirm the target workspace, region, and whether its current IA is agent-based.
Check the actual product version and current docs before assuming availability,
especially for self-hosted installations. If the workspace is project-based,
use its project model; do not send agent-addressed traces to it.

Read [how agent-based workspaces differ](https://docs.langchain.com/langsmith/migrate-to-agent-based-workspaces)
and [Agent Registry](https://docs.langchain.com/langsmith/agent-registry)
when identifying the workspace and agent.

Identify the intended agent by its stable ID, not its editable display name.
Treat that agent as the application identity. Use its environments to distinguish
where the same application runs, rather than creating another agent for each
tier or script. Preserve a user's explicit separation into distinct agents when
they represent genuinely different systems or ownership boundaries.

The environments are a fixed set with no custom names, and each has a role:

- **local**: a developer's machine, including ad hoc scripts and experiments.
- **development**, **staging**, **production**: deployed tiers.

Map extra tiers a team already uses (a second staging-like environment, for
example) onto these four, or keep them as a separate agent only when they really
are a different system. Some creation flows start the agent with all four
environments; an agent built in LangSmith's Build tab gains the others when
their first traces arrive.

Use `langsmith agents list` to find IDs and
`langsmith agents retrieve --agent-id <id> --include runtime_bindings` to
inspect environments and deployment bindings; an ordinary retrieval omits
bindings. `langsmith projects list` lists backing trace-storage projects, not
the Agent Registry.

## Place each resource at the right scope

| Resource | Scope to check | Practical check |
| --- | --- | --- |
| Traces | Agent and environment | Send a trace through the real application path and inspect the selected environment. |
| [Datasets](https://docs.langchain.com/langsmith/migrate-to-agent-based-workspaces#what-changes) | Agent, possibly more than one | Confirm the intended agent is attached; a dataset may exist at workspace level but be hidden by the agent filter. |
| [Online evaluators](https://docs.langchain.com/langsmith/evaluators), rules, alerts, and prebuilt dashboards | Agent environment | Check the environment that receives the runs being evaluated or monitored. |
| [Deployments](https://docs.langchain.com/langsmith/deploy-to-agent-environment) | Agent environment binding | Confirm the deployment appears under the intended agent and tier, and that its traces land there. |
| Custom dashboards | Agent | Check the agent selection when a dashboard seems absent. |

Attach evaluators intended to score production traffic to the production
environment, so local and development runs are not scored or billed as
production activity.

For offline evaluation and experiments, inspect their actual association and
visibility in the current product before assuming they follow online-evaluator
scoping. A dataset shared by several agents cannot by itself show which agent an
experiment ran against; record that in experiment metadata when it matters.

If a resource appears missing, clear the agent filter and inspect the workspace
inventory before recreating it. Then attach or configure the existing resource at
the intended scope. Attachment may be scriptable when the UI's bulk selector is
no longer offered; check the current docs and API reference for the attachment
mechanism (agent attachment has been implemented as a resource tag).

CLI dataset listings show that a dataset exists, but do not by themselves prove
its agent attachment. To inspect online evaluator targets, resolve the
environment first and pass its ID, for example
`langsmith sessions resolve --kind AGENT --id <agent-id> --environment PRODUCTION`
followed by `langsmith evaluators rule list --project-id <session-id>`. Avoid
name-based `--project` lookups: they may fall back to a legacy `LANGSMITH_PROJECT`
value from the shell and silently inspect the wrong target.

## Trace and deployment routing

Configure the application with the intended agent ID and environment using the
[tracing method](https://docs.langchain.com/langsmith/log-traces-to-agent)
supported by its installed SDK or integration. **Do not combine agent addressing
with a project destination.** Agent variables alongside legacy project variables
leave untargeted calls untraced, usually with only a warning. Naming just one
of the agent ID and environment has the same effect. A project override in code
can silently win over agent environment variables; passing an agent address and
project name on the same call fails. Remove legacy project settings
(`LANGSMITH_PROJECT`, `LANGCHAIN_PROJECT`, `LANGCHAIN_SESSION`, and code-level
project overrides) wherever agent addressing is intended. Check setting names
without exposing values across shell profiles, `.env` files, CI variables,
container and deployment environments, and IT-managed configuration.

Tracing to a new legacy project name in an agent-based workspace can register a
new agent automatically. One project name per script, experiment, or developer
therefore turns into dozens of throwaway agents. Send scripts and experiments to
the agent's local environment instead, and tell them apart with run names, tags,
or metadata. Developer tooling can create agents the same way (for example a
`<agent>-local` agent), so check for those in the inventory.

If an integration only accepts a project name, retrieve the environment's
compatibility name from LangSmith; do not derive it from the agent ID.

Verify a trace through the application's actual framework path, including
child runs and expected metadata. A standalone tracing probe does not establish
that framework traces use the same route; older framework tracers have set a
default project explicitly, which overrides agent addressing. When a query API
still takes a project or session ID,
[resolve the selected agent environment](https://docs.langchain.com/langsmith/resolve-an-agent)
first.

Library upgrades needed for agent addressing can also change run payloads, such
as the shape of tool inputs that callbacks receive. Custom tracers, redaction,
and classification code can then break without an error. Run their tests with
the agent settings both set and unset. Check transitive dependency pins on the
tracing SDK, which can block or invalidate the upgrade.

For a deployment, verify its agent and environment binding independently of
its name or tracing environment variables. If an existing deployment cannot be
rebound with currently supported tools, create the replacement and check the new
binding. Expect the replacement to have a new URL and possibly a
system-generated name: update every caller, not just CI (web app
configuration, release checklists, deployment IDs in secrets), and re-enable
settings such as preview builds. For a tier that CI or users depend on, create
the replacement alongside the old one and switch callers before retiring the old
deployment.

## Handle secrets during migration

Copying deployment configuration often means moving secret values. Never print
them, and assume any output may persist in transcripts, logs, or session-tracing
tools.

- **Never print the error response of a request that carries secrets.**
  Validation errors can echo the entire request body. Print only the status code
  and the error message or field location.
- Values the API returns already redacted, as placeholders, are not the real
  secret. Leave them out of the copy and have the user re-enter them.
- Prefer handing the user a script to run for secret copies, so values never pass
  through the assistant's context. Write any temporary files with restrictive
  permissions and delete them afterwards.
- If a value is exposed anyway, say so immediately. List which secrets (by name)
  and where the output went, and recommend rotation on every deployment that
  shares the value.

## Consolidate migration leftovers

Inventory before choosing a canonical agent. A read-only pass usually covers:

1. `langsmith agents list` for every agent.
2. For each agent, `langsmith agents retrieve --agent-id <id> --include runtime_bindings`
   to get its environments and deployment bindings.
3. For each environment, resolve its session ID. Then check its retained trace
   count, last activity, online evaluator rules, and alerts.
4. Check resources attached to each agent, and datasets attached to none.

During migration, each tracing project typically became its own agent, with its
traffic under Production and the project's existing ID kept for that
environment. So a project-per-tier setup produces several agents, with staging
and development traffic labeled Production. The agent for the old production
project keeps its evaluators, alerts, and monitoring history, which usually makes
it the right canonical identity. Confirm ownership and intent with the user
first.

Map every sender and deployment to its intended environment. Do not assume
historical traces can be merged or moved between agents; plan for discoverability
and verify currently supported migration paths. The old project's traces and
project-scoped rules remain with its new agent's Production environment.
Prompts, datasets, and experiments remain records but may be hidden by the agent
filter or need association with the intended agent. Check each resource before
recreating it.

One workspace per environment fits the agent model poorly. Moving to
environments inside one workspace is the intended direction, but there may be no
built-in path to move existing data. Discuss the trade-off before planning it.

Some workspaces may temporarily be able to restore the previous layout through
an admin setting. That changes the view for everyone in the workspace and is
transitional, so treat it as breathing room rather than a destination.

After moving new activity, verify every changed environment and resource
association. Re-inventory old agents before cleanup and preserve any with needed
history or active bindings.

- **Find live senders first.** Before removing an agent, confirm nothing still
  sends traces to it. Legacy tracing to that name may recreate the agent, so
  find the sender (run metadata often identifies the host or
  graph) and repoint it first.
- **Archive and delete differ.** Archiving, where available, may keep the agent's
  ID reserved. Deleting can be permanent and may also remove the agent's
  environments and stored traces. Check current behavior before choosing.
- **Delete only with authorization.** Delete only when the user has authorized
  permanent removal of the specific agents and a fresh inventory, taken
  immediately before deletion, shows them still empty.
