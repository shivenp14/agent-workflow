---
name: verify-change
description: Verify that a software change satisfies its acceptance criteria using targeted tests, builds, typechecks, reproduction steps, repository inspection, and integration checks. Use before accepting substantial implementation work.
---

# Verify Change

Verification establishes whether the requested outcome actually works.

A worker reporting success is evidence to inspect, not proof of completion.

Choose the smallest set of checks that provides strong evidence for the
acceptance criteria.

## 1. Start From Acceptance Criteria

List the observable requirements that must be true.

Verification should map back to these requirements.

Do not run broad commands solely because they exist.

Prefer checks that can disprove an incorrect implementation.

## 2. Identify Affected Surfaces

Determine which parts of the system are materially affected.

Consider:
- directly changed code;
- callers and consumers;
- interfaces;
- persistence or schema behavior;
- build or type relationships;
- user-visible behavior;
- security boundaries;
- important integration points.

Use this to select verification.

## 3. Run Targeted Tests First

Prefer the narrowest meaningful tests that exercise the changed behavior.

Examples:
- focused unit tests;
- package-level tests;
- component tests;
- targeted integration tests;
- regression tests for the original failure.

If a targeted test fails, investigate before running increasingly broad suites.

## 4. Run Static or Build Checks When Relevant

Use relevant project checks such as:
- typecheck;
- compilation;
- build;
- lint when lint rules affect correctness or repository acceptance;
- schema validation;
- generated-code consistency.

Do not run unrelated expensive checks without a reason.

## 5. Verify Behavior Directly When Useful

For behavior that is not adequately established by automated tests, use a
focused reproduction.

Examples:
- call the affected API;
- exercise the relevant CLI command;
- reproduce the original bug;
- verify the state transition;
- inspect produced output.

Prefer deterministic verification over subjective visual inspection when
possible.

## 6. Inspect Integration State

Before accepting substantial work, check for integration problems such as:
- incompatible interfaces between worker changes;
- unresolved merge conflict artifacts;
- unexpected changed files;
- accidental unrelated modifications;
- stale generated output;
- dependencies that were assumed but not implemented.

Inspect exact source only where needed to establish integration.

Do not reread every changed file without a verification reason.

## 7. Handle Failures

When verification fails, report:
- the exact failed check;
- the relevant concise error;
- which acceptance criterion is not established;
- whether the failure appears local, conceptual, or integration-related.

Route the failure to the implementation owner when appropriate.

Do not hide failed verification behind other passing checks.

## 8. Verification Result

Return:

STATUS

verified | partially verified | failed

ACCEPTANCE CRITERIA

For each criterion:
- criterion;
- verified | not verified;
- evidence.

CHECKS

For each meaningful check:
- command or method;
- pass | fail;
- concise result.

INTEGRATION

Any relevant integration observations.

REMAINING GAPS

Only verification that remains materially important.

Do not include:
- full terminal logs;
- routine successful output;
- unrelated repository observations;
- implementation narration.

## 9. Completion Standard

A substantial change should not be considered complete until:
- relevant acceptance criteria are verified;
- important automated checks pass;
- substantive review findings are resolved;
- integration is coherent;
- any remaining limitation is explicitly understood.

Verification should increase confidence through evidence, not through repeated
assertions that the implementation looks correct.
```

---

# Final Validation

Before reporting completion, verify that the resulting repository contains
exactly these `.agents/` files:

```text
.agents/skills/orchestrate/SKILL.md
.agents/skills/orchestrate/references/worker-contracts.md
.agents/skills/orchestrate/references/retry-policy.md
.agents/skills/orchestrate/references/state-schema.md
.agents/skills/review-change/SKILL.md
.agents/skills/verify-change/SKILL.md