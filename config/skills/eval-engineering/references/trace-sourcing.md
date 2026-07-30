# Trace Sourcing

Use this reference only when the user provides a trace source or asks to use traces.

## Scope

Traces supplement repository code, tests, issues, and user priorities. They show what happened, not what should have happened. The initiating actor may be a person, another agent, an API call, an event, or a scheduled job.

If the user has not already specified scope, state the source, time window or files, first-batch size, required fields, and temporary storage. Ask only for missing access or scope. Keep raw exports outside the repository and delete them after analysis and task validation. Never print credentials.

## Retrieve traces

Start with up to 25 complete traces from the supplied scope. Retrieve, when available:

- initiating input, context, and the full thread when prior turns matter;
- agent/model messages and child runs;
- tool calls, arguments, results, ordering, retries, and errors;
- final output, status, feedback or other outcome evidence;
- agent revision and relevant configuration.

Preserve trace IDs or equivalent source identifiers. Remove duplicate exports; retain retries inside the complete trace.

Pull another batch only to answer a concrete gap found during review. Example: if the first batch contains only `search_docs` timeouts, retrieve successful `search_docs` calls to learn the normal result schema. Do not claim production frequency from a small batch.

## Review the batch

Record only what is observable:

```text
Work requested:
Context:
Harness behavior:
Dependency behavior:
Outcome evidence:
Possible relevance: Harness, Environment, task, Verifier, or none
```

Outcome evidence may be user feedback, resulting state, a test result, or an external status. Absence of outcome evidence is not failure. A tool error is not automatically a Harness error: repeated identical calls may indicate a loop, while a service `429` describes dependency behavior.

## Summarize relevant evidence

Group only patterns that appear and affect an eval decision:

```text
Pattern:
Observed in: trace IDs
What happened:
What it may inform:
Limitation:
```

Do not force good/bad pairs or turn every pattern into an eval. Compare successful and unsuccessful behavior when the batch supports that comparison.

## Use traces in the eval

Choose eval directions from the combined repository, tests, issues, user priorities, and traces. A direction does not need trace support. When traces do affect it:

- **Harness:** preserve relevant prompts, control flow, tool use, retries, and session behavior.
- **Environment:** reproduce relevant schemas, ordering, pagination, permissions, errors, and state through the production interface, using controlled data rather than copied production records.
- **Task:** preserve the condition that exercised the capability, not the exact production interaction.
- **Verifier:** use independent truth; a trace-like bad result may be a negative calibration fixture, never the hidden answer.

After a run, confirm that the task reproduced the cited condition and the Verifier scored the intended Harness behavior rather than a dependency or infrastructure artifact.

## LangSmith commands

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

Confirm that exports contain child model and tool runs. `LANGSMITH_API_KEY` is required for this source.
