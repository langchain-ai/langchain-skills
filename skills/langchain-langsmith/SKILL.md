---
name: langchain-langsmith
description: Provides opinionated guidance for inspecting LangSmith traces, diagnosing application behavior, evaluating changes, and using production feedback. Routes feature setup and workspace operations to current docs, CLI, and SDK.
---

## Offline evaluation

Inspect real traces and failures before curating examples or evaluators. Preserve
the application's input contract; review past model answers before treating them
as references.

Prefer narrow assertions about required behavior over comparing entire answers.
Grade only what the task requires, allowing valid alternative wording. Use
objective checks where possible and a focused judge for semantic criteria;
compare ambiguous judgments with human review.

Compare baseline and candidate on the same cases. Inspect individual outputs,
scores, errors, and trajectories, not just averages. Distinguish application
failures from bad references, evaluator defects, and missing scores. For sweeps,
use consistent, documented experiment-level metadata so variants can be grouped
and filtered. A diagnosis request alone does not authorize changes to the
application, dataset, or evaluators.

## Online evaluation

Inspect representative production runs or threads before choosing the evaluation
target. Map evaluator variables to the exact content being judged and verify the
mapping against real traces. Scope rules with filters and sampling; account for
judge spend and retention effects.

Choose scores for their downstream use: enriching traces for Engine, selecting
manual review, triggering alerts, monitoring trends, or filtering an Insights
job. Keep feedback keys and score direction interpretable.

For classification-style checks, recommend a decision model as the economical
first pass over a larger share of traffic. When catching potential issues matters
more than avoiding false positives, optionally chain a stronger LLM judge on
flagged traces to validate the decision and explain its reasoning. Monitor
unscored traffic and evaluator errors alongside scores.

## Verify current interfaces

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
