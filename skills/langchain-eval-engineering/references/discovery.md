# Discover the Agent, Its Work, and Existing Evals

Discovery should explain the real work, the agent that performs it, the systems
around it, and the evidence available for new Tasks. Organize findings in the
form that best fits the project. Do not force every finding or trace into a
fixed template.

## Contents

- [Set the scope](#set-the-scope)
- [Review the repository](#review-the-repository)
- [Map the Harness and connected systems](#map-the-harness-and-connected-systems)
- [Review existing evals](#review-existing-evals)
- [Review traces](#review-traces)
- [Cluster real requests](#cluster-real-requests)
- [Review traces in batches](#review-traces-in-batches)
- [Learn tool and system behavior](#learn-tool-and-system-behavior)
- [Map dependencies and access](#map-dependencies-and-access)
- [Synthesize evidence](#synthesize-evidence)

## Set the scope

Identify the repository and revision, the agent or workflow under test, the
existing eval suite, the available trace source, and the human's goal. Keep
different agent versions or materially different deployments separate. Mark
unknown facts as unknown.

Read repository instructions, manifests, workspace configuration, and focused
documentation. During read-only discovery, do not start services, install
packages, open secret stores, or use credentials.

## Review the repository

Start from each real way the agent is invoked. Follow reachable code through:

1. Input, prompt, and context assembly.
2. Model creation, routing, settings, and fallbacks.
3. Agent loops, stopping, retries, and error handling.
4. Tools, exact input and output schemas, and validation.
5. Tool implementations, connected systems, parsing, and effects.
6. Skills, subagents, hooks, middleware, sessions, and memory.
7. Files, databases, APIs, applications, network, time, and identity.
8. Focused tests, known failures, deployment, local execution, and CI.

Use repository search to locate code, then read the complete relevant
functions, callers, schemas, and focused tests. A README or directory listing
can locate behavior, but it does not prove runtime behavior.

Keep notes in whatever structure makes relationships clear. Cite important
claims with repository paths and symbols. Distinguish what source code proves,
what a test proves, what a trace only suggests, and what remains uncertain.

For a large repository, divide review by real runtime area, system, or workflow.
Do not divide work by arbitrary file counts. The main reviewer must join
cross-area relationships and check the source behind consequential findings.

## Map the Harness and connected systems

The Harness is the evaluated agent behavior: prompts, model loop, tools,
session behavior, and adapter. The Environment contains the files, data,
services, identity, permissions, network, clock, and mutable state around it.

Follow each agent capability across that boundary. For a search tool, inspect
the registered tool name and arguments, how the Harness parses results, the
service that answers the query, the returned record shape, permissions,
ordering, pagination, errors, and any state changed by the call.

Map only details that can affect Task design or faithful execution:

- how requests enter the Harness;
- information added before the model sees a request;
- tools available in each condition;
- exact request, response, and error shapes;
- state read or changed by each operation;
- permissions, identity, time, ordering, and pagination;
- loops, retries, fallbacks, stopping, sessions, and memory;
- user-visible and external effects; and
- differences introduced by the Harbor reconstruction.

Repository definitions are the primary source for intended schemas. Traces are
useful evidence of real values, error shapes, latency, ordering, and behavior.
Compare both when designing a simulated system.

## Review existing evals

Follow each scored path from instruction to reward:

1. Read the exact agent input and promised result.
2. Read output parsing and fallback behavior.
3. Read every objective check and semantic judge.
4. Read weights, partial credit, thresholds, and the complete pass rule.
5. Read tests for valid, invalid, and partly valid results.
6. Correlate available run evidence with the exact Task version.

Look for unstated checks, unchecked requirements, hidden preferences, leaked
truth, false acceptance, false rejection, stale evidence, and infrastructure
errors reported as agent failures. New Task directions must add a meaningful
condition, capability, failure mode, or evidence requirement.

## Review traces

Use a trace source supplied or approved by the human. Record enough source
context to cite findings later, such as project, agent version, filters, time
range, export time, and stable conversation or trace identifiers.

A trace system can store one interaction as several related records. Names and
relationships differ across products. Reconstruct the user-visible interaction
and all relevant agent activity in time order. Include the initial request,
later user turns, model responses, tool calls and results, retries, errors,
state changes, and final outcome when they exist. Do not assume terms such as
parent run or child run are available.

Start with a varied sample. Include different request types, tools, lengths,
outcomes, permissions, agent versions, and failure shapes. Keep incomplete and
failed interactions visible. They can reveal important dependencies and Task
conditions.

Look for:

- what users actually ask the agent to accomplish;
- how much context, detail, data, and constraint users provide initially;
- facts users expect the agent to discover;
- ambiguity, follow-up questions, corrections, and changed requests;
- desired outputs, state changes, files, messages, or decisions;
- common agent strategies and where they diverge;
- failed tool calls, malformed arguments, empty results, permission errors,
  timeouts, retries, and fallback behavior;
- loops, abandoned attempts, unsupported claims, and partial completion;
- user dissatisfaction, corrections, rejection, repeated requests,
  abandonment, and explicit acceptance;
- final system state and external effects, not only the final response;
- cases where a user appears satisfied despite a hidden error, or unhappy
  despite correct work;
- tool and system schemas observed in real use; and
- realistic conditions that could become Tasks without copying private data.

Preserve citations for important examples and aggregate claims. A note can use
a trace ID, conversation ID, stable event ID, or another locator supported by
the source. The structure of the note is flexible. It only needs enough context
for another reviewer to understand and verify the claim.

Traces show observed behavior. They do not prove intended policy, complete
business rules, or a correct answer. Use repository code, tests, source data,
policies, final state, or human decisions as independent truth.

## Cluster real requests

Group requests by underlying work and outcome, not by exact wording. Useful
dimensions can include:

- user goal and requested artifact or state change;
- systems and tools needed;
- read-only, analytical, drafting, or mutating work;
- amount of context supplied by the user;
- information the agent must discover or clarify;
- permission, policy, time, or identity conditions;
- single-turn or multi-turn interaction;
- common failure or user dissatisfaction; and
- independent evidence available for verification.

Name each cluster in plain language. Keep representative citations and note
important variation inside the cluster. Counts can show frequency in the
sample, but they do not establish business priority or population frequency
unless the sample supports that claim.

Preserve rare but important requests, especially those involving safety,
permissions, high-impact effects, or a distinctive capability. Do not force an
unclear request into a cluster only to make the grouping complete.

Use the clusters to propose coverage, not to copy production conversations.
Translate a cluster into a Task only after defining a controlled Environment,
independent evidence, fairness boundary, and privacy-safe scenario.

## Review traces in batches

When the trace set is large, review several small batches before expanding.
Choose batches by stable identifiers, time windows, request clusters, agent
versions, or outcomes. Keep batches non-overlapping unless overlap is an
intentional review check.

If subagents are available and parallel review is useful:

1. The main agent defines shared analysis questions and privacy limits.
2. Give each subagent a bounded, non-overlapping batch and the same definitions.
3. Ask for request clusters, representative citations, tool and system facts,
   failure patterns, user reactions, possible Task conditions, and uncertainty.
4. Do not require one fixed response template. Require evidence for important
   claims and enough structure to merge results.
5. The main agent merges equivalent clusters, keeps disagreements visible,
   checks representative citations, and audits a sample from each batch.

Do not treat subagent agreement as truth. Retrieve more traces only to answer a
named gap, test whether a pattern repeats, or cover a missing segment.

## Learn tool and system behavior

Trace review should help reconstruct the systems an eval may need to simulate.
For each important tool or system, learn what evidence permits:

- exact operation and argument names;
- required, optional, enum, and nested fields;
- output objects, identifiers, ordering, pagination, and null behavior;
- validation, permission, empty-result, rate-limit, and timeout errors;
- retries and whether repeated calls are safe;
- reads, writes, external effects, and delayed effects;
- identity, role, tenant, time, and other hidden context;
- relationships across records and systems; and
- which behavior is defined by code versus only observed in traces.

Do not infer a complete API contract from one successful call. Compare varied
calls, failures, repository schemas, tests, and approved documentation. Record
known limits so a simulated Environment does not claim unsupported fidelity.

## Map dependencies and access

Map every dependency needed for discovery, Task construction, model runs, or
verification. This can include repositories, trace systems, documents,
databases, APIs, applications, sandboxes, model providers, networks, VPNs,
proxies, browser sessions, roles, and credentials.

Never read, print, copy, store, or ask the human to paste secret values. Do not
open `.env` files, credential stores, tokens, cookies, private keys, or secret
configuration. Inspect only safe code and sample configuration that names a
dependency or variable.

When access is needed, tell the human:

- which dependency is needed and for what step;
- the account, role, scope, or permission required;
- the safe setup mechanism supported by the project;
- the network or local environment requirement;
- whether read-only, sandboxed, frozen, or simulated access can work; and
- what fidelity or evidence is lost without access.

The human supplies access through the approved runtime mechanism. The agent
uses only that mechanism and never records the value. After a safe access path
works, record the reusable setup pattern in project World knowledge: dependency
name, required role and scope, variable or profile name, setup command or
documentation path, readiness check, and known limits. Never record the secret.

## Synthesize evidence

Before proposing Tasks, give the human a clear synthesis. Choose the structure
that best communicates the project. Cover:

- the Harness and connected-system behavior relevant to evaluation;
- real request clusters and representative trace citations;
- user-provided detail, common ambiguities, and interaction shape;
- tool schemas, system state, effects, errors, and simulation implications;
- agent failure patterns and user dissatisfaction signals;
- existing eval coverage and defects;
- dependencies, safe access needs, and missing evidence;
- conflicts, assumptions, and unknown facts;
- candidate reusable World knowledge; and
- two or three supported Task directions.

Protect private data. Summarize or replace identities and raw content when they
are not needed to support the finding.
