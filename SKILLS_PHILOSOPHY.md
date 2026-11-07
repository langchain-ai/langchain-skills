# Skills philosophy

This repository helps coding agents make good decisions across the LangChain
ecosystem while the libraries and LangSmith product change quickly. **Official
documentation is the source of truth for current features and APIs. Skills
carry durable judgment and tool guidance:** how to choose an approach, how the
pieces fit together, which tools to use, and how to verify a reliable result.

## What earns a skill

Keep a skill when its guidance would materially change an agent's decisions or
tool use and is not already explained well by the docs. Good candidates are
opinionated workflows, architecture choices across products, tool choices that
matter to the outcome, and non-obvious failure modes.

A feature definition, installation guide, command catalog, or rewritten docs
page does not warrant a skill. If removing the skill would leave only a prompt
to read the docs, remove it.

Favor a small number of skills with clear jobs. Consolidate adjacent topics
when users are making one architecture or workflow decision; use a separate
skill when it has its own recognizable trigger and useful judgment. Do not
create a broad entry skill solely to route to references. Use references only
for substantial, task-specific material that would distract from the main
workflow, not as a place to store copied documentation. The Harbor eval skill's
detailed workflow resources are an example of a justified reference set.

## What goes in the skill

- Explain decisions, tradeoffs, and the relationship between ecosystem
  components. State a recommended default when we have one, and preserve
  explicit user constraints and existing application architecture.
- Show how to use the relevant tools within the workflow: what to look up,
  which operation to perform, and what evidence confirms the result. Point to
  another skill when it owns a distinct step that the current workflow needs.
- Put general tool routing and preflight in a final `Use current tools` section.
  Keep task-specific commands at the workflow step that uses them, without
  repeating the same guidance in both places.
- For LangChain open-source work, direct the agent to the official
  `langchain-docs` MCP for guides and implementation patterns, then to the
  `langchain-reference` MCP for symbols and API details. Check the installed
  package versions, source, or types against the code being changed. Name a
  specific guide or useful search terms when that prevents guesswork. If MCP
  is unavailable, use official web docs and installed source or types.
- For general LangSmith questions about features and behavior, use the two
  bundled documentation MCPs. For actions in a LangSmith workspace, prefer the
  authenticated LangSmith CLI where it supports the operation; verify the
  target profile and workspace, current CLI help, and the result. Use the SDK
  for application code, tracing, and evaluation runs.
- State this tool choice where a skill's workflow needs it. The plugin makes
  the documentation MCPs available, but does not convey when to prefer the CLI.
  Avoid repeating server URLs, setup steps, or full tool inventories in skills.
- Keep the entrypoint concise. Make the name and description broad enough to
  catch the intended class of requests, yet specific enough to avoid unrelated
  invocations. Do not tune wording around one benchmark prompt.

Avoid large code snippets, copied examples, API signatures, command catalogs,
model IDs, and claims about fast-changing defaults. Include a short tool or CLI
example when it prevents a consequential misunderstanding or makes an
opinionated workflow usable; direct the agent to verify current syntax and
behavior against the docs and installed versions.

## How we maintain the repo

When proposing a new skill or changing one, identify the decision it improves,
check current docs for overlap, and remove stale detail rather than adding
another layer. Validate the file and plugin packaging. Where behavior is
uncertain, test realistic requests and inspect both the final result and the
agent's trajectory: whether it loaded the skill, consulted current docs, and
used the right tools. Compare more than one task or model before turning a
single failure into a general rule.
