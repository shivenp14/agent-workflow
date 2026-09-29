---
name: orchestrate
description: Coordinate substantial software tasks with isolated subagents while keeping the parent context compact. Use for non-trivial implementation, broad repository exploration, noisy debugging, multi-file changes, separable workstreams, or independent implementation review. Do not use for trivial reads, simple greps, or obvious tiny edits.
---

# Orchestrate

Coordinate the work instead of absorbing every implementation detail into the
parent context.

The coordinating agent owns:
- the user's objective;
- acceptance criteria;
- decomposition;
- dependencies;
- worker assignment;
- integration decisions;
- review routing;
- final acceptance.

Subagents own bounded exploration, implementation, testing, debugging, and
review.

The goal is not to minimize total tokens at all costs. The goal is to keep the
coordinating context compact and high-signal while moving context-heavy work
into cheaper isolated workers.

## 1. Decide whether delegation is worthwhile

Work directly when the task is small and obvious.

Do not delegate merely to perform:
- one grep;
- one targeted file read;
- a tiny one-file edit;
- a simple correction to already-understood work.

Delegate when one or more of these apply:
- substantial repository exploration is required;
- implementation spans meaningful logic or multiple files;
- tests or debugging may generate significant context;
- multiple independent components can be separated cleanly;
- an independent review would materially reduce risk;
- preserving parent context is valuable.

## 2. Define completion before delegation

Determine the actual acceptance criteria.

Prefer observable criteria such as:
- requested behavior works;
- relevant tests pass;
- build or typecheck succeeds;
- important regressions are covered;
- required interfaces remain compatible;
- no unrelated changes were introduced.

Do not delegate an ambiguous outcome when it can be made concrete first.

## 3. Explore only when necessary

If the relevant architecture is not sufficiently understood to divide the
work, spawn one explorer.

Give the explorer a specific question.

Good:
"Trace how password-reset tokens are created, persisted, validated, and
invalidated. Identify the files and symbols an implementation worker needs."

Bad:
"Understand the repository."

Use the explorer's summary to plan the task.

Do not reread every file the explorer inspected.

## 4. Build a bounded work graph

Divide the task into the smallest coherent implementation units that can be
owned independently.

For each delegated task determine:
- objective;
- writable or investigative scope;
- dependencies;
- required starting context;
- constraints;
- acceptance criteria;
- verification;
- expected return format.

Prefer one capable worker owning a coherent component over many workers owning
tiny fragments.

Parallelize:
- independent research;
- read-only exploration;
- independent test investigation;
- implementation in clearly disjoint components.

Serialize:
- changes to the same files;
- changes to the same abstraction;
- shared API redesigns;
- work where one decision materially constrains another.

Never give concurrent implementation workers overlapping write ownership.

## 5. Dispatch workers with a compact contract

Every delegated prompt should contain only:

OBJECTIVE
The bounded result required.

SCOPE
Files, components, or subsystem the worker owns.

CONTEXT
Only durable facts needed to begin.
Prefer file paths and symbols over pasted source code.

CONSTRAINTS
What must remain unchanged or outside scope.

ACCEPTANCE CRITERIA
Observable conditions for success.

VERIFICATION
Relevant tests, build, lint, typecheck, or reproduction steps.

RETURN CONTRACT
The structured concise result expected from the worker.

Do not send the worker the entire parent conversation.
Do not include unrelated project history.

Use `references/worker-contracts.md` when constructing or validating a worker
assignment.

## 6. Implementation belongs to the implementation worker

For delegated implementation, the implementation worker owns the local loop:

understand
-> edit
-> test
-> inspect failure
-> repair
-> retest
-> report

The coordinating agent should not repeat that investigation after the worker
returns unless a specific integration concern requires it.

This is deliberate: implementation context should normally remain inside the
worker rather than accumulating in the coordinating context.

## 7. Choose worker reasoning effort

Use the normal high reasoning setting by default.

Escalate to the highest available reasoning setting when deeper reasoning is
likely to materially improve the result, including:
- architecture remains genuinely ambiguous after exploration;
- several plausible root causes remain after investigation;
- the implementation involves difficult algorithms or state interactions;
- a high-reasoning worker failed because of reasoning rather than a mechanical
  mistake;
- a high-risk correctness, security, concurrency, or data-integrity review
  warrants deeper analysis.

Do not escalate merely because:
- a command failed once;
- a test had an obvious local failure;
- the task is large but straightforward;
- the worker has not yet been given sufficient context.

## 8. Consume worker responses as state updates

Do not absorb worker transcripts.

Retain only:
- outcome;
- changed files;
- important decisions;
- verification results;
- unresolved risks;
- dependencies for later work.

Do not copy full logs, diffs, or source files into parent context.

If detailed evidence may be needed later, refer to the repository file,
test artifact, or path instead of reproducing it.

For long-running or multi-workstream tasks, use the state format in
`references/state-schema.md`.

## 9. Handle implementation failures

On the first clear local failure:
send the owning worker the relevant failure evidence and allow it to repair the
problem.

Do not respawn a fresh worker for every minor failure.

If the same conceptual approach fails repeatedly:
- stop repeating the same prompt;
- identify the assumption that appears wrong;
- use a fresh explorer or fresh implementation worker;
- increase reasoning effort when the unresolved problem is reasoning-heavy;
- reconsider the decomposition if necessary.

Use `references/retry-policy.md` for retry and escalation behavior.

Do not solve repeated worker failures by simply adding more workers.

## 10. Review important changes

Use a fresh reviewer when one or more of these apply:
- the change is substantial;
- multiple workers contributed;
- the change crosses component boundaries;
- authentication or authorization is involved;
- security or data integrity matters;
- concurrency or state behavior is important;
- implementation required substantial debugging;
- automated verification is incomplete;
- the coordinating agent has meaningful uncertainty.

The reviewer must receive the intended behavior and changed scope, but should
not receive the implementation worker's reasoning history.

Ask it to independently inspect the resulting code.

Use the `review-change` skill for the review procedure.

Use normal high reasoning for ordinary review.

Use the highest available reasoning setting for difficult or high-risk review.

## 11. Route review findings

Treat reviewer findings as hypotheses that require evidence.

For a valid finding:
send the concrete finding back to the implementation worker that owns the
affected area.

Do not make the reviewer implement its own fixes.

After a meaningful fix:
rerun the relevant verification.

Request another review only when the correction is substantial enough to
justify it.

## 12. Integrate centrally

The coordinating agent owns cross-worker integration.

Before completion:
- confirm changed-file ownership is coherent;
- confirm interfaces between workstreams agree;
- check the relevant verification results;
- resolve substantive reviewer findings;
- inspect exact source only where integration cannot otherwise be established;
- ensure there are no unexplained or unrelated modifications.

Do not reread every implementation file merely because a worker touched it.

## 13. Verify before completion

Use the `verify-change` skill when verification requires more than an obvious
single check.

The coordinating agent must establish that the relevant acceptance criteria
are actually satisfied.

Verification evidence is more important than a worker's assertion of success.

## 14. Finish only from evidence

A worker saying "completed" is not sufficient.

The task is complete when:
- acceptance criteria are met;
- necessary verification has passed or limitations are explicitly understood;
- substantive review findings are resolved;
- dependent workstreams are integrated consistently.

Return the user a concise summary of:
- what changed;
- important decisions;
- verification performed;
- any genuine remaining risk.