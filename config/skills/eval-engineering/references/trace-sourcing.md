# Trace Sourcing

Use this reference only when the user provides a trace source or explicitly asks to use traces.

Traces show what users asked, what the agent did, which tools and data it used, and where it failed. They do not establish the correct answer.

## Scope

If the user's request already names the source and authorizes access, begin within that scope. Otherwise state, in one short message:

- the source and time window or local files;
- that the first batch is up to 25 complete traces;
- which fields are needed;
- where temporary exports will be stored and when they will be deleted.

Ask only for missing access or scope. Never print credentials or copy raw traces into the repository or a Harbor task.

## How to Select Traces

Use the source's native CLI, API, export, or local files. Preserve trace IDs or equivalent source identifiers.

Start by retrieving up to 25 complete traces. Select traces that let you compare good and bad agent behavior:

- a normal request that completed;
- a successful request where the user confirms the result;
- a request where the user corrects, rephrases, or adds a constraint;
- a trace with a failed, empty, or repeated tool call;
- a trace with an external failure such as a timeout, rate limit, or unavailable service.

For example, for an account-support agent, inspect a resolved plan question, a user correction after the agent looked up the wrong account, a repeated account lookup, and a rate-limit response.

Retrieve another batch only when a specific question remains unanswered: for example, whether a retry is common, which tool path succeeds, or whether the failure came from the target or an external service.

For each selected trace, retrieve what is available and relevant:

- user inputs and conversation/thread context;
- agent and model messages;
- tool names, arguments, results, ordering, retries, and errors;
- final output, status, latency, and model or agent revision;
- user feedback when present.

Compare good and bad behavior to identify capabilities to preserve or improve. Do not claim that a small selection represents production frequency.

## Analyze

Summarize only information that changes eval selection or environment design:

```text
Observed behavior: what the user asked and what the target did
Comparison: what worked and what did not
Attribution: target behavior, dependency behavior, or unclear
Eval candidate: capability to preserve or improve, if independently judgeable
```

Example:

```text
Observed behavior: user asks for an account's plan; target calls account lookup twice with the same ID.
Comparison: the first lookup returned the plan; the second call added no information.
Attribution: target loop.
Eval candidate: use returned account data to answer without repeating the lookup.
```

Use traces to source realistic requests and reproduce relevant dependency behavior. A failed tool call is not automatically an agent failure: a repeated lookup with the same arguments may indicate a target loop, while a 429 may indicate an upstream limit. Use an external failure as an eval direction only when the target has an expected recovery behavior, such as choosing an alternative or clearly reporting the limit. Use tests, source records, policy, known state, computation, accepted artifacts, or expert review as judge evidence. Never use the recorded target answer as hidden truth.

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
