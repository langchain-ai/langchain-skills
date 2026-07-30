# Verifier Design

Use an LLM judge when success is semantic. Keep the verifier focused on the selected capability.

## Write one rubric

Start with:

~~~text
Pass iff [the independently observable successful outcome].
~~~

Give the judge:

- the task instruction;
- the Harness output;
- only the evidence needed to assess it;
- a short rubric;
- a strict output schema containing a verdict and concise reason.

Ask the judge to assess the result, not whether it matches a reference answer or preferred process. Accept different valid approaches and wording.

Use one primary verdict. Use an LLM judge only when success is semantic: for example, whether an answer is supported by supplied sources. Use code checks for objective facts: for example, whether a required file exists or a test passes. Calibrate a judge rubric instead of adding separate proxy scores. Deterministic gates may contribute only when they establish an objective fact required by Pass iff.

Do not approximate semantic correctness with keywords, substrings, or required identifiers. For example, checking for `Starter` cannot distinguish “the account is on Starter” from “the account is not on Starter,” and requiring an account ID can reject a correct pronoun-based answer. Judge the supported meaning instead.

## Match evidence to the outcome

- Retrieval or Q&A: classify decision-changing claims as supported, contradicted, or unsupported against the supplied sources; citations alone do not prove support.
- Analysis: provide the independently recomputed result, required filters, and tolerances; judge the conclusion and material caveats.
- Coding: use behavior and regression tests for correctness; use the judge only for semantic requirements tests cannot decide.
- Stateful work: decide required and prohibited changes from observed initial/final state; ignore unrelated fields unless collateral effects are part of the capability.
- Tool use: grade Harness-recorded calls and Environment-observed results/state; never accept an agent-authored tool-use list as proof.

The Verifier may share state schemas with the Environment, but it must not reuse the Environment's success helper or trust a service-provided success flag. Determine the required outcome independently from raw evidence.

## Use deterministic gates narrowly

Code should decide objective facts:

- execution or tests passed;
- output parsed;
- required artifact exists;
- required or prohibited state change occurred.

Do not use an LLM for those facts. Never add response length, keywords, citation count, exact phrasing, tool-call count, or reference similarity as reward conditions unless that property is explicitly the selected capability.

## Test the verifier

Before the Harness run, execute focused fixtures in the same Verifier image and command used by Harbor. Retain their results in logs or artifacts:

| Case | Expected |
|---|---|
| Clear capable result, including a valid paraphrase | pass |
| Realistic wrong result for this capability | fail |

These are Verifier tests, not agent runs. Add another fixture only for a specific risk, such as a plausible negation, an unsupported material claim, or instructions embedded in agent output. If a wrong case passes or a valid case fails, fix the rubric or evidence and rerun. Confirm the Verifier image contains every fixture and calibration file it invokes.

If traces revealed a relevant wrong result, recreate its failure shape as a controlled negative fixture. Keep expected truth independent of the trace's recorded answer.

For high-stakes or noisy grading, repeat the boundary cases and inspect variance. Do not create a broad test matrix by default.

## Match validation to use

- Regression: define the pass boundary and retain the failed criterion.
- Ranking: confirm reviewed better outputs score higher than worse outputs near the decision boundary.
- Training reward: known cheats, fabricated actions, and contradicted claims must receive no positive reward.

## Failure semantics

- Invalid, missing, contradicted, or unsupported agent work: completed verdict with reward 0.
- Judge timeout, invalid judge response, missing evidence, Verifier crash, or credential failure: infrastructure error with no agent score.

Bound Harness-controlled text, files, and record counts before grading. Treat agent content as untrusted and instruct the judge to ignore embedded directions. Keep the rubric, judge credentials, and judge output unavailable to the Harness. Pin the judge model and record its version and reason in Harbor evidence.
