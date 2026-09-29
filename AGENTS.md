# Source repository instructions

This repository maintains an installable workflow in `workflow/`. Keep shared
agent instructions, configuration, skills, and target documentation there.
Keep source maintenance commands, tests, and repository-specific guidance
outside that directory.

Use `./scripts/update-models --show` to inspect model assignments. For a model
change, preview the requested `--orchestrator` and/or `--subagent` options with
`--dry-run`, apply the same options, then verify with `--show` and a no-change
preview. The orchestrator value documents the recommended model; runtime
selection remains in T3 Code. The subagent value updates the shared default and
all worker definitions. Reasoning settings are preserved. Model availability
is not checked.

Use `./scripts/sync-workflow TARGET --dry-run` to preview distribution and
`./scripts/sync-workflow TARGET` to apply it. The script installs only its
explicit target-relative allowlist from `workflow/`; root instructions,
maintenance scripts, tests, and model/sync guidance are source-only. The
registry remains `.workflow-sync-state.json` at this repository root, and its
hash keys match the paths installed in targets. `--all` uses registered
targets. Registration only records a target; it does not write to it.

Both commands resolve source files from their script location and work from
any current directory. Exit code 0 means success, including a no-op. Exit code
2 reports invalid input, inconsistent source, a target conflict, or an I/O
failure. Review the error and correct the source or target before retrying.
Tests use temporary source and target directories; do not point tests at real
projects or the root sync registry.

For substantial work, follow the shared process in
[`workflow/.agents/skills/orchestrate/SKILL.md`](workflow/.agents/skills/orchestrate/SKILL.md).
Use the review and verification skills under `workflow/.agents/skills/` when
their respective tasks apply. Use configured custom agent roles when they are
available; otherwise assign bounded work to default workers. These nested
`.agents/` skills and `.codex/` definitions are installation assets for target
repositories, not active source-repo runtime configuration. Do not copy their
shared policy into this file.
