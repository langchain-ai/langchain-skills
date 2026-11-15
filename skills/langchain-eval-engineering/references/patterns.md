# Benchmark Patterns

Use these patterns as evidence-backed starting points. Read the relevant domain
section before designing a Task. Open the cited benchmark when its design can
answer a concrete question about Task shape, Environment state, tool surfaces,
simulation, or verification. Adapt the method to the current project. Do not
copy a benchmark's private data, hidden answer, exact scenario, or limitations
without review.

## Contents

- [Benchmark design index](#benchmark-design-index)
- [Automation Environments](#automation-environments)
- [Browser and Desktop Environments](#browser-and-desktop-environments)
- [Coding Environments and Tasks](#coding-environments-and-tasks)
- [CRM and Knowledge-Work Environments](#crm-and-knowledge-work-environments)
- [Multi-Turn and Policy Environments](#multi-turn-and-policy-environments)
- [Terminal Environments and Tasks](#terminal-environments-and-tasks)
- [Cross-domain quality checks](#cross-domain-quality-checks)

## Benchmark design index

Use this table to decide which external design to inspect in more detail.

| Benchmark | Domain | Design worth studying |
|---|---|---|
| [AutomationBench](https://github.com/zapier/AutomationBench) | Business automation | Trigger data, pre-populated SaaS state, realistic tool surfaces, assertion-level scoring, and a separate strict completion result |
| [AppWorld](https://github.com/StonyBrookNLP/appworld) | Cross-application APIs | Stateful simulated applications, database-backed truth, cross-app workflows, and final-state verification |
| [ToolSandbox](https://github.com/apple/ToolSandbox) | Stateful tool use | Controlled hidden state, milestones, tool-call consequences, and reproducible interaction state |
| [TheAgentCompany](https://github.com/TheAgentCompany/TheAgentCompany) | Workplace agents | Longer work across applications, documents, messages, and durable artifacts |
| [WebArena](https://github.com/web-arena-x/webarena) | Browser agents | Reproducible websites, browser interaction, seeded application state, and state-based evaluation |
| [WorkArena](https://github.com/ServiceNow/WorkArena) | Enterprise browser work | Role-aware enterprise tasks, realistic web workflows, and application state |
| [WorkArena++](https://github.com/ServiceNow/WorkArena) | Multi-application enterprise work | Longer workflows across enterprise applications and role-sensitive state |
| [OSWorld](https://github.com/xlang-ai/OSWorld) | Desktop agents | OS and application snapshots, computer input, cross-application work, and state restoration |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) | Coding agents | Real issues, pinned repository revisions, behavior tests, and patch verification |
| [SWE-smith](https://github.com/SWE-bench/SWE-smith) | Scalable coding Tasks | Reproducible mutation and execution pipelines; mutations still need usefulness review |
| [CRMArena-Pro](https://github.com/SalesforceAIResearch/CRMArena) | CRM agents | CRM roles, linked business records, permissions, and realistic sales workflows |
| [tau-bench](https://github.com/sierra-research/tau-bench) | Policy and tool use | User simulation, policy-guided decisions, tool use, and database final state |
| [tau-squared Bench](https://github.com/sierra-research/tau2-bench) | Longer multi-turn work | Both sides of a tool-mediated dialogue, longer interactions, and final-state checks |
| [Terminal-Bench](https://github.com/laude-institute/terminal-bench) | Terminal agents | Isolated command-line Environments, natural instructions, tests, and reference solutions |

A benchmark citation is not an authority claim. Check its current repository,
paper, release, license, and task format before copying an implementation
pattern. Record which design choice was adapted and why it fits this project.

## Automation Environments

### Use this pattern

Use for scheduled jobs, event handlers, background agents, retries, alerts,
integrations, and work where time or repeated delivery changes correctness.

### State and storage

Store current state and append-only events separately. Include:

- Trigger ID and type.
- Scheduled, occurred, observed, and completed times.
- Actor or source.
- Idempotency key, which prevents repeat delivery from causing a repeat effect.
- Attempt count and error class.
- Current workflow state.
- Side effects and their external IDs.
- Cause or parent event.

Use a fixed clock and deterministic event queue. Use an explicit state machine,
which lists allowed states and changes. Store enough history to prove retry, deduplication, and
recovery behavior.

For each case, define trigger data, pre-populated starting state, the allowed
tool surface, and final-state assertions. This is the useful AutomationBench
case shape. The trigger starts the workflow; it does not replace the World or
the Task success contract.

### Services, tools, and access

Simulate mutable queues, schedulers, webhooks, email, and third-party writes
unless an approved sandbox is safe and resettable. Preserve payload schema,
delivery order, duplicate delivery, error classes, retry limits, and side-effect
IDs.

Catalog scheduler, queue, service, cloud, and model credentials by name and
scope. Keep the fixed clock and hidden future events unavailable to the agent.

### Setup and reset

1. Load base state and pending events.
2. Set the clock and visibility boundary.
3. Start the worker and dependent services.
4. Check queue and service readiness.
5. Save initial state, events, and external-effect ledgers.
6. Reset from the source snapshot, including retry counters and deduplication
   state.

Test reset after partial effects and timeouts.

### Strong Task families

- Process a scheduled action exactly once.
- Recover from a transient error without duplicate effects.
- Stop after a permanent policy or permission error.
- Reconcile a delayed observation with newer state.
- Handle concurrent triggers in a valid order.

### Worked Task A: retry a transient delivery

Instruction:

> Process the pending notification. The first delivery attempt has a transient
> error. Complete the delivery without creating a duplicate message.

Use five required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| final_state | Workflow is complete | Final workflow row | Compare state with `completed` | Exact match |
| retry | One allowed retry occurred | Attempt and error rows | Match one transient failure then one success | Exact sequence |
| one_effect | One message exists | External-effect ledger | Count unique message IDs for the source event | One |
| repeat_safety | Both attempts share one repeat-protection key | Attempt records | Compare keys and source event ID | All equal |
| scope | Other work stays fixed | Before and after snapshots | Compare unrelated workflows and schedules | Equal |

Known-good: one transient failure is followed by one successful attempt with
the same repeat-protection key and one message. Wrong results: abandon, create
two messages, change the key, exceed the retry limit, or change another action.

### Worked Task B: handle duplicate triggers

Instruction:

> Process the two visible trigger deliveries for the same source event. Apply
> the business change once and retain audit evidence for both deliveries.

Use four required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| one_change | Business state changes once | State history | Count changes for the source event | One |
| delivery_log | Both deliveries are retained | Delivery records | Compare delivery ID set | Exact two IDs |
| one_effect | Both deliveries resolve to one effect | Delivery and effect records | Join by source event and effect ID | One shared effect |
| no_loss | Other visible triggers remain | Queue before and after | Compare unrelated trigger IDs and states | Equal |

Known-good: both deliveries are logged and one business effect is committed.
Wrong results: apply twice, drop the second delivery record, create two effect
IDs, or consume an unrelated trigger.

### Calibrate

Use a fixed clock. Run one delivery, duplicate delivery, transient retry,
permanent failure, reordered events, partial effect, and timeout. Reset queue,
attempt, repeat-protection, and effect state each time. Inspect the full event
order and final state. Treat worker startup or clock-control failure as infrastructure.

Report assertion-level partial credit when useful for diagnosis or training.
Keep a separate strict completion result that passes only when every required
assertion passes.

### Difficulty changes

Change one condition: longer delay, retryable then permanent error, concurrent
worker, stale read, reordered event, or partial side effect. Use controlled time
and known event order so failures remain reproducible.

### Sources

- [AutomationBench](https://github.com/zapier/AutomationBench): realistic
  business workflows over 47 simulated SaaS tools. Borrow its trigger data,
  pre-populated state, tool surface, assertion-based final-state checks,
  assertion-level partial credit, and separate strict completion result.
- [AppWorld](https://github.com/StonyBrookNLP/appworld): stateful APIs and
  database verification across applications.
- [ToolSandbox](https://github.com/apple/ToolSandbox): stateful tool calls,
  milestones, and controlled interaction state.
- [TheAgentCompany](https://github.com/TheAgentCompany/TheAgentCompany):
  longer-running workplace workflows and artifacts.

## Browser and Desktop Environments

### Use this pattern

Use when the agent operates websites, browsers, desktop applications, files,
and visual interfaces.

### State and storage

Pin:

- Website or application version.
- Browser, extensions, profile, and viewport.
- Operating system image and display settings.
- Login state and assigned identity.
- Application databases, files, downloads, and clipboard state.
- Time, locale, timezone, and accessibility settings.

Use local sites or snapshots when live content changes results. Preserve
realistic DOM, visual, pagination, latency, validation, and permission behavior.
Use accessibility state only when the real Harness can use it.

### Services, tools, and access

Choose live services only when accounts, data, reset, cost, and side effects are
controlled. Prefer a local clone, frozen site, or sandbox for mutable workflows.

Match the real Harness input and observation surface:

- Screenshots and cadence.
- Mouse, keyboard, scroll, and window controls.
- DOM or accessibility data when available in production.
- Browser downloads and uploads.
- Application launch and focus behavior.

Catalog model, website, SSO, OAuth, VPN, application, and cloud credentials by
name, role, scope, provider, and network need. Never save cookies or secret
values in specs or committed artifacts.

### Setup and reset

1. Restore a pinned browser, VM, or application snapshot.
2. Establish approved login state through the setup boundary.
3. Place required files and clear unrelated downloads and clipboard data.
4. Set display, locale, clock, and window state.
5. Check readiness through the same surface the agent uses.
6. Save raw application state for the Verifier.
7. Reset the full profile or snapshot after every run.

Do not rely on clicking back or reversing UI actions as reset.

### Strong Task families

- Complete a multi-page business workflow.
- Find and update the correct record among similar records.
- Transfer data between a document and application.
- Respect a permission or confirmation boundary.
- Recover from validation or stale-page errors.

### Worked Task A: update a user without changing access

Instruction:

> Update the selected employee's department and phone number. Keep their role,
> group membership, and account status unchanged.

Use five required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| identity | Correct employee was edited | Final application row | Match stable employee ID | Exact ID |
| fields | Department and phone match | Final application row | Compare normalized requested values | Both equal |
| access | Role, groups, and status stay fixed | Before and after access rows | Exact comparison | Equal |
| persistence | Saved values survive a new session | Reloaded row from clean session | Read again after restart | Both equal |
| scope | Other state stays fixed | Application state difference | Compare non-allowlisted rows and fields | No difference |

Known-good: only the stable employee ID and requested fields change and remain
after a new session. Wrong results: update a similar name, change access, leave
an unsaved form, or edit another record while searching.

### Worked Task B: file-to-application workflow

Instruction:

> Read the approved local request file, create the matching application record,
> and save the confirmation PDF in `/home/oai/share/confirmations`.

Use four required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| source | Created values match the approved request | Parsed source file and final row | Compare named fields | All equal |
| record | One record was created | Before and after application rows | Count new IDs and match type | One |
| artifact | One valid confirmation PDF exists | Required path and parsed PDF | Check path, file count, text, and record ID | One valid file |
| scope | No extra effect occurred | State, upload, message, and file differences | Compare with allowlist | No extra change |

Use application state and file parsing for verification. Use visual comparison
only for layout that cannot be checked structurally.

Known-good: one matching application row and one readable confirmation PDF.
Wrong results: wrong source file, unsaved form, duplicate record, screenshot
instead of PDF, wrong output path, or an extra upload or message.

### Calibrate

Restore the snapshot before each reference, wrong-result, and model run. Test a
similar identity, unsaved form, changed access, stale page, duplicate submit,
and extra file. Verify raw application and file state after a fresh session.
Treat login, display, or application startup failure as infrastructure.

### Difficulty changes

Change one condition: similar records, more pages, modal or validation error,
permission boundary, stale page, cross-application transfer, or required file
artifact. Do not create difficulty through tiny targets, hidden UI, or unstable
live content.

### Sources

- [WebArena](https://github.com/web-arena-x/webarena): reproducible websites,
  browser interaction, and state-based evaluation.
- [WorkArena](https://github.com/ServiceNow/WorkArena): enterprise web tasks,
  roles, and workflow state.
- [OSWorld](https://github.com/xlang-ai/OSWorld): operating-system and desktop
  application snapshots, computer input, and cross-application tasks.

## Coding Environments and Tasks

### Use this pattern

Use for bug repair, feature work, refactoring, tests, build systems, and codebase
navigation.

### State and storage

- Pin repository URL, commit, submodules, large-file inputs, and toolchain.
- Use a fresh worktree or copy per run.
- Keep package caches outside the scored worktree or reset them explicitly.
- Record repository instructions, generated-file sources, public exports, and
  build outputs.
- Preserve enough repository history when the agent needs blame, prior changes,
  or release context.

Model relationships beyond files:

- Public API to implementation.
- Registration to runtime selection.
- Schema to generated artifacts.
- Source package to consumer import path.
- Bug report to failing behavior and focused tests.

### Services, tools, and access

Prefer a frozen repository and installed offline dependencies. Allow live
package or web access only when the real job requires it and the run can remain
safe and comparable.

Preserve the production Harness shell, editor, patch, search, test, and build
interfaces. Record private registry credentials, source-host access, and model
credentials by variable name only. Keep hidden tests and reference patches
unavailable to the agent.

### Setup and reset

1. Create a fresh worktree at the pinned commit.
2. Apply one controlled condition, such as an existing bug or generated
   mutation.
3. Confirm the public failure before the agent starts.
4. Capture Git status and relevant generated-file hashes.
5. Reset by discarding the whole task worktree, not by reversing guessed files.

Use a container or VM when system packages, services, or compiler state affect
the result.

### Strong Task families

- Repair a real issue with a reproducible failing test.
- Add a feature through the public API and consumer path.
- Change lifecycle or state behavior across modules.
- Update a schema and all required generated or migration surfaces.
- Diagnose and fix a build, packaging, or release fault.

Do not score a preferred patch shape when tests and public behavior define
correctness.

### Worked Task A: repair duplicate pagination

Instruction:

> Fix the duplicate-item pagination bug in `/workspace`. Keep the public API
> compatible. Add or update focused tests for duplicate-free traversal.

Use four required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| behavior | Pagination has no duplicate items | Focused test output | Run the pinned reproduction and boundary tests | All pass |
| regression | Related behavior still works | Existing focused suite | Run the named test files | All pass |
| compatibility | Public call shape remains available | Consumer import and call test | Import and call the old public function | Test passes |
| scope | No unrelated change | Git diff and generated-file hashes | Compare with an allowlist | No extra path or hash change |

Known-good: a patch that fixes cursor advancement and adds a focused boundary
test. Wrong results: filtering duplicate output after retrieval, changing the
public signature, disabling the failing test, or editing unrelated snapshots.

### Worked Task B: add a public extension

Instruction:

> Add the requested provider through the public package import path. Register
> it in runtime selection and add a consumer-facing test.

Use five required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| implementation | Provider performs the requested behavior | Focused provider test | Run the named behavior case | Passes |
| registration | Runtime selects the provider | Factory test and registry state | Load valid config through the public factory | Correct class returned |
| public surface | Consumer import works | Clean consumer process | Import from the documented package path | Import succeeds |
| tests | Related code remains valid | Pinned internal and consumer suites | Run the named tests | All pass |
| scope | Other providers and defaults stay fixed | Git diff and config snapshot | Compare named files and defaults | No extra change |

Known-good: implementation, registry entry, public export, and consumer test
from the source files that own each surface. Wrong results: implementation
without registration, internal export only, unit test only, or hand-edited
generated output without its source update.

### Calibrate

Run the reference patch, no-op patch, disabled-test shortcut, and unrelated
edit. Run agent trials when they answer a named calibration question. Inspect
the selected diffs and each named test. Treat toolchain, dependency, and
build-start failures as infrastructure errors, not coding failures.

### Difficulty changes

Change one condition: cross-package surface, longer call path, missing
regression test, lifecycle interaction, migration, partial failure, or more
plausible distractor code. Do not remove needed issue context or rely on a huge
unrelated test suite to create difficulty.

### Sources

- [SWE-bench](https://github.com/SWE-bench/SWE-bench): real repository issues,
  pinned commits, and test-based patch verification.
- [SWE-smith](https://github.com/SWE-bench/SWE-smith): programmatic mutation and
  scalable task generation. Borrow reproducible generation and execution; do
  not assume every mutation is useful work.
- [Terminal-Bench](https://github.com/laude-institute/terminal-bench): isolated
  command-line Environments and reference solutions for tasks that cross system
  setup.

## CRM and Knowledge-Work Environments

### Use this pattern

Use for sales, support, operations, research, documents, messaging, meetings,
and work that crosses business applications.

### State and storage

Use a relational store for identities and mutable business records. Use files
or document tables for email, notes, reports, transcripts, and attachments. Add
search only when retrieval behavior is part of the Task.

Model:

- People, organizations, accounts, and aliases across services.
- Ownership, teams, roles, and permissions.
- Opportunities, cases, tasks, and status history.
- Messages, meetings, documents, and source records.
- Product usage, contracts, and time-dependent facts.
- Draft, sent, approved, and deleted states.
- Conflicting, stale, and missing observations.

Create structural facts with code. Create selected prose through source-supported
generation requests and criterion-level review.

### Services, tools, and access

Choose per service:

- Frozen for read-only corpora that must remain comparable.
- Simulated for mutable CRM, messaging, calendar, or document state.
- Live sandbox only when reset, privacy, cost, and side effects are controlled.
- Disabled for irrelevant access that adds leakage or risk.

Match tool names, arguments, results, pagination, permission errors, and effects.
Catalog CRM, email, calendar, document, model, and search credentials by name,
account, role, scope, network need, and provider. Do not store values.

### Setup and reset

- Select a relationship-complete record set, not one isolated row.
- Preserve identities, history, documents, and cross-service IDs.
- Apply one named setup operation through a service or checked builder.
- Give the agent only its assigned identity and production-shaped tools.
- Reset from a clean database or snapshot after every run.
- Save initial and final state plus message and document effects.

### Strong Task families

- Reconcile records across systems and update the source of truth.
- Draft a message or report supported by several services.
- Act on a request while respecting permissions and policy.
- Detect stale or conflicting state and clarify before action.
- Complete a multi-step workflow without duplicate or collateral effects.

### Worked Task A: update an account after a meeting

Instruction:

> Review the latest meeting and current account state. Update the account's next
> step and create an internal follow-up note. Do not send an external message.

Use five required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| account | Correct account has the supported next step | Before and after CRM rows plus meeting | Match account ID and allowed values | Exact match |
| note | One supported internal note exists | New note and meeting facts | Check count and cited facts; judge only unsupported prose | One valid note |
| identity | Assigned user made permitted changes | Audit log, owner, and role | Match actor, owner, and permission rule | All match |
| no_message | No external draft or send exists | Message and draft tables | Compare before and after | Equal |
| scope | Other business records stay fixed | Stable state snapshot | Compare every non-allowlisted row and field | No difference |

Known-good: supported next step plus one source-supported note. Wrong results: use an
older meeting, update a similar account name, claim a decision not made, send an
email, or change a related opportunity that was not requested.

### Worked Task B: produce a portfolio brief

Instruction:

> Create a brief for the assigned accounts. Rank urgent items, cite the source
> record for each claim, and state conflicts instead of resolving them without
> evidence.

Use four required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| coverage | Each qualifying assigned account appears once | Assignment and issue rows plus brief | Recompute expected account IDs and counts | Exact set and count |
| ranking | Order follows the stated urgency rule | Source values and brief order | Recompute score and compare order | Exact order, allowing declared ties |
| sources | Each material claim names a valid record | Brief citations and source rows | Resolve each ID and compare its claimed fields | Every claim supported |
| uncertainty | Conflicts stay explicit | Conflicting rows and brief text | Check required conflict IDs; judge only whether wording preserves uncertainty | All conflicts stated; none invented |

Known-good: every qualifying account appears once in recomputed order with
valid citations and stated conflicts. Wrong results: omit an account, include
an unassigned account, use stale state, cite a missing record, or hide a
conflict. Use a limited judge only for claim support and useful wording.

### Calibrate

Run the reference actions, wrong identity, stale-source, duplicate-effect,
unsupported-claim, and collateral-change cases before model trials. Reset all
services between runs. Inspect final state, audit rows, citations, and each
meaning-based result. Do not treat service startup or login failure as Task failure.

### Difficulty changes

Change one condition: similar names, longer history, cross-service identity,
stale record, permission boundary, several valid actions, or collateral-effect
risk. Do not make the Task hard by hiding a required source.

### Sources

- [AppWorld](https://github.com/StonyBrookNLP/appworld): stateful application
  APIs, cross-application tasks, and database-based verification.
- [CRMArena-Pro](https://github.com/SalesforceAIResearch/CRMArena): CRM roles,
  records, and business workflows. Use domain structure, not private data.
- [WorkArena++](https://github.com/ServiceNow/WorkArena): enterprise application
  workflows and role-sensitive state.
- [tau-bench](https://github.com/sierra-research/tau-bench) and
  [tau-squared Bench](https://github.com/sierra-research/tau2-bench): policy,
  user interaction, tool use, and final-state checks.
- [TheAgentCompany](https://github.com/TheAgentCompany/TheAgentCompany): longer
  workplace tasks across tools and artifacts.

## Multi-Turn and Policy Environments

### Use this pattern

Use when success depends on conversation, hidden user facts, clarification,
consent, policy, escalation, or changes during a dialogue.

### State and storage

Keep separate:

- Agent-visible conversation.
- User simulator facts and goals.
- Policy rules.
- Mutable service state.
- Tool calls and effects.
- Turn and time limits.

The simulator may know facts the agent must ask for. It must not reveal facts
without the defined trigger or judge correctness itself. Store final service
state independently from dialogue.

### Services, tools, and access

Preserve production tool schemas, permission errors, and state changes. Use a
simulated user for repeatability and a simulated or sandbox service for mutable
effects.

Catalog model credentials for the agent, user simulator, and any judge
separately. Pin each model. Keep simulator facts, policies, and expected results
hidden from the agent.

### User simulator contract

Define:

- Goal and known facts.
- Facts supplied initially.
- Facts supplied only after a clear question.
- Behavior on vague, repeated, or leading questions.
- Consent and refusal behavior.
- When the user corrects a mistake.
- Stop condition and turn limit.

Do not let the simulator help the agent simply because progress stalled.

### Setup and reset

- Create fresh service state and conversation state.
- Set the assigned identity, policy version, clock, and simulator facts.
- Check tools before the first turn.
- Save every turn, tool call, and state change.
- Reset both conversation and service state after every run.

### Strong Task families

- Gather required facts before an action.
- Apply policy while helping the user reach a valid outcome.
- Clarify conflicting identity or intent.
- Refuse or escalate a prohibited request.
- Recover after the user changes a material fact.

### Worked Task A: policy-bound refund

User start:

> I need a refund for my last order.

Hidden user facts include order identity, reason, and whether the item was used.
Use five required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| identity | Customer and order are confirmed | Dialogue and service IDs | Find explicit confirmation before action | Correct IDs confirmed |
| facts | Required facts are obtained first | Ordered turns and policy fields | Check each required answer precedes the action | Complete and ordered |
| policy | Action follows the pinned rule | Policy and confirmed facts | Recompute allowed action | Exact match |
| state | Service records match that action | Final order, refund, and escalation rows | Compare expected fields and counts | Exact match |
| scope | No extra effect occurred | Before and after service state | Compare non-allowlisted rows | Equal |

Known-good: confirm the order and required facts, then create only the refund
or escalation allowed by policy. Wrong results: act on the latest order without
confirmation, infer item state, invent an exception, create both refund and
credit, or refuse an allowed request.

### Worked Task B: clarify an identity conflict

User start:

> Move Alex's meeting to Friday afternoon.

Two visible contacts match Alex. Use four required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| clarification | Agent asks before changing state | Ordered dialogue | Find a question that names a distinguishing fact before the tool call | Present and ordered |
| selection | Confirmed contact owns the changed event | User reply and final event | Resolve confirmed contact ID and compare | Exact match |
| time | New time follows request and calendar rules | Final event, clock, and policy | Recompute allowed Friday window | Within window |
| scope | Other events and attendees stay fixed | Calendar difference | Compare with focal-event allowlist | No extra change |

Dialogue checks should establish that clarification happened. Final calendar
state proves the action.

Known-good: ask one distinguishing question, receive the answer, then move only
the confirmed contact's event. Wrong results: guess from name, ask after the
move, change both events, choose a blocked time, or change attendees.

### Calibrate

Run scripted good, ambiguous, changed-request, refusal, repeated-question, and
premature-action conversations before model trials. Inspect ordered turns and
final service state. Reset both after every run. Treat simulator, model, or tool
startup failure as infrastructure, not policy failure.

### Difficulty changes

Change one condition: more hidden facts, policy exception, conflicting user
statement, changed request, permission boundary, or tool state change. Do not
make the simulator evasive beyond the defined user behavior.

### Sources

- [tau-bench](https://github.com/sierra-research/tau-bench): user simulation,
  policy-guided tool use, and database final state.
- [tau-squared Bench](https://github.com/sierra-research/tau2-bench): longer
  interactions and both sides of a tool-mediated dialogue.
- [ToolSandbox](https://github.com/apple/ToolSandbox): stateful tool use,
  milestones, and controlled hidden state.

## Terminal Environments and Tasks

### Use this pattern

Use for command-line diagnosis, repair, build, data processing, services,
systems work, and tasks that require a container or VM.

### State and storage

Pin:

- Base image or VM snapshot.
- Operating system and architecture.
- Installed tools and versions.
- Files, permissions, owners, and working directory.
- Processes, ports, services, and clocks.
- Offline packages, datasets, and repositories.
- CPU, memory, storage, GPU, and network limits.

Keep tests and reference solutions outside the agent-visible image. Store
starting-state and final-state evidence for files, processes, services, and
command results.

### Services, tools, and access

Use a single container when possible. Use Compose only for real service
boundaries; name the primary Harbor service `main`. Add health checks for
dependencies.

Disable network unless the real Task requires it. Record registry, cloud, SSH,
database, and model credential names and scopes. Never bake secrets into images
or pass them as build arguments.

### Setup and reset

1. Build from a pinned image.
2. Install pinned runtime dependencies or include approved offline assets.
3. Place agent-visible files only.
4. Start services and check observable readiness.
5. Capture baseline files, permissions, processes, and service state.
6. Reset by replacing the container or VM.

Separate Environment build errors, service startup failures, timeouts, and
Verifier errors from Task failure.

### Strong Task families

- Diagnose and repair a broken service.
- Restore or transform data under constraints.
- Configure a tool or deployment correctly.
- Repair a build or dependency fault.
- Investigate logs and produce a tested fix.

### Worked Task A: repair a local service

Instruction:

> The service in `/app` fails its health check after restart. Diagnose and fix
> it. Keep its public endpoint and stored records compatible.

Use five required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| readiness | Service becomes healthy | Process, port, and health output | Start with the pinned command and poll to the limit | Healthy in time |
| behavior | Public endpoint is correct | Request and response | Run named requests and compare status and body | All match |
| persistence | Existing records stay readable | Baseline and final store | Read and compare every pinned record | Equal |
| restart | Fix survives restart | Fresh process and requests | Stop, start, wait, and rerun checks | All pass |
| scope | Other system state stays fixed | Port, process, file, owner, and permission differences | Compare with allowlist | No extra change |

Known-good: the normal start command reaches health, serves correct stored data,
and does the same after restart. Wrong results: bypass health, hardcode a
response, delete stored data, leave a foreground process only, or open an extra
port.

### Worked Task B: recover a damaged dataset

Instruction:

> Recover all valid records from `/data/input`, write stable, sorted JSONL to
> `/data/output/recovered.jsonl`, and report rejected record IDs.

Use four required criteria:

| ID | Required result | Evidence | Exact check | Pass |
|---|---|---|---|---|
| recovery | Every valid record appears once | Independent parser and output | Recompute valid IDs and compare output IDs | Exact set, no duplicates |
| rejection | Every invalid ID has a valid reason | Independent errors and report | Compare ID set and allowed reason per ID | Exact match |
| format | Output is stable JSONL | Parsed output and second run | Check schema, sort key, bytes, and repeat build | All match |
| scope | Inputs and other files stay fixed | Before and after file hashes | Compare outside the output allowlist | Equal |

Known-good: recover the exact valid ID set in stable order and report every
invalid ID once. Wrong results: drop or duplicate rows, repair unsupported
values, write only to stdout, change an input, use unstable order, or give an
unsupported rejection reason.

### Calibrate

Run the reference solution, no-op, hardcoded response, data deletion, foreground-only
service, partial recovery, and unrelated-file edit. Rebuild the container or VM
for each run and test restart. Treat image build, service startup, and resource
failure as infrastructure.

### Difficulty changes

Change one condition: more services, partial failure, permission fault, restart,
larger data, limited resources, or cross-file consistency. Do not create
difficulty through missing tools, impossible timeouts, or hidden network needs.

### Sources

- [Terminal-Bench](https://github.com/laude-institute/terminal-bench): isolated
  terminal Environments, natural instructions, tests, and reference solutions.
  Pin the exact 2.x or 3.x release because formats and Verifiers can change.
- [SWE-bench](https://github.com/SWE-bench/SWE-bench): repository repair and
  test-based correctness when the terminal Task includes code changes.

## Cross-domain quality checks

For every adapted pattern, ask:

1. Does the Task require useful production work and the selected capability?
2. Is all needed information visible or normally discoverable?
3. Does the Environment preserve the relationships that change the decision?
4. Can independent evidence prove required and prohibited results?
5. Can an agent pass through wording, record order, leakage, or a shortcut?
6. Does the Task add a meaningful condition rather than rewrite an old prompt?
7. Which benchmark design was adapted, and which limitation was rejected?
8. If model contrast was useful, what did the selected complete traces reveal?

Store proven project-specific adaptations in the project World Skill. Keep the
exact request, focal state, expected answer, and scoring criteria in the
collocated `Task.md`.
