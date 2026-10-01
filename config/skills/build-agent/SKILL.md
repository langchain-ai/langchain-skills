---
name: build-agent
description: Choose and combine LangChain, LangGraph, Deep Agents, and Managed Deep Agents when designing a new agent application or changing its architecture. Use when the user asks to build an agent, says “LangChain” ambiguously, needs help choosing a starting point, or describes an application that may span multiple frameworks. Skip when existing code or the request already identifies the framework and capability to change.
---

# Build an agent

Use this skill to choose an application architecture and the other skills needed
to implement it. It is an architecture router, not a prerequisite for every
LangChain ecosystem task.

The frameworks work together:

- **LangChain** supplies models, tools, agent construction, middleware,
  structured output, and retrieval components.
- **LangGraph** supplies explicit state, deterministic control flow, durable
  execution, branching, loops, and parallelism. Its nodes can call LangChain
  agents or Deep Agents.
- **Deep Agents** is an agent harness built from LangChain and LangGraph. A Deep
  Agent can run alone, inside a graph node, or as a delegated worker.
- **Managed Deep Agents** is the managed LangSmith path for building and
  deploying a Deep Agent with minimal infrastructure and setup.

Do not force these into a single-choice framework comparison. Choose a starting
surface, then compose other surfaces where the application needs them.

## Opinionated starting defaults

For a new application:

1. **Start with Deep Agents when the application should be agentic.** This is
   the default for an agent that must reason through work, call tools, manage
   context, work with files, or delegate tasks.
2. **Start with LangGraph when the workflow should be deterministic.** Use it
   when the developer wants explicit steps, state transitions, branches, loops,
   parallel work, or precise control instead of an autonomous agent loop.
3. **Use a hybrid LangGraph workflow when only some steps should be agentic.**
   Keep deterministic business logic in graph nodes and place a LangChain agent
   or Deep Agent only in the nodes that need model-directed behavior.
4. **Choose Managed Deep Agents when the user already uses LangSmith and wants
   the easiest managed route to build and deploy a Deep Agent.** Prefer it when
   managed threads, context, sandboxes, schedules, channels, and deployment are
   more valuable than controlling that infrastructure directly.

Use LangChain directly when building model calls, tools, middleware, structured
output, retrieval, or an existing LangChain agent. For a new agentic application,
prefer the Deep Agents starting point unless the user wants a lower-level agent
with deliberately minimal harness behavior.

## Start from existing reality

Before selecting architecture, determine whether the application is new or
existing. For an existing application, inspect its imports, construction APIs,
state, persistence, deployment, and composition boundaries. Preserve the
current architecture unless the requested behavior exposes a concrete reason to
change it.

When the user says “LangChain,” determine from their repository and request
whether they mean the LangChain framework, the broader ecosystem, or the
company's products. Do not assume they want `create_agent` solely from the name.

## Select a skill set

Load the construction skill for every surface being changed:

| Work | Skill |
|---|---|
| LangChain models, tools, agents, or structured output | `langchain` |
| Explicit graph state and control flow | `langgraph` |
| Open-source Deep Agents harness | `deep-agents` |
| Managed LangSmith Deep Agent runtime or deployment | `managed-deep-agents` |

Add capability skills based on behavior, regardless of starting surface:

| Behavior | Skill |
|---|---|
| Thread state, durable memory, stores, or working files | `memory-and-persistence` |
| Pauses, review, approval, editing, or rejection | `human-in-the-loop` |
| Delegation, subagents, agent-as-tool, or nested graphs | `subagents-and-composition` |
| Agent-loop hooks, planning, summarization, or tool wrapping | `middleware` |

Add specialized or operational skills only when needed:

- `langchain-rag` for indexed knowledge retrieval.
- `langchain-dependencies` for installation and version resolution.
- `langgraph-cli` for LangGraph project configuration and deployment commands.
- `eval-engineering` for Harbor evaluation tasks.
- `langsmith-online-eval-engineering` for production trace evaluators.
- `swarm` when independent implementation work should run in parallel.

## Example routing

```text
“Build an agent that researches and writes reports”
→ deep-agents

“Build an order workflow with fixed validation and approval steps”
→ langgraph + human-in-the-loop

“Use a Deep Agent for research inside our existing graph”
→ langgraph + deep-agents + subagents-and-composition

“Deploy our Deep Agent with LangSmith schedules and Slack”
→ managed-deep-agents

“Add durable conversation state to this LangChain agent”
→ langchain + memory-and-persistence
```

Bound agentic execution with appropriate step, recursion, and time limits.
Validate model-selected tool arguments and state-changing actions against
application rules and authorization before execution.
