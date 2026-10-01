---
name: langgraph
description: Build or modify applications with LangGraph, including StateGraph, state schemas, nodes, edges, routing, Command, Send, compilation, invocation, streaming, and error handling. Use when the application needs explicit graph control flow or already uses LangGraph APIs.
---

# LangGraph

LangGraph is the low-level orchestration and durable execution runtime beneath
LangChain agents and Deep Agents. Use it for workflows that need explicit state,
branching, loops, parallelism, or deterministic control around agentic steps.
LangChain agents and Deep Agents can run inside or alongside a graph.

## Start from the application

Before changing code:

1. Determine whether this is a new graph or an existing application.
2. Inspect the language, package versions, state schema, compiled graph,
   persistence configuration, and any agents or subgraphs it contains.
3. Preserve explicit choices such as language, provider, model, state shape,
   deployment target, and framework boundaries.
4. Check current LangGraph documentation for APIs that may have changed since
   this skill was authored.

Do not replace a LangChain agent or Deep Agent with a custom graph unless the
requested behavior needs explicit graph control. Do not flatten an existing
graph into an agent loop merely because some nodes call models.

## Design the graph

1. Identify discrete steps and the outcome of each step.
2. Define state from raw data shared between steps; format prompts inside nodes.
3. Make each node return a partial state update rather than mutating state.
4. Add deterministic edges, conditional routing, loops, or parallel fan-out.
5. Compile the graph, then invoke or stream the compiled graph.

Fields overwrite by default. Add reducers only for values that must accumulate
across updates or parallel branches. Every loop needs a reachable exit.

## Reference routing

| Need | Read |
|---|---|
| Build or modify Python LangGraph code | [Python](references/python.md) |
| Build or modify TypeScript LangGraph code | [TypeScript](references/typescript.md) |

Route shared capabilities to their peer skill:

- checkpointing, durable execution, history, or stores →
  `memory-and-persistence`
- `interrupt` and resumable human review → `human-in-the-loop`
- subgraphs, graph-as-tool, agent nodes, or dynamic workers →
  `subagents-and-composition`

Use `langgraph-cli` for project configuration, local servers, builds, and
deployment commands. LangGraph control flow is not agent middleware; use the
`middleware` skill only for a LangChain or Deep Agent contained in the graph.

## Core boundaries

- `Command` can combine a state update with dynamic routing. Static edges from
  the same node still run, so account for both.
- `Send` creates dynamic parallel work; accumulated results require a reducer.
- Use retry policies for transient failures, model-visible tool errors for
  errors the model can correct, and ordinary exceptions for unexpected faults.
- Keep state and persisted values serializable for the configured checkpointer.
- Verify the actual branch, loop, parallel, and failure paths the application
  depends on.
