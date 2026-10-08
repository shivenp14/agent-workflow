---
name: review-change
description: Independently review a completed or proposed code change for substantive correctness, regression, security, state, concurrency, contract, and testing issues. Use for meaningful implementation review. Do not use for ordinary style commentary.
---

# Review Change

Perform an independent implementation review.

The purpose of review is to find concrete problems that could cause incorrect
behavior, regressions, unsafe behavior, broken contracts, or important missing
verification.

Do not review merely to generate comments.

## 1. Establish Intended Behavior

Before judging the implementation, identify:
- the requested behavior;
- the relevant acceptance criteria;
- the changed scope;
- important constraints.

Do not rely on the implementation itself to define what correct behavior means.

## 2. Preserve Independence

When possible, review from fresh context.

Use:
- the intended behavior;
- changed files or diff;
- relevant surrounding source;
- relevant tests;
- repository contracts.

Avoid inheriting:
- the implementer's chain-of-thought;
- the implementer's full conversation;
- speculative justifications for questionable code;
- unnecessary implementation history.

The reviewer should evaluate the resulting artifact rather than defend the
implementation process.

## 3. Inspect the Change

Inspect the changed code and enough surrounding implementation to understand its
actual effect.

Trace relevant:
- callers;
- callees;
- state changes;
- data flow;
- error paths;
- interfaces;
- persistence behavior;
- security boundaries;
- concurrency assumptions;
- tests.

Do not indiscriminately read unrelated areas of the repository.

## 4. Prioritize Substantive Problems

Prioritize:
- functional bugs;
- behavioral regressions;
- incorrect assumptions;
- security vulnerabilities;
- authorization or authentication mistakes;
- data-integrity problems;
- race conditions or state-management errors;
- broken public or internal contracts;
- important unhandled edge cases;
- resource lifecycle problems;
- meaningful missing test coverage.

Do not report:
- personal style preferences;
- purely cosmetic formatting;
- speculative concerns without a plausible failure mode;
- unrelated refactoring opportunities;
- changes that are merely different from the reviewer's preferred design;
- issues already demonstrably handled by the implementation.

## 5. Validate Findings

A finding should identify a plausible concrete failure mode.

Before reporting it:
- inspect enough source to confirm the assumption;
- check whether existing code already handles the condition;
- distinguish confirmed problems from uncertainty.

Do not inflate severity.

If evidence is insufficient, either investigate further or label the
uncertainty clearly.

## 6. Review Tests

Determine whether the tests meaningfully exercise the requested behavior.

Look for:
- missing regression coverage;
- tests that assert implementation details but not behavior;
- important failure paths that remain untested;
- tests that would pass even if the bug remained;
- missing boundary cases where risk is material.

Do not demand exhaustive testing for low-risk trivial behavior.

## 7. Output Format

For every substantive finding return:

SEVERITY

critical | high | medium | low

LOCATION

File and symbol or line when available.

PROBLEM

What is wrong.

IMPACT

The concrete failure mode.

EVIDENCE

Why the implementation supports the finding.

FIX DIRECTION

A concise correction approach.

Order findings by severity.

Do not bury severe findings beneath minor observations.

If there are no substantive findings, return:

NO SUBSTANTIVE FINDINGS

Then return:

CONFIDENCE

high | medium | low

TEST GAPS

Only important missing verification.

## 8. Do Not Implement During Review

Unless explicitly assigned both roles, review should remain independent from
implementation.

Do not modify source files.

Preserve the user's runtime and interaction modes. In T3 Code, launch review
children with `runtimeMode: "inherit"` and `interactionMode: "inherit"`, and
verify their modes using the `orchestrate` procedure. Do not switch auto to
supervised (`approval-required`) or plan mode for review. Keep the no-edit
constraint in the review prompt; approval mode does not enforce a read-only
sandbox.

Route valid findings back to the implementation owner or coordinator.
