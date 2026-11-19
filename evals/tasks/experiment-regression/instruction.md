Our customer-support agent is in `/app/support_agent.py`, and we're about to
start changing it with no regression checks in place. Our support lead wrote
down what a correct answer must do for each of our test questions in
`/app/cases.md`.

Set us up in LangSmith so we can catch regressions. Put the cases in a dataset
named after the `TARGET_DATASET_NAME` environment variable, then run an
experiment of the current agent against it that scores each requirement
separately, so a failing case shows which requirement broke.

Don't change the agent; we want to know how it behaves today. When you're
done, tell us which cases fail and why.
