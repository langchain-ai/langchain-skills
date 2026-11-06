# LangSmith offline evaluation

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
