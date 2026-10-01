---
name: subagents-and-composition
description: Design or modify delegation between agents, graphs, and specialized workers. Use when an application needs subagents, agent-as-tool patterns, nested workflows, context isolation, or composition across Deep Agents, LangChain, and LangGraph.
---

# Subagents and composition

Inspect the existing application before selecting a composition pattern.
LangChain agents, LangGraph workflows, and Deep Agents can call or contain one
another; preserve the user's current boundaries unless the requested behavior
requires changing them.

Choose the smallest boundary that improves the application:

- Use a **tool** when the caller only needs a narrow operation and result.
- Use a **subagent** when a task benefits from a fresh context, specialized
  prompt, model, or tools.
- Use a **graph or subgraph** when the delegated work needs explicit state and
  deterministic control flow.
- Keep work in the **main agent** when delegation adds no useful isolation or
  specialization.

Define the input contract, available context, tools, state ownership, result
shape, and failure behavior at every boundary. Give ephemeral workers complete
instructions for one invocation and expect one final result. Do not assume a
custom worker inherits the parent's middleware, skills, memory, or permissions;
configure and verify each dependency explicitly.

## References

- For LangChain agent-as-tool composition, read
  [LangChain](references/langchain.md).
- For LangGraph subgraphs, agent nodes, and dynamic workers, read
  [LangGraph](references/langgraph.md).
- For Deep Agents subagents, read
  [Deep Agents](references/deep-agents.md).
