# Synthetic Data

Create structured truth with deterministic code. Use a model only for fields
that need natural language or semantic variation.

## Build structured truth first

Define IDs, relationships, permissions, dates, state, constraints, and edge
cases in code. Use a fixed seed. Materialize the result so each trial gets the
same data. Validate foreign keys, event order, permissions, counts, and required
scenario conditions before generating prose.

Create a relationship-complete subset. Each record must support the intended
decision, a named distractor, or a required relationship. Do not use answer-coded
names, insertion order, a single obvious choice, or unrelated noise.

## Generate prose from facts

Give the generator one structured request per output. Include:

- stable request and target IDs;
- allowed source facts with fact IDs;
- document type and workflow position;
- required and prohibited claims;
- time bounds and output fields; and
- a rubric version.

The generator must use only supplied facts and return the fact IDs it used. It
must not invent keys, permissions, source facts, or the planned Task answer.
Keep the request, output, generator identity, and content hash.

## Separate generation from review

When volume warrants it, generate independent records in parallel. Validate
shape with code, then use a separate reviewer for meaning. Do not show the
reviewer another review.

Review every output for:

| Check | Question |
|---|---|
| Facts | Does each factual claim match an allowed fact? |
| Time | Are dates and event order valid? |
| Relations | Are people, teams, records, and products connected correctly? |
| Fit | Does the content fit its document type and workflow point? |
| Distinctness | Is it specific and not a near-duplicate? |
| Safety | Does it avoid private data, hidden answers, and agent directions? |

Require pass or fail and evidence for each check. Use code for JSON shape, IDs,
date and length bounds, prohibited literals, duplicate hashes, strong overlap,
and content-hash matching. Use a reviewer only for meaning that code cannot
settle.

Merge only accepted content. Use one transaction. Reject missing, changed,
repeated, or failed requests. Validate the complete world after the merge.

## Test Task quality

Before model runs, inspect ordinary, boundary, and rejected records with their
source facts. Confirm that the Task is solvable through normal discovery and
that data does not reveal the expected result. Run the reference path and the
Verifier fixtures. When model contrast answers a named uncertainty, inspect
the selected traces for confusing records, accidental clues, and unsupported
shortcuts. Do not require weak-and-strong model runs for every Task.

Put reusable project schemas, generators, validation rules, and safe examples
in the project World Skill. Keep a Task's focal records and exact expected
answer in its collocated `Task.md` and Environment assets.
