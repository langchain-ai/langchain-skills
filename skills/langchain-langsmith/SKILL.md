---
name: langchain-langsmith
description: Use whenever a user wants to understand or accomplish something in or with LangSmith. Provides current guidance and points to authoritative documentation and appropriate tools.
---

# Work with LangSmith

## Use current interfaces

Use the official guides MCP for current workflows and the API-reference
MCP for SDK details. For supported workspace queries and resource operations,
use an authenticated LangSmith CLI profile; verify the target workspace and
check installed CLI help. If the CLI is absent, follow the official
https://docs.langchain.com/langsmith/langsmith-cli setup guide; the plugin does
not install it. Use the SDK in application code for tracing and
dataset evaluation runs. For operations the CLI does not cover, use the
documented SDK or API. If MCP is unavailable, consult
https://docs.langchain.com/llms.txt and https://reference.langchain.com/llms.txt.
Verify installed versions rather than assuming an interface.

## Offline evaluation

For offline evaluation design, experiment comparison or diagnosis, read
[evaluation.md](references/evaluation.md). Use current documentation for
feature setup and API details. For online evaluation, use the standalone
`langsmith-online-evaluation` skill.
