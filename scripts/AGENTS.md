# Workflow maintenance commands

These instructions apply to the source repo's scripts and are not synced into
target projects. Read `../README.md` for the model-change and distribution
sequence; use `update-models --help` and `sync-workflow --help` for flags.

Use the model command for role-aware changes rather than manually replacing
IDs or labels. Preserve the existing role markers and sync allowlist. Do not
add source-only scripts, tests, or maintenance documentation to that allowlist.

Keep automated tests isolated in temporary source and target directories;
never mutate the real workflow source or `.workflow-sync-state.json` in tests.
