---
name: langchain-agent-tracing
description: Use when adding, fixing, or reviewing LangSmith tracing for an agent or LLM application, including choosing instrumentation for LangChain, LangGraph, Deep Agents, other agent frameworks, or OpenTelemetry; sending traces to the right agent environment or project; grouping turns into threads; metadata; sampling and conditional tracing; redacting sensitive data; distributed tracing across services; and finding traces after they land.
---

# Trace agents with LangSmith

Good tracing lands every run in the right place, keeps a request's runs in one
trace, keeps sensitive data out, and records what monitoring and evaluation
will need later. Decisions made while instrumenting limit what is possible
downstream: without a thread ID there are no thread-level evaluators, and
without stable metadata there is nothing to filter or alert on.

## Decide where traces go

Check how the target workspace organizes traces before configuring a
destination. Run `langsmith agents list --workspace <workspace-id> --format json`.
If it returns registered agents, the workspace is agent-based. An empty result
or an error is not conclusive: confirm in the LangSmith UI, where the top-left
control names the workspace in an agent-based workspace and shows the LangSmith
logo with an **Application** picker in a project-based one. If it is still
unclear, ask the user before choosing a destination.

In an agent-based workspace:

- Register the application as one agent, once, rather than one agent per tier
  or script. Reuse an existing agent when it represents the same system.
  Registration needs permission to create projects; `langsmith agents create`
  or the docs' programmatic creation flow can do it.
- Address traces with `LANGSMITH_AGENT_ID` (the stable ID, not the display
  name) and `LANGSMITH_AGENT_ENVIRONMENT`: `local` for a developer machine and
  ad hoc scripts; `development`, `staging`, or `production` for deployed tiers.
- Remove `LANGSMITH_PROJECT`, `LANGCHAIN_PROJECT`, and `LANGCHAIN_SESSION` from
  that runtime. Do not combine legacy destinations with agent addressing.
- When an integration only accepts a project name, use the environment's
  `tracer_session_name`.
- To route individual requests, such as per tenant or per feature branch, pass
  an agent address through the SDK's tracing context instead of changing
  process-wide variables.

In a project-based workspace, set `LANGSMITH_PROJECT` to the tracing project.

### Confirm the region, workspace, and credentials

The application's endpoint and API key determine which organization and
workspace receive traces before the agent or project is applied. Check them in
every runtime that sends traces: local shell, `.env` files, CI, and deployment
secrets often differ.

- **Region or instance:** `LANGSMITH_ENDPOINT` must be the API URL for the
  organization's region or self-hosted instance. Without it, the SDK uses the
  default US URL, and a key from another region (EU, for example) will not
  authenticate. Look up the region's URL in the docs instead of guessing it.
  OpenTelemetry exporters use the same base URL with the OTLP path.
- **Workspace:** when the API key can access more than one workspace, set
  `LANGSMITH_WORKSPACE_ID` to the target workspace. Otherwise traces go to the
  key's default workspace. Direct API calls and OpenTelemetry exports carry the
  workspace in the `X-Tenant-Id` header. Agent IDs and project names are
  resolved within that workspace, so the same ID in another workspace is a
  different agent or none.
- **Key:** use a key from the target organization with permission to write
  traces there. Never print or log its value.
- **Legacy names:** `LANGCHAIN_*` equivalents of these variables are still
  read. Remove stale ones so they cannot point traces at another endpoint,
  workspace, or project.

Compare the application's settings with what the CLI will query:
`langsmith auth info --format json` reports the CLI's `api_url` and
`workspace_id`. If they differ from the application's endpoint or workspace,
pass `--api-url` and `--workspace` explicitly; otherwise verification searches
the wrong place and a correctly sent trace looks missing.

## Choose the instrumentation layer

Start from what the application already uses:

- **LangChain, LangGraph, and Deep Agents** trace automatically once tracing
  and the destination are configured. Agents running on a LangSmith Agent
  Server are traced by the server; check its deployment settings rather than
  adding tracing code.
- **Another agent framework or model provider:** use its official LangSmith
  integration when one exists. Find it on the
  [integrations page](https://docs.langchain.com/langsmith/integrations) under
  "Agent frameworks" or "LLM providers", and follow its setup, including how it
  selects the agent environment. Wrapping the framework's entry point in
  `traceable` instead records only your wrapper, not the framework's own agent,
  model, and tool spans.
- **Custom Python or TypeScript code:** wrap meaningful units of work with
  `traceable` and use the SDK's provider client wrappers so model calls nest
  under them.
- **An existing OpenTelemetry pipeline or another language:** export to
  LangSmith's OTLP endpoint with the agent ID and environment headers, or use
  the SDK's OpenTelemetry support.

Instrument each call once. Combining a framework integration, a wrapper, and an
OpenTelemetry exporter on the same calls produces duplicate or disconnected
runs. To send the same traces to LangSmith and another backend, use the SDK's
tracing modes or replicas rather than parallel instrumentation.

Choose the instrumentation first, then propagate context the way it expects:
the SDK's `langsmith-trace` and `baggage` headers for `traceable`, and W3C
`traceparent` for OpenTelemetry-based integrations. Don't switch to the SDK
just to make cross-service propagation easier.

## Make traces useful for monitoring

- **Threads:** for multi-turn applications, put a `thread_id` in the metadata
  of every run, including child runs, using one ID per conversation (the docs
  recommend UUID v7). Runs without it drop out of thread filters and thread
  token and cost totals.
- **Metadata and tags:** choose a small set of stable metadata keys, such as
  app version, tenant, feature flag, or model, and use tags for coarse
  grouping. Keep key names consistent across services so filters and alerts
  keep working. Never put secrets or raw personal data in metadata or tags.
- **Names and boundaries:** give runs names that describe the step, and make
  the root run's inputs and outputs the user-visible request and response.
  Evaluators and reviewers read the root run first.

For scoring and alerting on these traces, use `langchain-agent-monitoring`.

## Control volume and cost

- `LANGSMITH_TRACING_SAMPLING_RATE` (0 to 1) downsamples traces sent through
  the SDK and LangChain; it does not apply to direct API logging.
- Use the SDK's tracing context to disable tracing for low-value requests or
  tenants with zero-retention requirements, and to enable it for one code path
  without turning it on globally.
- Online evaluators sample the traces that remain, so the effective coverage
  is the product of both rates. Check how sampling treats multi-turn threads
  before relying on thread-level evaluation of sampled traffic.

## Keep sensitive data out

Decide what may leave the process before enabling tracing in production.
Choose the narrowest control that meets the requirement:

- Hide all inputs or outputs for a client or process (`LANGSMITH_HIDE_INPUTS`,
  `LANGSMITH_HIDE_OUTPUTS`) when nothing may be stored.
- Use the SDK's anonymizer or input/output processors to redact known
  patterns while keeping the rest of the trace.
- Redact per request with replica updates when only some tenants need it;
  follow the docs' caveat about setting the replica destination explicitly, or
  the redaction can be dropped.
- Disable tracing for a request when even run structure must not be recorded.
- In an OpenTelemetry pipeline, redact span attributes in the collector before
  export.

Confirm the result by reading a real trace's inputs, outputs, and metadata.

## Trace across services

When one request crosses services, propagate LangSmith's trace context so the
whole request appears as one trace. The caller sends the current run's headers
(`langsmith-trace`, plus `baggage` for metadata and tags); the receiving service
continues the trace from them through the SDK's tracing context or its tracing
middleware. Calls into a deployed Agent Server have their own guide.

Only accept these headers from trusted internal services. They control how runs
are recorded, so strip them from untrusted inbound requests at the gateway.

With OpenTelemetry, every ancestor span must also reach LangSmith. A child whose
parent is exported elsewhere or sampled out is dropped without an error, even
though the export call succeeds.

## Find traces after they land

Resolve the destination to an ID, then query by ID; name-based `--project`
lookups can silently use a leftover `LANGSMITH_PROJECT`.

```bash
langsmith projects resolve --kind AGENT --id <agent-id> --environment LOCAL --format json
langsmith traces list --project-id <session-id> --last-n-minutes 30 --limit 5 --format json
langsmith traces get <trace-id> --project-id <session-id> --full --format json
```

In a project-based workspace, find the project ID with `langsmith projects list`.
Narrow `traces list` with `--error`, `--tags`, `--metadata key=value`, or
`--filter`. Use `langsmith runs list --project-id <session-id> --trace-ids <trace-id>`
for the runs in one trace, adding `--metadata thread_id=<thread-id>` to confirm
child runs carry the thread. Check grouping with `langsmith threads list` and
`langsmith threads get <thread-id>` using the same `--project-id`.

## Verify the instrumentation

Exercise the real application path with a realistic request, then use the
commands above to confirm:

- The trace is in the intended region, workspace, and agent environment or
  project, and nowhere else.
- The run tree has the expected structure, with no duplicate or orphaned runs.
- `thread_id` and the chosen metadata appear on child runs, not only the root.
- Inputs, outputs, and metadata contain no secrets or data that should have
  been redacted.
- Calls across services appear as one trace.

Tracing exports in the background. Scripts, tests, serverless functions, and
workers must flush or shut down the tracer before exiting, or the last traces
are lost; look up the flush call for the SDK and language in use. If no trace
appears, check that the CLI is querying the same endpoint and workspace as the
application, then the API key, agent ID and environment, and whether a sampling
rate or tracing context disabled it, before changing code.

## Use current tools

Use `langchain-docs` → `search_docs_by_lang_chain` and
`query_docs_filesystem_docs_by_lang_chain` for current setup. Useful searches:
"log traces to an agent", "LangSmith integrations", "trace with OpenTelemetry",
"distributed tracing", "conditional tracing", "sample traces", "threads", and
"prevent logging of sensitive data". Use `langchain-reference` → `search_api`,
then `get_symbol`, for exact signatures of `traceable`, `tracing_context`,
wrappers, and client options, and reconcile them with the installed SDK
version. If MCP is unavailable, start from https://docs.langchain.com/llms.txt
and https://reference.langchain.com/llms.txt.

Before the first workspace command, check `langsmith --version` and
`langsmith auth info`; do not call `langsmith auth token`. Pin the workspace
with `--workspace`, request `--format json` when parsing, and check each
command's `--help` for current flags.
