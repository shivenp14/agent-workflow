# Orchestration State Schema

Use durable state only for substantial tasks where the work spans multiple
workers, multiple phases, or enough time that reconstructing orchestration state
from conversation context would be wasteful.

State is a compact coordination artifact.

State is not a transcript.

## When to Create State

Create a task state file when one or more of these apply:
- multiple implementation workstreams exist;
- dependencies between workers must be tracked;
- the task is likely to survive context compaction;
- significant review or retry loops are expected;
- work may need to resume later;
- the coordinator would otherwise need to retain substantial execution history.

Do not create state for trivial tasks.

## Suggested Location

When the repository provides an `.agent-state/` directory, create one
task-specific Markdown file there.

Example:

```text
.agent-state/password-reset.md
```

Use a short descriptive task name.

## Required Structure

Use the following structure.

```md
# Task State: <short task name>

## Goal

<one concise statement of the requested outcome>

## Acceptance Criteria

- <criterion>
- <criterion>

## Decisions

- <only durable decisions that constrain later work>

## Workstreams

### <task-id>

Status: pending | running | completed | blocked | needs-review

Owner: <worker identifier or unassigned>

Scope:
- <component, subsystem, or files>

Depends on:
- <task-id or none>

Outcome:
<one or two sentence durable summary>

Verification:
- <relevant check and result>

### <task-id>

Status: pending | running | completed | blocked | needs-review

Owner: <worker identifier or unassigned>

Scope:
- <component, subsystem, or files>

Depends on:
- <task-id or none>

Outcome:
<one or two sentence durable summary>

Verification:
- <relevant check and result>

## Known Risks

- <only unresolved substantive risks>

## Next Actions

1. <next orchestration action>
2. <next orchestration action>
```

## State Content Rules

Record:
- the goal;
- observable acceptance criteria;
- durable architectural or behavioral decisions;
- workstream status;
- ownership;
- dependencies;
- concise worker outcomes;
- relevant verification status;
- unresolved blockers;
- next orchestration actions.

Do not record:
- chain-of-thought;
- worker transcripts;
- complete prompts;
- raw terminal output;
- full diffs;
- large source excerpts;
- chronological narration;
- routine successful command output.

## Updating State

Update the existing task state after meaningful state transitions, such as:
- a workstream starts;
- a workstream completes;
- a blocker is discovered;
- a decision changes downstream work;
- review finds a substantive issue;
- verification establishes or disproves completion.

Do not update state after every command or minor implementation action.

## Worker Results

Compress worker output into durable facts.

Bad:

"Worker tried implementation A, ran the test, saw error X, then searched Y,
changed Z, reran the test, and eventually..."

Good:

"Backend reset-token validation completed. Auth tests pass. Tokens are
single-use and expire after 30 minutes. Frontend integration remains pending."

## Completion

When the task is complete, the state file should make the final status obvious.

Do not retain stale temporary reasoning.

Delete or archive completed task state according to repository policy if the
state has no ongoing project value.