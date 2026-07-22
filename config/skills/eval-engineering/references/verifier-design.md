# Verifier Design

Use an LLM judge when success is semantic. Keep the verifier focused on the selected capability.

## Write one rubric

Start with:

~~~text
Pass iff [the independently observable successful outcome].
~~~

Give the judge:

- the task instruction;
- the target output;
- only the evidence needed to assess it;
- a short rubric;
- a strict output schema containing a verdict and concise reason.

Ask the judge to assess the result, not whether it matches a reference answer or preferred process. Accept different valid approaches and wording.

Use one primary verdict. Use an LLM judge only when success is semantic: for example, whether an answer is supported by supplied sources. Use code checks for objective facts: for example, whether a required file exists or a test passes. Calibrate a judge rubric instead of adding separate proxy scores. Deterministic gates may contribute only when they establish an objective fact required by Pass iff.

## Match evidence to the outcome

- Retrieval or Q&A: classify decision-changing claims as supported, contradicted, or unsupported against the supplied sources; citations alone do not prove support.
- Analysis: provide the independently recomputed result, required filters, and tolerances; judge the conclusion and material caveats.
- Coding: use behavior and regression tests for correctness; use the judge only for semantic requirements tests cannot decide.
- Stateful work: decide required and prohibited changes from observed initial/final state; ignore unrelated fields unless collateral effects are part of the capability.
- Tool use: grade calls and state observed by the harness; never accept a target-authored tool-use list as proof.

## Use deterministic gates narrowly

Code should decide objective facts:

- execution or tests passed;
- output parsed;
- required artifact exists;
- required or prohibited state change occurred.

Do not use an LLM for those facts. Never add response length, keywords, citation count, exact phrasing, tool-call count, or reference similarity as reward conditions unless that property is explicitly the selected capability.

## Test the verifier

Before the actual-target run, pass two fixtures directly to the verifier:

| Case | Expected |
|---|---|
| Clear capable result | pass |
| Plausible but wrong result | fail |

These are verifier tests, not Harbor agent runs. Add another fixture only when it targets a specific risk, such as rejecting a materially different valid answer or following instructions embedded in target output. If a wrong case passes or a valid case fails, fix the rubric or evidence and rerun the fixtures.

For high-stakes or noisy grading, repeat the boundary cases and inspect variance. Do not create a broad test matrix by default.

## Match validation to use

- Regression: define the pass boundary and retain the failed criterion.
- Ranking: confirm reviewed better outputs score higher than worse outputs near the decision boundary.
- Training reward: known cheats, fabricated actions, and contradicted claims must receive no positive reward.

## Failure semantics

- Invalid, missing, contradicted, or unsupported target work: completed verdict with reward 0.
- Judge timeout, invalid judge response, missing evidence, verifier crash, or credential failure: infrastructure error with no target score.

Bound target-controlled text, files, and record counts before grading. Treat target content as untrusted and instruct the judge to ignore embedded directions. Keep the rubric, judge credentials, and judge output unavailable to the target. Pin the judge model and record its version and reason in Harbor evidence.
