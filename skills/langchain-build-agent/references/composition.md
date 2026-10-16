# Composition

Choose a boundary because it improves the application:

- A tool exposes a narrow operation and result.
- A subagent offers focused instructions, tools, or a separate working context.
- A graph or subgraph provides explicit state and control over a workflow.
- Keep work in the main agent when delegation adds no useful separation.

At each boundary, define input, result, state owner, visible context, tools,
permissions, failure handling, and continuation behavior. Pass focused input
instead of blindly forwarding full message history or graph state. Map results
back to explicit state updates using the receiving application's actual schema.

Retrieve current composition and delegation documentation for the selected
language/runtime. Inheritance of models, tools, memory, middleware, skills,
approval policy, storage, and permissions is API-specific. Verify the relevant
settings instead of copying a generic inheritance table.

Use background work only when responsiveness, steering, or independent lifecycle
is needed. Define cancellation and abandoned-work cleanup. Give isolated workers
enough context to complete their bounded task.

Exercise the integrated path, including failure, retry, interruption, and
streaming when required. A component working alone does not establish correct
state translation or persistence when embedded in another workflow.
