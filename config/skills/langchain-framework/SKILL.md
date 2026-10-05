---
name: langchain-framework
description: Build or modify code using the LangChain framework library, including models, tools, the base create_agent/createAgent API, middleware integration, structured output, and agent invocation. Use when existing code imports LangChain framework APIs or the user explicitly asks for create_agent, a minimal configurable ReAct-style agent harness, or LangChain components. Do not activate solely because the user says “LangChain”; that normally means the broader ecosystem and should route through langchain-build-agent.
---

# LangChain framework

This skill is for the LangChain framework library, not the entire LangChain
ecosystem. It provides model, tool, middleware, structured-output, retrieval,
and base agent APIs. The base `create_agent`/`createAgent` implementation is the
foundation Deep Agents builds on with additional middleware and prompt
opinions. The same LangChain components are commonly used inside Deep Agents and
LangGraph workflows.

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
`create_agent` in Python or `createAgent` in TypeScript for a minimal,
configurable ReAct-style harness when a model must choose and call tools and the
user deliberately wants the base agent abstraction. For a new agentic
application, the `langchain-build-agent` skill recommends starting with Deep Agents. Do
not replace an existing LangGraph workflow or Deep Agent merely because it
contains LangChain components.

## Reference routing

Read only the language reference needed for the task:

| Need | Read |
|---|---|
| Build or modify Python LangChain code | [Python](references/python.md) |
| Build or modify TypeScript LangChain code | [TypeScript](references/typescript.md) |

Route shared capabilities to their peer skill:

- thread state or durable memory → `langchain-memory-and-persistence`
- approvals, interrupts, or resumable review → `langchain-human-in-the-loop`
- agents as tools or agent/graph delegation → `langchain-subagents-and-composition`
- custom hooks or other agent middleware → `langchain-middleware`
- indexed knowledge, retrieval pipelines, or retrieval tools →
  `langchain-retrieval-and-rag`

Handle package selection and version compatibility within the applicable skill
reference and the project's existing dependency files.

## Core guidance

- Give every tool a specific name, input schema, and description that explains
  when the model should call it.
- Keep tool authorization and argument validation in application code. A tool
  description guides model choice; it does not grant permission.
- Use structured output when downstream code needs validated data rather than
  prose.
- Use runtime context for request-scoped identity, configuration, connections,
  and other dependencies instead of global variables or persisted secrets.
- Add only the tools and middleware needed for the requested behavior.
- Bound long-running agent execution and handle tool failures at the layer that
  can recover from them.
- Use event streaming for new applications that need typed message, tool-call,
  value, or subgraph projections; preserve an existing stream-mode integration
  when modifying one.
- Verify an observable application path, not only agent construction.

For MCP, frontend integration, observability, or deployment, use the current
language-specific LangChain documentation and preserve the application's
authentication, authorization, transport, and hosting boundaries.

Do not deserialize untrusted LangChain manifests or runnables with permissive
class allowlists. Never load secrets from serialized input. If an application
accepts a configurable model endpoint or `base_url`, validate it against an
explicit allowlist before sending credentials.
