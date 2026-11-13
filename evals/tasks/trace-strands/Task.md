# Trace a two-service Strands support agent

Status: Draft (exploratory, unscored)

## Purpose

Evaluate whether the agent-tracing skill leads a coding agent to LangSmith's
native Strands Agents integration and uses it to send traces to the right agent
environment, grouped into threads, with context propagated to a separate tools
service. The instruction names the agent, environment, and outcomes but not the
integration, exporter, CLI, or skill.

This is one of three tracing tasks that share the app and checks in
`evals/shared/trace-support/`. `trace-sdk` and `trace-otel` use the plain
version of the assistant.

## Environment and evidence

`environment/app/assistant.py` replaces the shared assistant with a Strands
agent driven by a scripted `Model` subclass. Its tools call the shared tools
service over HTTP, and it produces the same replies as the plain assistant. The
image preinstalls `strands-agents` and `langsmith[otel]`, which includes the
Strands integration, because the sandbox cannot reach a package index.

The report records, against `expected.json`, the destination, whether every
turn arrived, thread grouping and `thread_id` coverage, and whether
tools-service spans join the calling turn's trace. Strands emits OpenTelemetry
spans, so cross-service linking depends on W3C trace-context propagation from
the tool call to the tools service.

## Fairness and limits

The scripted model needs no provider credentials, and every trial plays the same
turns. `expected.json` stays outside the task environment. Strands names its
own spans, so the report's run names reflect the framework as well as the
agent's choices. Tools-service spans are recognized by an OpenTelemetry
`service.instance.id` that differs from the turn root's. One trial per profile
is an anecdote, not a rate.
