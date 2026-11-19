# Evals philosophy

The Harbor harness in `evals/` measures whether the skills in this repository
make coding agents more effective. **The `skill-claims` check keeps what a
skill says accurate against the docs; the harness checks whether that guidance
helps.** A skill helps when the agent loads it in the situations it was written
for, the work the agent produces is better, and the improvement is worth its
cost and latency compared with the same agent without the skill.
`evals/README.md` covers how to run tasks; this document covers which tasks to
add and what makes one good.

## What earns an eval task

Every skill has at least one task. A task targets a decision or workflow the
skill claims to improve, the same one named when the skill was proposed. Add
another task for a skill only when it changes the condition or the way the
agent can fail, such as a different framework, data shape, or service boundary,
as the three tracing tasks do. A reworded instruction is not a new task.

A task that checks a fact, flag, or command name tests the docs, not the
skill's judgment; leave that to `skill-claims`. Once a task has run for a few
weeks, one that every profile completes equally well, or none can complete,
does not separate the profiles and is not worth the cost of running it.

## What goes in a task

- **A realistic instruction.** Write what a user would ask their coding agent:
  the goal, the context they would have, and the result they expect. Name the
  outcome, not the skill, tool, commands, or steps; whether the agent finds the
  right guidance is part of what we measure.
- **A controlled environment.** Seed only what the user's project or workspace
  would contain. Prefer deterministic apps and synthetic data so every trial
  sees the same inputs. Keep `Task.md`, expected values, and held-out data
  outside `environment/`.
- **A minimal verifier.** State the outcome as one sentence, "Pass iff …", and
  check only what that sentence requires, from the end state: the resources
  created, the traces stored, the code's behavior. Accept every equivalent
  result. Do not require a particular tool, command sequence, wording, or file
  layout unless that choice is the capability under test. Use an LLM judge
  only for meaning that code cannot settle.
- **Human-reviewed alignment.** A person approves `Task.md` and confirms that
  the verifier agrees with their own judgment before its results count. Run it
  on a known-good result, a valid alternative, a realistic wrong result, and a
  shortcut, then read trajectories from real runs to confirm that passes and
  failures match what happened. Keep `Status: Draft` until then.

Most tasks are basic: one instruction, and the agent works until it finishes.
Use a simulation task, in which a model plays the user across several turns,
only when the skill's value depends on that dialogue, such as the
eval-engineering skill interviewing the user and waiting for approval. The
simulated user is part of the environment: review its persona and what it
knows as carefully as the verifier, so it neither leaks the answer nor
withholds what a real user would say.

## Comparing with and without skills

Every task runs with the same agent and model under three profiles: `none`
(no skills or documentation MCPs), `mcp-only` (the documentation MCPs), and
`full` (every skill plus the documentation MCPs). For each profile, record the
verifier outcome, cost, latency, and whether the agent loaded the skill the
task targets. `mcp-only` separates what the skill adds from what the docs
already provide.

A skill earns its place when `full` reaches the outcome more often, or reaches
the same outcome at lower cost or latency, than `mcp-only`. When it does not,
revise or remove the skill as described in `SKILLS_PHILOSOPHY.md`; do not tune
the task, or the skill's wording, around one prompt. One trial per profile is an
anecdote. Before attributing a result to a skill, read the trajectory and rule
out instruction, environment, verifier, and infrastructure defects, and compare
across several runs.

## Report, don't gate

For now, outcome checks are reported, not enforced: a failed check does not
fail the suite run. Failures of the harness itself, such as setup, agent
tracing, or cleanup, still fail the run because they make the results
unusable. Revisit gating once tasks have approved verifiers that stay stable
across several runs.

## How we maintain the harness

- Every task runs in each suite run. Add a new task to the workflow matrix in
  the same change that adds the task.
- When a skill changes materially, check that its tasks still target what the
  skill claims to improve, and update `Task.md` and the verifier together.
  Retire a task when its skill is removed or it no longer separates the
  profiles.
- Bump pins (Harbor, the agent version, the model, the LangSmith CLI, and the
  tracing plugin) deliberately and in their own commit, so changes between
  runs can be attributed to skills rather than to the harness. Keep them
  current enough that tasks exercise what users have.
- The repository, workflow logs, task prompts, and fixtures are public. Never
  put confidential content or real customer data in a task.
