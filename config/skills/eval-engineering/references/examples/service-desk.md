# Service-Desk World Knowledge Example

This example shows how reusable project knowledge grows across Tasks. It is not
a template for one fixed service-desk scenario.

## After Task 1

Task 1 asks an agent to resolve a support request with account, requester,
entitlement, owner, and history data. Its collocated `Task.md` keeps the exact
request, focal records, accepted result, and Verifier criteria.

The audit proves reusable project facts:

- the Harness uses `search_cases`, `get_case`, and `update_case`;
- case visibility depends on team membership;
- entitlement and account state can change the valid action;
- updates write an event and change the case row in one transaction;
- reset rebuilds SQLite from a fixed structured fixture; and
- the Verifier can compare raw case and event state without exposing it.

Create `.agents/skills/service-desk-world/SKILL.md`. Add only these proven
facts, their source paths, and routes to any reusable script.

## After Task 2

Task 2 uses the same product but tests a different capability: it requires the
agent to connect a stale knowledge article, a recent incident, and a customer
message before making an update.

The second audit finds more reusable knowledge:

- documents need stable structured facts before prose generation;
- article freshness is decided by `effective_at`, not insertion order;
- incident-product and case-product links must stay complete;
- generated messages need fact-ID review for unsupported claims; and
- known-good, valid-alternative, wrong, shortcut, collateral, and corrupt-
  evidence fixtures expose different Verifier faults.

Add a short reference for the data relationships and a reusable fixture
validator only because two distinct Tasks now use them. Update `SKILL.md` to
route agents to those items.

## Resulting project skill

```text
.agents/skills/service-desk-world/
├── SKILL.md
├── references/
│   └── data-and-verification.md
└── scripts/
    └── validate_fixture.py
```

Its root skill states when the knowledge applies and gives exact project paths,
commands, state rules, and known limits. It can contain project-specific Task,
Environment, data, Verifier, Harbor, and calibration guidance. It does not say
only “follow eval-engineering,” and it does not copy broad guidance without a
project-specific adaptation.

The skill does not include either Task's request, selected records, expected
answer, or exact rubric. Those stay with each Task. It also does not add empty
folders, a catalog, a manifest, or a file per concept. New content must reduce
rediscovery or prevent a demonstrated defect in another Task.

## Evidence of value

Task 3 tests whether the World Skill works. A new author should be able to find
the correct tool contract, create relationship-complete data, reset state, and
reuse the raw-state Verifier boundary without studying Tasks 1 and 2 in full.
If a rule fails on Task 3, narrow or correct it and cite the new evidence.
