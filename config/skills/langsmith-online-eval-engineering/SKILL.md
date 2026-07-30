---
name: langsmith-online-eval-engineering
description: Iteratively inspect traces, interview the user, and create LangSmith online evaluators one at a time. Use specifically for creating online evaluators for use within LangSmith -- use "eval-engineering" for Harbor-style online evaluations. 
---

# Online Eval Engineering

Build online evaluators iteratively:

```text
inspect traces and interview user -> propose directions -> user chooses
-> build evaluator -> test, attach, verify -> review and repeat
```

Read [references/langsmith-api.md](references/langsmith-api.md) before creating or modifying evaluators.

## 1. Inspect traces

Ask the user for their LangSmith project name. Fetch recent root-level traces and print their structure. Read [references/trace-inspection.md](references/trace-inspection.md). Find:

- run name and type;
- available input and output field names;
- the shape and content of the data (truncated samples);
- which fields carry the data an evaluator would need.

Summarize the trace structure in the conversation:

```text
Project: name
Run type: chain | llm | tool | ...
Input fields: field names and what they contain
Output fields: field names and what they contain
Sample: one representative input/output pair (truncated)
```

Keep the user involved: explain the trace structure and what it implies, then ask only for information the traces cannot establish. For example: "What does this application do?", "What quality concern matters most?", or "What failure should never happen?"

Ask whether the user wants a naming prefix for evaluators in this session (e.g., `myapp-`, `v2-`, `dogfood-`). If they provide one, apply it to all evaluator names, prompt hub handles, and run rule display names. If they decline, use plain descriptive names.

Do not propose evaluators until the trace structure is understood and the user has described their concerns.

## 2. Discuss and choose an eval direction

Read [references/evaluator-design.md](references/evaluator-design.md). Propose two or three evaluation criteria grounded in the trace data. Apply the naming prefix from step 1 if the user provided one. For each, give:

```text
Name: descriptive evaluator name (with prefix if set)
Type: LLM-as-judge or code
Measures: what quality dimension this evaluates
Scoring: bool, float (0-1), or int; what pass/fail means
Fields needed: which trace fields are used and how
Rationale: why this type and approach
```

Example:

```text
Name: response-relevance
Type: LLM-as-judge
Measures: whether the response addresses the user's question
Scoring: bool; True = relevant, False = off-topic or non-responsive
Fields needed: input (user question), output (assistant response)
Rationale: relevance is semantic and requires reading comprehension; not decidable by code
```

Recommend one and ask the user which to build. Do not implement until the user chooses.

## 3. Build one evaluator

Read [references/langsmith-api.md](references/langsmith-api.md). Build the selected evaluator. Show the full configuration to the user and get approval before executing any API calls.

**LLM-as-judge path.** Define a `ResponseSchema` with `reasoning` first, then the score field. Write prompt messages with a clear rubric that assesses the result, not whether it matches a reference answer. Set `variable_mapping` using field names discovered in step 1. Present the schema, prompt, variable mapping, and evaluator name for approval. On approval, push the prompt and create the evaluator. Report the evaluator ID.

**Code evaluator path.** Write a `perform_eval(run, example=None)` function. It must be self-contained (only builtins and standard library), access `run` as a dict (`run.get("outputs")`), and return `{"key": ..., "score": ..., "comment": ...}`. Present the function code and evaluator name for approval. On approval, create the evaluator. Report the evaluator ID.

## 4. Test, attach, and verify

Before attaching, ask the user what sampling rate they want (1.0 = every trace, 0.5 = half, 0.1 = 10%, or custom). Do not default silently. If the user is unsure, recommend 1.0 for initial testing.

Ask the user whether they want to test the evaluator against a few existing traces before attaching. Run rules only fire on new traces, so historical testing is the only way to verify before new traffic arrives.

For code evaluators, execute `perform_eval` directly against fetched root-level traces, passing a dict with `inputs`, `outputs`, and `attachments` keys. This catches runtime errors (wrong field names, dict-vs-object access, missing data) before production. For LLM evaluators, verify the configuration: confirm `variable_mapping` keys match prompt placeholders, confirm mapped trace fields exist, and check that the mapped data is meaningful.

If testing reveals errors, fix and recreate before attaching. If the user declines testing, proceed to attach.

Create a run rule to connect the evaluator to the tracing project. Apply the user's naming prefix to the `display_name`. Confirm the evaluator appears in the evaluator list with the correct project attachment. Inspect:

- evaluator attachment and run rule status;
- recent trace feedback and scores (from historical testing or new traces);
- whether scores match expectations for the traces inspected;
- edge case handling (empty output, errored runs, unexpected structure).

Fix and reattach when the evaluator crashes, scores incorrectly, or fails on edge cases. Before approval, confirm the evaluator scored the intended quality dimension, not an infrastructure or data-shape failure.

## 5. Review with the user

Explain the evaluator name and ID, quality dimension and scoring approach, trace fields used, sampling rate, and any limitation. Ask the user to approve, revise, drop, or choose the next direction. If continuing, reuse the trace findings, then propose a distinct quality dimension.

## Invariants

- One quality dimension per evaluator.
- No guessing field names; always inspect traces before implementing.
- Show configuration and get user approval before making API calls.
- Code evaluators must be self-contained: only builtins and standard library.
- Code evaluators receive `run` as a plain dict; use `run.get("inputs")` and `run.get("outputs")`, not attribute access. The `example` parameter must default to `None`.
- Treat API failures, auth errors, and run rule failures as infrastructure errors, not evaluator bugs.
