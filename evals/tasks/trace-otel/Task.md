# Trace a two-service support agent with OpenTelemetry

Status: Draft (exploratory, unscored)

## Purpose

Evaluate whether the agent-tracing skill helps a coding agent export
OpenTelemetry traces from an existing plain-Python application to the right
LangSmith agent environment, with turns grouped into threads and context
propagated across a service boundary. The instruction requires OpenTelemetry
because the team standardizes on it; it does not name the exporter settings,
headers, span attributes, CLI, or skill.

This is one of three tracing tasks that share the app and checks in
`evals/shared/trace-support/`. `trace-sdk` uses the same app with the
LangSmith SDK, and `trace-strands` uses a Strands version of the assistant.

## Environment and evidence

The app, agent setup, and live report are the same as in `trace-sdk`. The image
preinstalls `langsmith[otel]`, which brings the OpenTelemetry SDK and OTLP
exporter, because the sandbox cannot reach a package index. The LangSmith SDK
is therefore also installed; whether the agent keeps to OpenTelemetry is part
of the evidence.

The report records, against `expected.json`, the destination, whether every
turn arrived, thread grouping and `thread_id` coverage, and whether
tools-service spans join the calling turn's trace. Thread grouping in
OpenTelemetry depends on the agent mapping `thread_id` into LangSmith metadata,
and cross-service linking depends on W3C trace-context propagation.

## Fairness and limits

The model is scripted, so no provider credentials are needed and every trial
plays the same turns. `expected.json` stays outside the task environment. The
OTLP endpoint accepts spans asynchronously, so a span whose parent never
arrives is dropped without an error; the report counts what LangSmith stored,
not what the app attempted to send. Tools-service spans are recognized by an
OpenTelemetry `service.instance.id` that differs from the turn root's, so span
names do not matter. One trial per profile is an anecdote, not a rate.
