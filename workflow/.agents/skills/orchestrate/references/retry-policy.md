# Retry Policy

Retries should preserve useful context without allowing repeated failure to
consume unlimited tokens.

The goal is to distinguish a normal local implementation mistake from a wrong
approach, insufficient context, poor decomposition, or insufficient reasoning.

## 1. Local Failure

A local failure is an issue such as:
- a targeted test failure;
- a compile or type error caused by the current change;
- a straightforward incorrect implementation detail;
- a missed local dependency;
- a mechanical mistake.

When a clear local failure occurs:

1. Send the relevant failure evidence back to the same worker.
2. Keep the original ownership boundary.
3. Allow the worker to diagnose and repair it.
4. Rerun the relevant verification.

Do not create a fresh worker for every ordinary failure.

Do not send the entire command history when a concise error excerpt or
description is sufficient.

## 2. Repeated Conceptual Failure

Treat the problem as conceptual rather than local when one or more of the
following occur:
- the same underlying problem survives two meaningful repair attempts;
- the worker repeatedly changes symptoms without addressing the cause;
- the implementation depends on an architectural assumption that appears
  false;
- the worker cannot determine the relevant ownership or control flow;
- the same approach repeatedly produces incompatible behavior.

When this occurs:

1. Stop repeating the same task prompt.
2. Identify the assumption or uncertainty blocking progress.
3. Use a focused explorer when repository understanding is missing.
4. Reformulate the implementation task using the new durable findings.
5. Use a fresh implementation worker when a clean context is valuable.
6. Increase reasoning effort when the unresolved problem is reasoning-heavy
   rather than mechanical.

## 3. Reasoning Escalation

Start with the normal high reasoning setting.

Use the highest available reasoning setting when:
- multiple plausible root causes remain after investigation;
- architecture is still genuinely ambiguous;
- correctness depends on subtle state interaction;
- an algorithmic problem requires deeper reasoning;
- security, concurrency, data integrity, or another high-risk property requires
  stronger independent analysis;
- a high-reasoning worker failed despite receiving adequate and correct
  context.

Do not escalate merely because:
- a command failed once;
- a test had an obvious local failure;
- a task contains many files but is mechanically straightforward;
- the worker lacks context that can simply be provided.

## 4. Decomposition Failure

The decomposition is likely wrong when:
- workers repeatedly need to modify each other's files;
- apparently independent workstreams are blocked on shared design decisions;
- integration requires substantial rewriting;
- multiple workers independently make incompatible assumptions about the same
  interface.

When decomposition fails:

1. Stop parallel write work.
2. Reassess the shared abstraction or interface.
3. Establish the necessary decision centrally.
4. Redefine ownership boundaries.
5. Serialize coupled implementation when necessary.

Do not preserve parallelism merely for speed.

## 5. Review Failure

Treat reviewer findings as hypotheses rather than automatic truth.

For each substantive finding:

1. Check whether the finding identifies a concrete failure mode.
2. Route valid findings to the implementation owner.
3. Provide only the relevant finding and required context.
4. Allow the owner to fix and verify the issue.

Do not ask the reviewer to both critique and implement the correction unless
there is a specific reason to combine those roles.

If a reviewer repeatedly produces speculative or invalid findings, do not keep
re-running identical review prompts. Tighten the review scope or stop.

## 6. Agent Explosion Prevention

Do not create additional subagents solely because another subagent failed.

Prefer this sequence:

same worker repair
-> clarify missing context
-> focused exploration
-> fresh worker
-> reasoning escalation
-> decomposition revision

before increasing agent count.

A larger number of agents is not evidence of better orchestration.

## 7. Stop Conditions

Stop retrying the current approach when:
- the same conceptual failure persists after appropriate investigation;
- required information or access is unavailable;
- success requires violating the task's constraints;
- further retries would repeat already-tested assumptions;
- the task should be returned to the coordinator for re-planning.

Report the blocker concisely and preserve any verified useful result.