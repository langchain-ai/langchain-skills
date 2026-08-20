# Bootstrap and Maintain Project World Knowledge

## Sections

- [Purpose](#purpose)
- [Choose the project location](#choose-the-project-location)
- [Learn from broad guidance](#learn-from-broad-guidance)
- [Decide what belongs](#decide-what-belongs)
- [Bootstrap with the first Task](#bootstrap-with-the-first-task)
- [Create the project skill](#create-the-project-skill)
- [Write each resource](#write-each-resource)
- [Learn through Tasks two and three](#learn-through-tasks-two-and-three)
- [Use World knowledge at scale](#use-world-knowledge-at-scale)
- [Avoid common failures](#avoid-common-failures)

## Purpose

A World Knowledge Skill is a repository-local skill that improves future Task
Spec generation and Spec2Task implementation for one project or benchmark. It
contains reusable project-specific knowledge, procedures, scripts, assets,
tests, and examples.

It is not a complete simulated company, a copy of repository documentation, or
a container for one Task's hidden truth. It can describe any reusable project
knowledge needed across Task design, Environment construction, data creation,
verification, Harbor execution, calibration, or audit.

## Choose the project location

Do not assume every coding agent discovers the same project skill directory.
Inspect the active agent, its current documentation or configuration, and the
repository's existing conventions. Good landing spots include:

- `.agents/skills/<project>-world/SKILL.md` for agents and repositories that
  discover project skills under `.agents/skills/`; and
- `.claude/skills/<project>-world/SKILL.md` for Claude Code project skills.

Use the native project location that the active agent will discover. If the
repository has no established convention, or the intended agent is unclear,
show the proposed path and reason to the user and get confirmation before
creating the skill. For another agent, use its documented project skill
location. Do not create copies in several locations unless the user asks for
that compatibility work.

The resulting skill has this structure wherever it is placed:

```text
<project-skill-root>/<project>-world/
├── SKILL.md             # required
├── references/          # optional detailed knowledge
├── scripts/             # optional reusable operations
├── assets/              # optional material copied or processed
└── tests/               # optional checks for reusable code and contracts
```

Create only `SKILL.md` at first. Add a folder only when real contents justify
it.

## Learn from broad guidance

Read the relevant `eval-engineering` references before creating or updating
World knowledge. Ask what project-specific answer was required to apply the
broad method.

| Broad guidance | Useful project-specific adaptation |
|---|---|
| Preserve relationships needed for a decision | Exact project records and links that must stay together |
| Verify final state independently | Exact tables, files, APIs, or logs that prove effects |
| Simulate mutable services | Exact local service, operations, errors, and reset command |
| Generate prose from source facts | Project fact schema, generation method, review rules, and scripts |
| Accept valid alternatives | Known equivalent states or outputs for this project |
| Inspect complete trajectories | Exact project artifacts and service logs to correlate |
| Use real failure conditions | Project-specific failure families learned from traces |
| Prevent leakage | Project fields, endpoints, filenames, or fixtures that reveal truth |

Record the adaptation, not a copy of the broad paragraph.

## Decide what belongs

Add a finding when it is:

- specific to the project or benchmark;
- useful for Task Spec generation, Spec2Task implementation, or both;
- likely to help more than one Task;
- supported by repository code, traces, a human decision, or Task evidence;
- specific enough for another agent to apply; and
- easier to find here than inside one old Task.

Useful contents can include:

- Task families, meaningful variations, coverage, and known weak designs;
- tool and service contracts exercised by Tasks;
- entities, relationships, identities, permissions, time, and history;
- approved data sources and proven generation or subset methods;
- setup, readiness, reset, and cleanup procedures;
- independent truth sources and reusable Verifier checks;
- project-specific shortcuts, reward hacks, and invalid-run signatures;
- useful model or judge configurations and artifacts to inspect;
- reusable commands, scripts, fixtures, and templates; and
- unresolved gaps that can change future Task validity.

Keep these in the collocated `Task.md` instead:

- the exact request;
- focal records and initial state;
- the expected result;
- exact Task criteria and hidden evidence;
- one-off setup or workaround; and
- a decision that has no likely use outside that Task.

Do not add generic guidance already clear in `eval-engineering`, unsupported
guesses, large copied documents without routing, or unrun scripts.

## Bootstrap with the first Task

Create or update the World Skill while the first Task Spec takes shape. Do not
build a large project encyclopedia from repository shape alone. Add the small
set of supported facts and methods that help design the current Task and are
likely to help later Tasks.

In the first user-facing design response, show these parts together in any
clear structure:

- the proposed Task;
- relevant content already in the World Skill;
- reusable additions or corrections suggested by the current inputs; and
- details that will stay only in `Task.md`.

Revise the Task and World knowledge together with the human. During Task
design, build, and audit, update reusable knowledge from:

- repository and trace evidence;
- human corrections and policy decisions;
- Environment construction and service behavior;
- data-generation and review work;
- Verifier design and regression cases;
- real agent trajectories and final state;
- leaks, shortcuts, false acceptance, and false rejection; and
- setup, timeout, reset, or infrastructure failures.

Show the World Skill with the Task Spec and let the human revise both. A human
can approve the Task while rejecting a proposed generalization. Treat a World
Skill change as accepted only after human review. If the user asked for
autonomous end-to-end updates without a pause, make only the smallest supported
change and show it in the final review. Do not label that change as
human-approved.

After the Task is audited, reconcile the skill. Keep supported reusable
knowledge, narrow or remove claims that the Task disproved, and keep Task-only
truth in `Task.md`. State the evidence, use in another Task, location, and
uncertainty in any clear structure.

## Create the project skill

Start from `assets/world-skill/SKILL.md.template`. Replace all template values
and delete unused sections. Use a short lowercase name ending in `-world`.

Write `SKILL.md` as a concise operating guide and router. Include:

- sources and commands that future Task work should start from;
- a table that routes concrete needs to references, scripts, or assets;
- short, commonly needed project rules;
- existing Task coverage and meaningful gaps;
- known limits; and
- the update procedure.

Do not fill generic headings with vague project biography. A source or rule
must help an agent create, build, or check a Task.

The project skill can say:

> Read `$eval-engineering` first. Use its broad references and examples as
> guidance. Use this skill for reusable knowledge about how that guidance
> applies to this project.

Do not link to internal `eval-engineering` file paths from the project skill.
The general skill owns its own routing and can reorganize without breaking
project skills.

## Write each resource

### `SKILL.md`

Keep always-needed rules and routing here. Prefer one concrete sentence over a
category label. For example:

```text
For Tasks that change a ticket, retain its customer, team, assigned user,
active assignment, comments, and status history.
```

### `references/`

Create a reference when detailed knowledge is conditionally needed. Name it by
the real project topic, such as `ticket-state.md`, `repository-setup.md`, or
`document-generation.md`. Link it directly from the project `SKILL.md` and
state when to read it.

Choose reference names from real project topics. Do not create a fixed file
taxonomy before concrete reusable content exists.

### `scripts/`

Add deterministic operations that would otherwise be rewritten or are easy to
implement incorrectly. Document inputs, outputs, side effects, and what the
script does not prove. Run the script and add focused tests.

Examples include creating a relationship-complete subset, validating a source
bundle, or packaging a project-specific Task.

### `assets/`

Add templates or static material intended for copying or processing. Do not
use assets to hide instructions, expected answers, or Verifier logic from skill
review.

### `tests/`

Test reusable scripts and project contracts. Do not copy one runnable Task's
Verifier suite into the World Skill.

## Learn through Tasks two and three

Use the project skill while creating materially different Tasks. After each
Task, ask:

- Did the skill prevent repeated discovery?
- Did it improve the Task Spec or Environment?
- Did it preserve relationships or behavior that could have been lost?
- Did it provide independent Verifier evidence?
- Was a script actually reused?
- Was a rule too broad, stale, or wrong?
- What new knowledge should another Task inherit?

Revise the smallest useful resource. Remove competing guidance rather than
keeping both versions.

Treat the project skill as ready for scale when several Tasks have exercised
its important knowledge, shared construction and verification methods are
clear, current coverage and gaps are visible, and known limits are stated.
Do not require a fixed Task count or file count.

## Use World knowledge at scale

For Task Spec generation, use project knowledge to:

- select real conditions and uncovered capabilities;
- state realistic objects, relationships, access, and failure modes;
- choose project-supported data methods;
- avoid duplicate or previously rejected designs; and
- identify independent evidence before implementation.

For Spec2Task implementation, use project knowledge to:

- build services and state through proven project methods;
- preserve tool behavior and relationships;
- reuse builders, validators, and assets;
- implement project-specific Verifier evidence; and
- recognize known leakage and infrastructure failures.

Keep reviewing generated Task Specs with the human. World knowledge improves
generation but does not replace task-level judgment.

## Avoid common failures

- **Speculative encyclopedia:** building a large project map before one Task
  shows what is useful.
- **Task leakage:** storing focal records, expected answers, or exact criteria
  in the World Skill.
- **Generic duplication:** copying broad eval guidance instead of recording the
  project-specific adaptation.
- **Empty taxonomy:** creating standard reference files with no concrete use.
- **Unmotivated examples:** mixing unrelated domains without explaining the
  Task that produced the lesson.
- **Untested automation:** listing scripts or commands that were not run.
- **Stale certainty:** preserving a rule after later evidence contradicts it.
- **Hidden dependency:** relying on project knowledge that is neither routed
  from `SKILL.md` nor cited by the Task Spec.
