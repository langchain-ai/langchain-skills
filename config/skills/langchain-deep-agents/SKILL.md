---
name: langchain-deep-agents
description: Build or modify applications that use the open-source Deep Agents harness, including create_deep_agent/createDeepAgent, execution and context management, delegation, steering, and composition with LangChain agents or LangGraph workflows. Use for Deep Agents-specific construction and configuration, not Managed Deep Agents deployment or generic LangChain or LangGraph work.
---

# Deep Agents

Deep Agents is an agent harness built from LangChain agent components and the
LangGraph runtime. It adds capabilities for execution, context management,
delegation, and steering around the core agent loop. Some
capabilities, including task planning and skills, are opt-in.

A Deep Agent can be used by itself or composed with other LangChain agents and
LangGraph workflows.

Preserve the user's existing architecture. Do not treat Deep Agents,
LangChain agents, and LangGraph workflows as mutually exclusive application
choices.

## Start from the task and repository

Before changing code:

1. Determine whether the user is creating a new application or modifying an
   existing one.
2. For an existing application, inspect its language, package versions,
   current agent construction, and surrounding graph or application code.
3. Preserve explicit choices such as language, provider, model, project
   location, tools, and deployment target.
4. Consult current Deep Agents documentation for API shapes that may have
   changed since this skill was authored.

Do not force a research-agent demo, a new directory, a different model, or a
new provider when the user has already described the application they want.

## Reference routing

Read only the references needed for the current task:

| Need | Read |
|---|---|
| Build or modify a Python Deep Agent | [Python](references/python.md) |
| Build or modify a TypeScript Deep Agent | [TypeScript](references/typescript.md) |
| Design harness configuration or compose agents and graphs | [Harness configuration](references/harness-configuration.md), plus the relevant language reference |
| Configure execution, context, delegation, or steering | [Harness configuration](references/harness-configuration.md), plus the relevant language reference |
| Add multimodality, profiles, event streaming, fault tolerance, frontend integration, or an agent protocol | [Harness configuration](references/harness-configuration.md), then the current capability documentation |

When a task also involves a shared capability, route that part of the work to
the corresponding peer skill:

- persistence, durable memory, or filesystem backends →
  `langchain-memory-and-persistence`
- approvals, interrupts, or resumable review → `langchain-human-in-the-loop`
- subagents, delegation, or agent/graph composition →
  `langchain-subagents-and-composition`
- task planning or other agent middleware → `langchain-middleware`
- indexed knowledge or retrieval tools → `langchain-retrieval-and-rag`

Load a peer because the requested behavior requires it, not merely because Deep
Agents is built on LangChain and LangGraph. Keep Deep Agents harness construction
in this skill and capability-specific details in the peer skill.

## Implementation principles

- Use `create_deep_agent` in Python or `createDeepAgent` in TypeScript for the
  Deep Agents harness.
- Add only the tools and configuration required by the application.
- Use the harness's execution, context-management, delegation, and steering
  capabilities instead of rebuilding equivalent scaffolding.
- Treat task planning as opt-in in current releases and verify behavior against
  the installed language package.
- Choose sandbox execution for shell commands, package installation, tests, or
  operating-system filesystem access. Choose an interpreter for lightweight
  in-process computation and programmatic tool calling.
- Treat filesystem permissions as a boundary for built-in file tools only.
  They are permissive when no rule matches and do not constrain custom tools,
  MCP tools, or sandbox shell execution.
- Keep boundaries explicit when a Deep Agent is embedded in a LangGraph node,
  exposed as a tool, or used alongside another agent.
- Verify behavior by exercising the application path the user asked for, not
  only by checking that the agent can be constructed.

## Boundaries

- Use `langchain-managed-deep-agents` for the Managed Deep Agents product and `mda` CLI.
  An open-source Deep Agent can also be deployed on LangSmith infrastructure;
  consult the current Deep Agents production guidance instead of assuming that
  every hosted deployment is MDA.
- Do not reproduce generic LangChain tool or middleware documentation here.
- Do not reproduce generic LangGraph persistence or interrupt protocols here.
- Do not assume every Deep Agent needs persistent memory, human approval,
  custom subagents, or user-authored skills.
