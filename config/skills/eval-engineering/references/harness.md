# Harness

The Harness is the complete agent Harbor runs. Harbor's core concepts call it the Agent.

It owns:

- model configuration, prompts, loop, routing, retries, and stopping;
- repository-defined tool definitions and implementations, including argument/result parsing;
- middleware, hooks, memory, session state, and context assembly;
- the Harbor adapter that starts the agent and records its rollout.

The Environment owns what surrounds it: files, data, services behind tools, permissions, network, time, and mutable external state.

## Write `harness.md`

Before implementation, write `evals/specs/<task-id>/harness.md`:

```text
Status: draft | approved
Entrypoint: exact callable or command
Source: repository path and revision
Preserved behavior: prompts, model loop, tools, hooks, memory, stopping
Adapter: I/O translation and dependency binding, or none
Session: single-turn or exact multi-turn persistence
Credentials: environment-variable names only
Recorded evidence: messages, model/tool calls, results, state, errors
Reconstruction differences: none, or exact lost/changed behavior
```

Set `Status: approved` only after the user approves this file with `environment.md` and `task.md`.

## Choose what Harbor runs

Prefer the active repository entrypoint. Use a reconstruction only when the entrypoint cannot run safely or reproducibly, and name what changes.

```text
Harness: active `support_agent.run`
Preserved: prompt, model settings, tool code, retry middleware, thread memory
Adapter: translates Harbor instruction/response and records observed calls
Credentials: model API key and read-only ticket-service token
```

A copy that changes prompts, control flow, tool parsing, memory, or model behavior is a reconstruction. Do not describe its result as the production agent's result.

If source is copied into a task image, pin the revision and include every reachable Harness-owned module. Hashing only the entrypoint does not establish parity. Keep logging and Harbor translation in a wrapper rather than changing agent logic.

## Preserve the production interface

Follow the production boundary. Keep repository-defined tool behavior in the Harness and replace its dependency behind the existing interface.

```text
Harness: `search_docs(query)` tool definition, validation, result parsing, retries
Environment: search endpoint, frozen documents/index, latency and error responses
```

A dynamically supplied MCP or HTTP tool server may run in the Environment; the Harness still owns how it discovers, calls, and uses it. If the eval replaces repository-defined tool code with a lookalike, label the Harness a reconstruction.

## Sessions and multi-turn runs

Create one Harness session per trial. Send `instruction.md` first, then later user messages through that same session. Do not preload future turns. The Harness may make any number of model and tool calls before returning each response.

For multi-turn wiring, use [the simulation reference](multi-turn-simulation/guide.md).

## Record the rollout

The Harness adapter must record events as they happen:

- user and agent messages;
- model/tool calls, arguments, results, retries, and errors it directly observes;
- session ID and non-secret resolved configuration;
- final response and termination reason.

Do not infer calls from the agent's prose. Keep credentials, hidden truth, simulator instructions, and Verifier criteria out of Harness-visible input and artifacts.
