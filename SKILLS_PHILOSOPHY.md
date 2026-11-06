# Skills philosophy

This repository helps coding agents make good decisions across the LangChain
ecosystem while the libraries and LangSmith product change quickly. **Official
documentation is the source of truth for current features and APIs. Skills
carry durable judgment:** how to choose an approach, how the pieces fit
together, and which workflow tends to produce a reliable result.

## What earns a skill

Keep a skill when its guidance would materially change an agent's decisions
and is not already explained well by the docs. Good candidates are opinionated
workflows, architecture choices across products, and non-obvious failure modes.
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
- Tell the agent where to verify implementation details: official guides MCP
  for workflows, API-reference MCP for symbols, and installed package versions
  for the code actually being changed. If MCP is unavailable, use official web
  docs and installed source or types.
- For LangSmith work, use current docs for feature behavior; use the
  authenticated CLI for supported workspace operations and the SDK for
  application code and evaluation runs. The plugin registers docs MCPs but
  does not install or authenticate the CLI.
- Keep the entrypoint concise. Make the name and description broad enough to
  catch the intended class of requests, yet specific enough to avoid unrelated
  invocations. Do not tune wording around one benchmark prompt.

Avoid large code snippets, copied examples, API signatures, CLI flag lists,
model IDs, and claims about fast-changing defaults. Include a concrete
identifier only when it prevents a consequential misunderstanding; still
direct the agent to verify it against current docs and installed versions.

## How we maintain the repo

When proposing a new skill or changing one, identify the decision it improves,
check current docs for overlap, and remove stale detail rather than adding
another layer. Validate the file and plugin packaging. Where behavior is
uncertain, test realistic requests and inspect both the final result and the
agent's trajectory: whether it loaded the skill, consulted current docs, and
used the right tools. Compare more than one task or model before turning a
single failure into a general rule.
