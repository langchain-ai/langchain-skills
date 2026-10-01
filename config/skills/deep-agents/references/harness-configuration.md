# Deep Agents harness configuration

Use this reference when adding or changing a Deep Agent in an application.
Confirm the installed package version and current official documentation before
relying on an exact constructor option or import path.

Read the [Python](python.md) or [TypeScript](typescript.md) reference for
language-specific construction, invocation, and graph-node examples.

## Capability model

Deep Agents uses the same core tool-calling loop as other LangChain agents and
the LangGraph runtime for durable execution. The harness groups its additional
capabilities into four areas.

### Execution environment

- **Tools and MCP:** Accept custom functions, LangChain tools, and tools from
  Model Context Protocol servers.
- **Virtual filesystem:** Provide file tools backed by in-memory state, local
  disk, a LangGraph store, composite routing, or a custom backend.
- **Filesystem permissions:** Restrict read and write operations with ordered
  path rules. Use these to scope workspace access and protect secrets or other
  sensitive files.
- **Code execution:** A sandbox backend supplies an `execute` tool for shell
  commands, package installation, tests, CLIs, and operating-system filesystem
  access. An interpreter supplies an in-process `eval` tool for loops,
  batching, deterministic transformations, and programmatic tool calling; it
  does not provide shell, filesystem, package, or network access.
- **Streaming:** Typed event streams expose messages, tool calls, state values,
  output, and delegated subagent activity.

The core virtual filesystem surface includes tools such as `ls`, `read_file`,
`write_file`, and `edit_file`. Backend capabilities determine whether
additional execution tools are available. Use supported profiles and tool
allowlists to hide model-visible tools; do not try to remove middleware that
the harness requires as scaffolding.

### Context management

- **Skills:** Load task-specific instructions progressively from Agent Skills
  directories. Skill metadata is available at startup and full content is read
  when relevant.
- **Memory:** Load persistent instructions and preferences from `AGENTS.md`
  files supplied through the agent's memory configuration. Unlike skills,
  memory content is loaded at startup.
- **Summarization and offloading:** Compress growing conversation history and
  large intermediate results so long-running tasks can stay within context
  limits.
- **Prompt caching:** Reuse static prompt sections on supported providers. The
  harness applies caching automatically for supported Anthropic and Amazon
  Bedrock models; consult current provider guidance for other integrations.

Keep the distinction between thread state, durable storage, startup memory,
and on-demand skills explicit. They solve different context and persistence
problems.

### Delegation

- **Subagents:** The built-in `task` tool delegates isolated work to ephemeral
  child agents. A default general-purpose subagent is available unless the
  harness is configured to hide it; custom subagents can provide specialized
  instructions or tools.
- **Task planning:** Planning is opt-in in current releases. In Python Deep
  Agents v0.7 and later, add `TodoListMiddleware` when structured task tracking
  helps with long, multi-step work or progress-oriented user interfaces. Check
  the installed language package before configuring it, and do not assume
  `write_todos` is available by default.

Subagents have fresh context, run autonomously, return one final result, and do
not provide a continuing message channel between invocations.

### Steering

- **Human-in-the-loop:** Configure `interrupt_on` to pause before sensitive
  tool calls so a person can approve, edit, or reject the action.
- **Filesystem permissions:** Use path-based permissions to constrain the work
  the agent and its subagents may perform.

These capabilities do not prevent composition. A Deep Agent can be invoked
inside a LangGraph node, supplied as a component of a larger application, or
used alongside ordinary LangChain agents.

## Configuration ownership

Keep harness-specific construction here and route shared behavior to its
capability guidance:

| Concern | Deep Agents-specific responsibility |
|---|---|
| Model and instructions | Pass the application's selected model and agent instructions to the harness. |
| Tools and MCP | Supply only the custom and remote tools required by this agent. |
| Planning | Add task-planning middleware only when structured task tracking is useful. |
| Filesystem context | Select a backend and permission rules appropriate to the execution environment. |
| Code execution | Choose a sandbox for shell and operating-system access or an interpreter for restricted in-process computation. |
| Streaming | Select the message, tool, value, output, and subagent streams required by the caller or UI. |
| Context management | Decide which information belongs in prompts, startup memory, on-demand skills, or durable storage. |
| Delegation | Register specialized subagents only when the task benefits from isolated context or tools. |
| Persistence | Supply the appropriate checkpointer, store, and thread identity according to the application's persistence design. |
| Human approval | Configure tool interruption according to the application's approval policy. |
| Skills | Supply skill locations and backend access appropriate to the runtime. |

Do not infer that every row is required. Start with the smallest configuration
that satisfies the application.

## Composition

When placing a Deep Agent inside a LangGraph workflow, define the boundary
between graph state and agent input/output. Avoid passing an entire graph state
object when the agent needs only a focused message or task. Map the agent's
result back to explicit state updates.

When using an existing LangChain agent or compiled graph as a delegated
component, preserve its own tools, persistence, and state contract. Do not
silently replace it with a Deep Agent merely to make the composition uniform.

## Verification

Exercise the real integration boundary:

- confirm the intended tools are available and selected correctly;
- confirm filesystem permissions and execution tools match the intended trust
  boundary;
- confirm messages and results are mapped correctly at graph boundaries;
- confirm filesystem, delegation, planning, and code-execution tools appear
  only when intended;
- exercise the streaming mode consumed by the caller or user interface;
- verify long-running behavior when the design relies on summarization,
  offloading, or persistent context;
- test continuity, approval, or persistence separately when the application
  requests those capabilities.
