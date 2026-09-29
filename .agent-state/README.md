# Agent State

This directory is reserved for temporary durable orchestration state created
during substantial agent tasks.

Task-state files are coordination artifacts, not conversation transcripts.

## Use This Directory For

State files may contain:
- the task goal;
- acceptance criteria;
- workstream status;
- worker ownership;
- dependencies;
- durable implementation decisions;
- concise worker outcomes;
- verification state;
- unresolved blockers;
- next orchestration actions.

For the exact state format, follow:

```text
.agents/skills/orchestrate/references/state-schema.md
```

## Do Not Store

Do not store:
- chain-of-thought;
- worker transcripts;
- full prompts;
- raw terminal output;
- full diffs;
- large source excerpts;
- chronological implementation narration;
- routine successful command output.

## File Naming

Use one short task-specific Markdown file when persistent state is justified.

Example:

```text
.agent-state/password-reset.md
```

Do not create task-state files for trivial work.

## Lifecycle

Update state only after meaningful orchestration transitions.

Examples:
- a workstream starts or completes;
- a blocker appears;
- an architectural decision changes downstream work;
- a review identifies a substantive problem;
- verification establishes or disproves completion.

When a task is finished, delete or archive temporary state if it has no ongoing
project value.

The goal is to make orchestration resumable without turning this directory into
long-term execution history.
