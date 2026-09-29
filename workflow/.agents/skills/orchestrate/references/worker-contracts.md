# Worker Contracts

Every delegated task must be bounded enough that the worker can determine
whether it succeeded without needing the full parent conversation.

Use the following structure when assigning substantial work.

## Objective

Describe the concrete result required.

The objective should describe an outcome rather than an activity.

Good:

"Add server-side validation preventing expired reset tokens from being used."

Bad:

"Look at the reset-token code and improve it."

## Scope

Define the files, components, subsystem, or behavior the worker owns.

For implementation workers, write ownership must not overlap with another
concurrent implementation worker.

Prefer a coherent ownership boundary over an arbitrary file count.

## Context

Provide only durable information necessary to begin.

Prefer:
- relevant file paths;
- relevant symbols;
- interfaces;
- architectural facts;
- decisions already made;
- concise upstream worker findings.

Avoid:
- complete parent conversations;
- complete source files;
- raw search output;
- routine command logs;
- unrelated task history;
- another worker's chain of reasoning.

When possible, point the worker to repository locations rather than copying the
contents into the assignment.

## Constraints

State anything the worker must preserve or avoid.

Examples:
- do not change the public API;
- do not modify database schema;
- preserve backward compatibility;
- remain within the assigned component;
- do not perform unrelated cleanup.

## Acceptance Criteria

Define observable conditions for success.

Examples:
- expired tokens are rejected;
- valid unexpired tokens still succeed;
- existing authentication tests pass;
- a regression test covers the new behavior.

Avoid acceptance criteria based only on implementation details unless those
details are themselves requirements.

## Verification

Specify the most relevant validation when known.

Examples:
- targeted unit tests;
- integration tests;
- build;
- typecheck;
- lint;
- reproduction steps.

Workers may run additional focused checks when necessary.

## Return Contract

Implementation workers should return exactly the durable information the
coordinator needs.

Use this structure:

OUTCOME

completed | partially completed | blocked

CHANGES

For each changed file:
- path;
- concise description of what changed.

VERIFICATION

For each meaningful command:
- command;
- pass | fail;
- concise failure explanation if it failed.

DECISIONS

Only decisions that affect integration, interfaces, or later work.

RISKS / BLOCKERS

Remaining issues, assumptions, dependencies, or follow-up work.

Do not return:
- full source files;
- full diffs;
- routine shell output;
- chronological implementation narration;
- speculative commentary unrelated to the assigned task.

## Explorer Return Contract

Exploration workers should return:

FINDINGS

A concise answer to the exact assigned question.

RELEVANT FILES

For each relevant file:
- path;
- relevant symbol or region when useful;
- why it matters.

FLOW / DEPENDENCIES

Only relationships relevant to the assigned task.

RISKS / UNCERTAINTIES

Anything unresolved that affects planning.

RECOMMENDED IMPLEMENTATION SCOPE

The smallest likely file or component set needed for implementation.

Do not paste whole files or routine search output.

## Reviewer Return Contract

Reviewers should return only substantive findings.

For each finding:

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

If no substantive issue is found, return:

NO SUBSTANTIVE FINDINGS

Then include:

CONFIDENCE

high | medium | low

TEST GAPS

Only important missing verification.