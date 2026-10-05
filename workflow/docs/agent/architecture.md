# Agent Architecture

This repository uses a coordinator-worker architecture for Codex.

The system is designed to keep the primary coordinating context compact while
isolating context-heavy exploration, implementation, debugging, testing, and
review inside subagents.

## Primary Coordinator

The intended primary session configuration is:

- Model: <!-- agent-workflow-model:orchestrator:full:gpt-6.1-sol -->GPT-6.1 Sol<!-- /agent-workflow-model -->
- Reasoning: Medium
- Selected through: T3 Code

The repository does not hard-code the parent model.

This allows the operator to change the primary model or reasoning effort later
without changing repository instructions.

The coordinator owns:
- understanding the user's goal;
- defining acceptance criteria;
- deciding whether delegation is worthwhile;
- decomposition;
- dependency ordering;
- worker selection;
- task-state management;
- cross-worker integration decisions;
- routing review findings;
- final verification;
- deciding when the task is complete.

The coordinator is not the default implementation worker for substantial work.

## Worker Model

The default worker configuration is:

- Model: <!-- agent-workflow-model:subagent:full:gpt-6-luna -->GPT-6 Luna<!-- /agent-workflow-model -->
- Reasoning: High

The coordinator must explicitly select the configured worker model and
reasoning effort when launching a worker. A custom role's model field or a
native tool description does not establish which settings the runtime applied.
In T3 Code, every worker must be a T3-owned child launched with `delegate_task`
and explicit provider, model, and reasoning settings from the live
`orchestrator_capabilities` catalog. This includes same-provider and nested
delegation; native Codex spawning is not used in T3 by this workflow. Outside
T3, native Codex agents may be used with explicit settings. The launch procedure
is documented in the `orchestrate` skill; check returned runtime metadata and
the child thread configuration where available, and report unverified settings.

A worker may be spawned with the highest available supported reasoning effort
when deeper reasoning is justified by task difficulty, risk, or repeated
reasoning failure.

Reasoning escalation should be selective.

Large but straightforward tasks do not automatically require the highest
reasoning setting.

## Worker Types

### Explorer

The explorer is read-only.

Use it for:
- locating relevant code;
- tracing execution paths;
- mapping dependencies;
- identifying implementation boundaries;
- answering focused architectural questions.

Do not use the explorer merely for one cheap grep or one obvious file read.

### Implementer

The implementer owns a bounded implementation task end-to-end.

Its local loop is:

```text
understand
-> edit
-> test
-> inspect failure
-> repair
-> retest
-> report
```

The implementation context should remain inside the worker unless a durable
fact is needed by the coordinator.

### Reviewer

The reviewer is read-only and should normally receive fresh context.

It evaluates the resulting implementation independently for substantive
problems such as:
- correctness;
- regressions;
- security;
- data integrity;
- concurrency;
- state behavior;
- broken contracts;
- meaningful missing test coverage.

It should not inherit the implementer's reasoning history unless a specific
piece of implementation context is necessary.

## Skills

Repository-local procedures live in:

```text
.agents/skills/
```

The primary orchestration procedure is:

```text
.agents/skills/orchestrate/SKILL.md
```

Supporting references are loaded only when relevant:

```text
.agents/skills/orchestrate/references/worker-contracts.md
.agents/skills/orchestrate/references/retry-policy.md
.agents/skills/orchestrate/references/state-schema.md
```

Independent reusable procedures live in:

```text
.agents/skills/review-change/SKILL.md
.agents/skills/verify-change/SKILL.md
```

This separation keeps `AGENTS.md` small and prevents detailed procedures from
being placed in every primary-session context unnecessarily.

## Delegation Principle

Delegation is useful when it creates a meaningful execution or context boundary.

Good reasons to delegate include:
- substantial repository exploration;
- meaningful multi-file implementation;
- noisy testing or debugging;
- a bounded independent workstream;
- fresh-context review;
- preserving coordinator context.

Delegation is not useful when coordination overhead is larger than the work.

Examples that should usually be handled directly:
- one targeted lookup;
- one grep;
- one obvious file read;
- a trivial edit;
- a small correction to already-understood code.

## Context Principle

The coordinator maintains global task state.

Workers maintain local execution context.

Worker responses should be compressed into durable state such as:
- outcome;
- changed files;
- decisions;
- verification;
- blockers;
- dependencies.

Do not return or persist:
- entire worker histories;
- full source files;
- full diffs;
- large logs;
- routine tool output.

Prefer references to repository paths and symbols.

## Work Contracts

Every substantial worker assignment should define:
- objective;
- scope;
- starting context;
- constraints;
- acceptance criteria;
- verification;
- return contract.

The canonical format is documented in:

```text
.agents/skills/orchestrate/references/worker-contracts.md
```

## Concurrency

Parallelize only work that is genuinely independent.

Good parallel candidates include:
- independent read-only exploration;
- independent research;
- implementation in clearly disjoint components;
- isolated test investigation.

Serialize work when agents would:
- modify the same files;
- modify the same abstraction;
- depend on a shared design decision;
- make incompatible assumptions about the same interface.

Concurrent implementation workers must not have overlapping write ownership.

Maximum concurrency is intentionally conservative.

The configured maximum is a ceiling, not a target.

Do not spawn workers merely because capacity exists.

## Retry Behavior

Ordinary local failures should normally be returned to the same implementation
worker.

Repeated conceptual failures should trigger investigation, re-planning, fresh
context, or reasoning escalation rather than unlimited retries.

The canonical policy is:

```text
.agents/skills/orchestrate/references/retry-policy.md
```

## Persistent State

For substantial multi-worker or long-running tasks, compact durable state may
be stored under:

```text
.agent-state/
```

State should allow the coordinator to resume or reconstruct the task without
reloading worker histories.

State is not required for trivial or short tasks.

## Completion

Substantial work is complete only when:
- acceptance criteria are satisfied;
- relevant verification is complete;
- dependent workstreams integrate coherently;
- substantive review findings are resolved;
- remaining limitations are understood.

Worker self-reports are inputs to this decision, not the final decision.
