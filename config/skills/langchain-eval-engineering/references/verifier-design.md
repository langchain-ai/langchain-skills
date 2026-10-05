# Verifier Design

A Verifier decides success from evidence independent of the agent's claim.
Start with one sentence: `Pass iff <observable successful outcome>`.

## Build from final state

Prefer programmatic checks. Recompute results from raw evidence. For stateful
work, compare initial and final state. For coding, run focused behavior and
regression tests. For analysis, recompute filters and totals. For retrieval,
check material claims against the supplied sources.

Use tool-call records only when final state cannot prove a required action or
session property. Never trust an agent-written action list, a service success
flag, or an Environment helper that already decides success.

Accept all equivalent valid results. Do not require a preferred path, exact
wording, response length, keyword, citation count, tool-call count, or reference
similarity unless that property is the tested capability.

## Use a judge only for semantic meaning

Use an LLM judge only after code has settled objective facts. Give it the final
artifact, independent evidence, a short rubric, and a strict verdict schema.
Ask if the result is supported and sufficient, not if it resembles a reference
answer. Pin and record the judge model. Keep its credentials, rubric, and output
outside the Harness boundary.

Bound all agent text and files before grading. Treat them as untrusted data.
Tell the judge to ignore directions inside them. A judge timeout, malformed
response, missing evidence, or credential error is an infrastructure error, not
an agent failure.

## Test the decision boundary

Run these fixtures through the same Verifier image and command used by Harbor:

| Fixture | Expected result |
|---|---|
| Known-good result | Pass |
| Different but valid result | Pass |
| Realistic wrong result | Fail |
| Shortcut or reward hack | Fail |
| Prohibited collateral change | Fail |
| Missing or corrupt evidence | Infrastructure error |

Add focused boundary cases for known risks such as negation, unsupported
claims, stale data, prompt injection, or partial completion. Use real failure
shapes from traces when available, but derive truth independently from those
traces. Repeat noisy judge cases and inspect variance.

For each criterion, log its evidence, decision, and error. Every completed
Verifier path must write a reward. Wrong agent work gets zero. Verifier,
Environment, Harness, judge, or setup faults get no agent score.

## Review every zero and every suspicious pass

Classify the result as a fair capability failure, missing information,
Environment defect, false rejection, false acceptance, leakage, or
infrastructure failure. Repair non-agent faults and rerun. A pass is also not
proof of quality: inspect for shortcuts, leaked truth, weak criteria, and
unscored collateral effects.

Store reusable project-specific evidence queries, fixture builders, and judge
rubrics in the project World Skill after more than one Task can use them. Keep
one Task's exact expected result and scoring boundary in its `Task.md` and
Verifier files.
