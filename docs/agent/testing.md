# Agent System Evaluation

This document defines how to evaluate whether the repository's orchestrated
workflow is actually better than a simpler single-agent workflow.

The orchestration system should earn its complexity through measurable results.

## Objective

The primary objective is:

Reduce high-value coordinator context usage while maintaining or improving task
correctness.

A successful orchestration system does not necessarily minimize total tokens.

It may intentionally move more token volume to cheaper worker models in order
to reduce expensive coordinator input growth.

## Baselines

Compare two configurations.

### A. Single-Agent Baseline

Use the normal primary coding model without delegated workers.

For the intended setup:

```text
GPT-6 Sol
Medium reasoning
```

Let the primary model perform:
- exploration;
- implementation;
- testing;
- debugging;
- review;
- final response.

### B. Orchestrated Configuration

Use:

```text
Coordinator:
GPT-6 Sol
Medium reasoning

Default workers:
GPT-6 Luna
High reasoning

Escalated workers:
GPT-6 Luna
highest supported reasoning effort when justified
```

Use the repository orchestration policy normally.

Do not artificially force delegation when the policy would handle a task
directly.

## Task Selection

Evaluate using real repository tasks rather than synthetic toy tasks whenever
possible.

Include a mix of:

### Small Tasks

Examples:
- small bug fix;
- one-file behavior change;
- simple configuration correction.

These establish the overhead cost of orchestration.

### Medium Features

Examples:
- several-file feature;
- API plus tests;
- contained UI or backend behavior.

These are likely to benefit from bounded implementation workers.

### Broad Repository Tasks

Examples:
- cross-component feature;
- refactor;
- architecture-sensitive modification;
- task requiring significant repository discovery.

These test context isolation.

### Debugging Tasks

Include failures that generate:
- test logs;
- repeated investigation;
- uncertain root causes.

These test whether noisy debugging remains isolated in workers.

### Highly Coupled Tasks

Include at least some tasks that are difficult to decompose.

These test whether the coordinator correctly avoids excessive parallelism.

## Metrics

Record the following for each run.

### Correctness

- task completed: yes | no;
- acceptance criteria satisfied;
- targeted tests passing;
- full relevant test suite status;
- regressions introduced;
- manual corrections required after completion.

### Coordinator Usage

- coordinator input tokens;
- coordinator output tokens;
- number of large file reads performed directly by coordinator;
- number of broad searches performed directly by coordinator;
- number of compactions if visible;
- context size at completion if visible.

### Worker Usage

- total worker input tokens;
- total worker output tokens;
- number of workers spawned;
- worker reasoning efforts used;
- number of worker retries;
- number of fresh workers created after failure.

### Time

- total wall-clock time;
- time to first implementation;
- time spent on review;
- time spent on retries.

### Review

- number of review findings;
- number of findings confirmed valid;
- number of false or non-actionable findings;
- number of implementation defects found only by fresh-context review.

### Coordination

- number of overlapping-file conflicts;
- number of tasks that required re-decomposition;
- number of workers blocked on another worker;
- number of duplicated repository investigations.

## Cost Interpretation

Do not evaluate token count without considering model mix.

A run may use more total tokens but still be preferable if:
- expensive coordinator input is substantially lower;
- worker tokens are cheaper;
- correctness improves;
- the coordinator retains enough clean context to complete a larger task.

Track both:
- total token volume;
- estimated model-weighted cost.

## Suggested Experiment Method

For each representative task:

1. Start from the same repository state.
2. Use the same user request and acceptance criteria.
3. Run the task once with the single-agent baseline.
4. Reset the repository.
5. Run the task once with orchestration enabled.
6. Record metrics.
7. Compare resulting implementations using tests and independent inspection.

When practical, repeat important task classes more than once to reduce the
effect of stochastic variation.

Do not compare two runs that started from materially different repository
states.

## Primary Success Criteria

The orchestration system is providing value when, across meaningful tasks:

- coordinator input growth is lower;
- task success is maintained or improved;
- regression rate does not increase;
- manual correction does not increase;
- context-heavy exploration and debugging remain inside workers;
- coordination failures remain uncommon;
- worker review finds meaningful defects often enough to justify its cost.

## Warning Signs

Reconsider or simplify the orchestration system if:
- the coordinator repeatedly rereads all files the workers already investigated;
- multiple workers repeatedly perform the same exploration;
- small tasks become meaningfully slower due to unnecessary delegation;
- worker retries increase substantially;
- review findings are mostly speculative or false positives;
- concurrent workers frequently touch overlapping files;
- workers frequently depend on hidden assumptions from other workers;
- persistent state becomes larger than the useful task context;
- the coordinator spends more context managing workers than implementation
  would have required;
- total cost rises without a correctness or context-retention benefit.

## Tuning Decisions

Change one orchestration variable at a time when possible.

Examples:
- concurrency limit;
- threshold for delegation;
- reviewer usage;
- High versus highest reasoning escalation;
- state-file threshold;
- number of parallel implementers.

Avoid changing the entire architecture after one failed task.

## Initial Recommendation

Begin with:
- Sol Medium as coordinator;
- Luna High as default worker;
- highest Luna reasoning only by escalation;
- maximum four open subagent threads;
- one explorer only when architecture is unclear;
- bounded implementation workers;
- fresh reviewer for substantial or risky changes;
- persistent state only for genuinely multi-step work.

Measure real repository performance before adding additional specialized agents,
skills, hooks, or orchestration layers.
```

---

# Final Validation

Before reporting completion, verify that the repository contains all of these
files with the exact supplied contents:

```text
AGENTS.md
.codex/config.toml
.codex/agents/explorer.toml
.codex/agents/implementer.toml
.codex/agents/reviewer.toml
.agent-state/README.md
docs/agent/architecture.md
docs/agent/testing.md
