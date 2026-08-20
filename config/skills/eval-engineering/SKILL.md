---
name: eval-engineering
description: Inspect an agent repository and optional traces, interview the user, write reviewed Task Specs, build and audit Harbor tasks, and bootstrap reusable project World Knowledge Skills. Use for agent evals, benchmark design, Task generation, controlled Environments, synthetic data, Verifiers, Harbor runs, calibration, or continuous benchmark maintenance.
---

# Eval Engineering

## Flow

- Inspect all inputs first: the repository, Harness, optional traces, existing
  Tasks and runs, existing World knowledge, and the human goal. Identify the
  source files and skill references that apply before proposing work.
- Create or update the small project World Knowledge Skill from reusable facts
  in those inputs. Use it to propose one grounded Task.
- Draft the Task Spec and World Skill together. Show both to the user, keep exact
  Task truth only in `Task.md`, and refine both until the user approves them.
- Implement the approved Task, validate its Environment and Verifier, run the
  real Harness, inspect the full evidence, and fix only non-agent failures.
- Reconcile the World Skill with what the run proved, then repeat this flow for
  the next Task.

## Terms

- **Task Spec:** `Task.md`, which describes the input, relevant agent
  conditions, Environment, scoring, fairness, and open decisions for one Task.
- **Task:** the runnable instruction, Environment, and Verifier.
- **Harness:** the complete agent Harbor runs, including prompts, model loop,
  tools, hooks, memory, sessions, and adapter.
- **Environment:** the files, data, services, identity, permissions, network,
  clock, and mutable state around the Harness.
- **Verifier:** independent checks that score the result or mark a run invalid.
- **World Knowledge Skill:** a repository-local skill with reusable
  project-specific knowledge, references, scripts, assets, and tests that help
  generate Task Specs and build future Tasks.
- **Spec2Task:** the full loop that turns a reviewed Task Spec into an audited
  runnable Task. Follow [Task implementation](references/task-implementation.md)
  for its concrete build order and reference routing.

## Reference routing

Read each reference when its decision appears:

| Need | Read |
|---|---|
| Inspect source, traces, the Harness, dependencies, access, and existing evals | [Discovery](references/discovery.md) |
| Bootstrap or update reusable project knowledge | [World knowledge](references/world-knowledge.md) |
| Propose Tasks and write the single Task Spec | [Task design](references/task-design.md) |
| Build data, services, access, state, and reset | [Environment building](references/environment-building.md) |
| Create structured or natural-language data | [Synthetic data](references/synthetic-data.md) |
| Define independent evidence and scoring | [Verifier design](references/verifier-design.md) |
| Apply Spec2Task to turn a reviewed Spec into an audited Task | [Task implementation](references/task-implementation.md) |
| Compare model runs and classify failures | [Calibration](references/calibration.md) |
| Package and run Harbor tasks | [Harbor](references/harbor.md) |
| Adapt a known benchmark design | [Benchmark patterns](references/patterns.md) |
| Build multi-turn conversations | [Multi-turn simulation](references/multi-turn-simulation/guide.md) |
| See World knowledge learned across two Tasks | [Service-desk example](references/examples/service-desk.md) |

Reusable implementation resources:

- Multi-turn [runner](references/multi-turn-simulation/runner.py), [model user](references/multi-turn-simulation/model_user.py), and [Harbor adapter example](references/multi-turn-simulation/harbor_example.py)
- [Tool-schema comparison](scripts/compare_tool_schemas.py), which compares
  supplied schema fragments but does not resolve external `$ref` targets
- [Read-only SQLite state snapshot](scripts/snapshot_sqlite_state.py)

## 1. Inspect inputs and existing World knowledge

Review every input the user provides before proposing a Task. Use the guidance
that matches each available input:

- For a repository, Harness, traces, or dependencies, read
  [Discovery](references/discovery.md).
- For existing Tasks and runs, inspect their instructions, Environments,
  Verifiers, rewards, trajectories, and final state. Read
  [Calibration](references/calibration.md) when run quality or failure causes
  affect the new design.
- For an existing project World Skill, read
  [World knowledge](references/world-knowledge.md), then check the sources and
  reusable methods that affect the new Task.
- For human goals and constraints, read
  [Task design](references/task-design.md).
- For relevant benchmark examples, use the domain index and source callouts in
  [Benchmark patterns](references/patterns.md).

Inspect the repository before asking questions that source and tests can
answer. Follow the active Harness through prompts, models, tools, services,
state, effects, and focused tests. Inspect existing Task instructions, parsers,
Verifiers, reward paths, and run evidence.

If the user supplies traces, review complete runs or threads. Use traces to
learn real requests, dependency behavior, state shapes, errors, and failure
conditions. Do not treat a trace answer as independent truth.

If `.agents/skills/<project>-world/SKILL.md` exists, read it. Follow its routing
only for knowledge relevant to the current Task. Check cited repository paths,
commands, and scripts when their accuracy affects the design.

## 2. Propose and select a Task

Read [Task design](references/task-design.md) and use the index in
[Benchmark patterns](references/patterns.md) to find the relevant domain and
source callouts. Focus on that domain unless the Task crosses another one.
In the first user-facing design response after inspection, propose one Task
grounded in repository evidence, supplied traces, existing coverage, or a
human priority. State:

- the real work and capability;
- the condition that makes the case non-trivial;
- the Environment and independent evidence it needs;
- the important failure it can detect;
- how it differs from existing Tasks; and
- the main open decision.

In the same response, show the relevant current World Skill content and the
specific additions or corrections this Task suggests. If no World Skill
exists, show the small initial contents that will help create this Task and
future Tasks. Keep the Task's exact request, focal records, expected result,
hidden truth, and exact scoring rules out of the World Skill.

Let the user revise the Task proposal and World knowledge together before
implementation. Offer alternatives only when a real user choice changes the
design.

## 3. Write and review the Task Spec and World Skill

Copy [the Task template](assets/task/Task.md.template) to
`evals/<suite>/tasks/<task-id>/Task.md`. Put all Task-specific design in this
one file. At the same time, create or update the project World Skill by
following [World knowledge](references/world-knowledge.md). Determine the
project skill location supported by the active agent and repository.
`.agents/skills/<project>-world/SKILL.md` and
`.claude/skills/<project>-world/SKILL.md` are common landing spots. Follow an
established project convention when one exists. Otherwise, explain the proposed
location and get user confirmation before creating the skill. Start from
[the World Skill template](assets/world-skill/SKILL.md.template) when needed.

Keep each `Task.md` beside the Harbor task it describes:

```text
evals/<suite>/tasks/<task-id>/
├── Task.md              # human-reviewed control-plane spec
├── task.toml             # required Harbor configuration
├── instruction.md        # required agent input
├── environment/          # required Environment definition and visible state
│   ├── Dockerfile        # use this or docker-compose.yaml
│   └── docker-compose.yaml # optional; primary service must be main
├── tests/
│   ├── test.sh           # required Harbor Verifier entry point
│   ├── test_*.py         # optional Verifier helpers
│   └── fixtures/         # optional hidden Verifier data
└── solution/
    └── solve.sh          # optional reference path
```

Never copy or mount `Task.md` into the evaluated agent's workspace or image.
The agent receives `instruction.md` and only the Environment state intended for
the run.

Include:

- purpose and source evidence;
- exact input and later turns;
- only the Harness conditions relevant to this Task;
- initial state, services, access, visibility, reset, and production
  differences;
- required results, prohibited effects, accepted alternatives, and independent
  Verifier evidence;
- fairness, leakage risks, and invalid-run conditions; and
- open decisions and assumptions.

Show the full Task Spec and the World Skill changes to the user. Explain what
is already in the World Skill, what this Task adds or corrects, and what stays
only in `Task.md`. Revise both through the same back-and-forth. Mark the Task
Spec approved only after explicit approval. Treat World Skill changes as
accepted only after the user reviews them. If the user requests an end-to-end
build without an approval pause, continue with an agent-reviewed
`Status: Draft` and label the World Skill changes as unreviewed.

If implementation changes the request, visible information, material
Environment behavior, or scoring boundary, update `Task.md` and show the
change. Set its status back to `Draft`. Show the diff and require explicit
reapproval before setting it to `Approved` again.

## 4. Apply Spec2Task

Follow [Task implementation](references/task-implementation.md). It gives the
build order and routes each decision to the Environment, synthetic-data,
Verifier, Harbor, and calibration references.

For an existing project, use its pinned or supported Harbor version. Otherwise,
use the installed supported version and record it. Upgrade only with user
approval and a stated compatibility reason. Use the installed CLI help as the
command contract.

Before a scored model run:

1. Confirm the model, trial count, judge, timeout, and maximum expected cost
   with the user unless the user already authorized that run plan.
2. Complete the package audit in [Harbor](references/harbor.md). Confirm every
   required file, entry point, path, permission, configuration value, mount,
   service, and reward output needed for this exact Task is present and works
   through Harbor. Confirm hidden Task, Verifier, solution, and secret material
   is absent from the agent-visible image and workspace.
3. Check setup and trial isolation in the way that fits the Environment. A
   fresh container or worktree can provide isolation by replacement. A reused
   mutable service needs a checked reset. Immutable frozen data needs only a
   checked load. See [Task implementation](references/task-implementation.md).
4. Exercise every operation the Task depends on.
5. Run the reference path when one exists.
6. Test the Verifier with a clear valid result, a valid alternative, a
   realistic wrong result, a shortcut, a prohibited collateral change, and
   missing or corrupt evidence.
7. Confirm every completed Verifier path writes a valid reward and useful
   evidence without exposing hidden truth or secrets.

## 5. Run and audit

Run the actual Harness through Harbor. Read the complete trajectory, not only
the reward. Inspect:

- messages, model calls, tool calls, results, retries, and errors;
- initial and final Environment state and external effects;
- service, setup, readiness, reset, and cleanup evidence;
- each Verifier criterion, its evidence, decision, and error; and
- the resolved Harness, model, Environment, and judge configuration.

Classify each unsuccessful run as an agent capability failure, missing
information, Harness defect, Environment defect, Verifier false rejection,
Verifier false acceptance, leakage, or infrastructure failure. Fix non-agent
failures before using the score.

Model comparison is an optional calibration strategy, not a completion rule.
When it would answer a real uncertainty, compare a weaker model, the target
model, or a stronger model and repeat trials when behavior is variable. Read
every selected trace. Contrast can expose unclear inputs, brittle setup,
leakage, shortcuts, or reward hacks. Pass rates and model ordering do not prove
Task quality.

Read [Calibration](references/calibration.md) for the complete audit method.

## 6. Reconcile project World knowledge

Use [World knowledge](references/world-knowledge.md) throughout Task design,
implementation, and audit. Add or correct project-specific knowledge when the
work supplies evidence that would help another Task. This can include Task
patterns, Environment methods, data creation, Verifier evidence, run
procedures, scripts, assets, and examples.

After the audit, reconcile the World Skill with what the completed Task proved.
Show the user:

- the proposed reusable knowledge;
- the evidence supporting it;
- how another Task would use it;
- where it should live; and
- what remains specific to the completed Task.

Remove or narrow ideas that the Task disproved. If the user asked for
autonomous end-to-end updates without a pause, make the smallest supported
update, show it in the final review, and do not imply that the human approved
the generalization.

Create only `SKILL.md` at first. Add `references/`, `scripts/`, `assets/`, or
`tests/` only when their real contents justify them.

Keep the completed Task's request, focal state, expected result, and exact
criteria in its collocated `Task.md`. Do not copy broad guidance that is already
clear in this skill. Record the project-specific adaptation of that guidance.

## 7. Repeat

Use Tasks two and three to test the World Skill. Check whether it reduces
rediscovery, improves Task Specs, preserves important relationships, reuses a
proven operation, or prevents a known Verifier defect. Correct rules that are
missing, stale, or too broad.

When several materially different Tasks have exercised the shared knowledge
and the construction and verification methods are clear, the next cycle can
propose several independent Task Specs:

1. Mine new repository, trace, and human evidence.
2. Use the World Skill to generate distinct Task Specs.
3. Have the human review the specs.
4. Build independent approved Tasks in parallel.
5. Audit every Task individually.
6. Update World knowledge only with reusable corrections.

Continue this loop as production behavior, user priorities, agents, and models
change.

## Dependencies, access, and safety

Map required systems, data, roles, network needs, and safe setup methods. Never
read, print, copy, store, or ask the human to paste secret values. Tell the
human what dependency is needed, why it is needed, and how the project expects
access to be provided. Default to controlled local, frozen, or simulated
dependencies. Never write to production during an eval. Treat access, startup,
reset, timeout, judge, and Verifier failures as invalid runs, not failed agent
work.

## Complete only when

- `Task.md` matches the built instruction, Environment, and Verifier.
- The Task is solvable from agent-visible or normally discoverable information.
- The Environment starts reliably and isolates trials by replacement, reset,
  or immutable state as appropriate, without leaking hidden truth.
- Valid and invalid Verifier cases behave as intended.
- At least one real Harness run was read in full.
- Non-agent failures were repaired or reported as unresolved limits.
- Model comparison, when used, includes trace review rather than pass rates
  alone.
- The project World Skill was created or updated with the Task Spec, reviewed
  during the work, and reconciled with the final evidence.
- The user receives the Task path, run command, results, evidence, and remaining
  limits.
