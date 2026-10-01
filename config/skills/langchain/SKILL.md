---
name: langchain
description: Build or modify applications with the LangChain framework, including models, tools, create_agent/createAgent, structured output, and agent invocation. Use when the code uses LangChain APIs or the user wants a LangChain agent; do not infer the framework solely from “LangChain” when it may mean the company or ecosystem.
---

# LangChain

LangChain provides model, tool, and agent abstractions. Its agents run on the
LangGraph runtime and can be composed with LangGraph workflows and Deep Agents.
Treat those layers as compatible parts of one application.

## Start from the application

Before changing code:

1. Determine whether this is a new application or an existing one.
2. Inspect the language, package versions, imports, agent construction, tools,
   and surrounding graph or application code.
3. Preserve explicit choices such as provider, model, project location,
   deployment target, and framework composition.
4. Check current LangChain documentation for APIs that may have changed since
   this skill was authored.

Use a direct model call when the application does not need an agent loop. Use
`create_agent` in Python or `createAgent` in TypeScript when a model must choose
and call tools. Do not replace an existing LangGraph workflow or Deep Agent
merely because it contains LangChain components.

## Reference routing

Read only the language reference needed for the task:

| Need | Read |
|---|---|
| Build or modify Python LangChain code | [Python](references/python.md) |
| Build or modify TypeScript LangChain code | [TypeScript](references/typescript.md) |

Route shared capabilities to their peer skill:

- thread state or durable memory → `memory-and-persistence`
- approvals, interrupts, or resumable review → `human-in-the-loop`
- agents as tools or agent/graph delegation → `subagents-and-composition`
- custom hooks or other agent middleware → `middleware`

Use `langchain-rag` for retrieval pipelines and `langchain-dependencies` for
package selection or version problems.

## Core guidance

- Give every tool a specific name, input schema, and description that explains
  when the model should call it.
- Use structured output when downstream code needs validated data rather than
  prose.
- Add only the tools and middleware needed for the requested behavior.
- Bound long-running agent execution and handle tool failures at the layer that
  can recover from them.
- Verify an observable application path, not only agent construction.

Do not deserialize untrusted LangChain manifests or runnables with permissive
class allowlists. Never load secrets from serialized input. If an application
accepts a configurable model endpoint or `base_url`, validate it against an
explicit allowlist before sending credentials.
