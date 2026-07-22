# Trace Sourcing

Use this reference only when the user provides a trace source or explicitly asks to use traces.

Traces show what users asked, what the agent did, which tools and data it used, and where it failed. They do not establish the correct answer.

## Scope

If the user's request already names the source and authorizes access, begin within that scope. Otherwise state, in one short message:

- the source and time window or local files;
- that the initial sample is at most 25 complete traces;
- which fields are needed;
- where temporary exports will be stored and when they will be deleted.

Ask only for missing access or scope. Never print credentials or copy raw traces into the repository or a Harbor task.

## Retrieve a small complete sample

Use the source's native CLI, API, export, or local files. Preserve trace IDs or equivalent source identifiers.

For each sampled trace, retrieve what is available and relevant:

- user inputs and conversation/thread context;
- agent and model messages;
- tool names, arguments, results, ordering, retries, and errors;
- final output, status, latency, and model or agent revision;
- user feedback when present.

Start with at most 25 varied traces. Include common requests, different tool paths, failures, unusual cases, and multi-turn threads when relevant. Pull more only when a named behavior, tool contract, failure mode, revision, or environment question remains unresolved.

Do not claim that a small sample represents production frequency.

## Analyze

Summarize only information that changes eval selection or environment design:

```text
User work: recurring requests seen in the sample
Agent behavior: decisions, tool paths, retries, and outputs
Environment: data, tools, state, permissions, and failures
Eval opportunities: capabilities or failures with independently judgeable outcomes
```

Use traces to source realistic requests and reproduce relevant dependency behavior. Use tests, source records, policy, known state, computation, accepted artifacts, or expert review as judge evidence. Never use the recorded target answer as hidden truth.

Delete temporary raw exports according to the stated retention plan after the required analysis and task validation are complete.

## LangSmith example

When the user supplies a LangSmith project, use the official `langsmith` CLI:

```bash
langsmith trace stats --project <project> --last-n-minutes <window>

langsmith trace list \
  --project <project> \
  --limit <metadata-limit> \
  --include-metadata \
  --include-feedback \
  --show-hierarchy

langsmith trace export <temporary-outside-repo-dir> \
  --project <project> \
  --trace-ids <comma-separated-ids> \
  --full
```

Confirm that the export contains child model and tool runs. `LANGSMITH_API_KEY` is needed only for this source. Do not require LangSmith for local files or another tracing provider.
