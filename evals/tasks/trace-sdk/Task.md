# Trace a two-service support agent with the LangSmith SDK

Status: Draft (exploratory, unscored)

## Purpose

Evaluate whether the agent-tracing skill helps a coding agent instrument an
existing plain-Python application so its traces land in the right agent
environment, group into threads, and stay connected across a service boundary.
The instruction names the agent, environment, and outcomes but not the SDK
calls, CLI, or skill, so the trajectory shows which guidance the agent finds
and how it verifies the result.

This is one of three tracing tasks that share the app and checks in
`evals/shared/trace-support/`. `trace-otel` requires OpenTelemetry on the same
app, and `trace-strands` uses a Strands version of the assistant.

## Environment and evidence

The shared app is a deterministic support assistant: `assistant.py` calls a
separate tools service (`tools_service.py`) over HTTP, and
`run_conversations.py` plays three recorded conversations (seven turns, six of
which call the tools service). `prepare` registers a temporary agent for each
trial and passes its ID as `TARGET_AGENT_ID`. The image preinstalls the
LangSmith SDK because the sandbox cannot reach a package index.

The live report reads only run names, types, parent links, and whether each run
carries a `thread_id`; it never stores inputs or outputs. It records, against
`expected.json`:

- **Destination:** root runs in the `development` environment, and stray runs
  in the agent's other environments or the trial's target project.
- **Flush:** whether every turn arrived, including the tools service's runs
  after the service shuts down.
- **Threads:** distinct thread IDs, turns per thread, and the share of runs
  that carry `thread_id`.
- **Distributed tracing:** whether tools-service runs appear inside the calling
  turn's trace rather than as separate root traces.

## Fairness and limits

The model is scripted, so no provider credentials are needed and every trial
plays the same turns. `expected.json` stays outside the task environment; the
conversation script is visible because the agent must run it. Tools-service
runs are recognized by position: any run whose parent is the app's `call_tool`
span counts, whatever the agent names it. A service run that lands as a root
trace, because context did not cross the process boundary, still fails
distributed tracing. One trial per profile is an anecdote, not a rate.
