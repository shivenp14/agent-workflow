# Agent workflow source

This repository maintains a reusable agent workflow and installs its shared
files into other project repositories. The distributable source lives under
`workflow/`; repository tooling and maintenance guidance stay at the root.
The sync script uses an explicit allowlist, so only the workflow files it owns
are copied to a target.

```text
workflow/                    Shared instructions, configs, skills, and docs
  AGENTS.md                  Instructions installed in target repositories
  .agents/                   Skills installed for target-repository agents
  .codex/                    Runtime config and worker roles installed to targets
  docs/agent/                Architecture and test guidance for targets
  .agent-state/README.md     State directory guidance for targets
  .gitignore.example         Optional target ignore-file template
scripts/                     Source-only model and sync commands
tests/                       Isolated source and target tests
docs/agent/models.md         Source-only model maintenance reference
docs/agent/sync.md           Source-only distribution reference
AGENTS.md                    Source repository instructions
.workflow-sync-state.json    Local target registry and installed hashes
```

Use `./scripts/update-models --show` to inspect the current model assignments.
The [model command guide](docs/agent/models.md) explains how to preview and
apply role-specific changes. The [sync guide](docs/agent/sync.md) covers target
registration, migration, and conflict handling. Both commands resolve the
source from their own location, so they work from any current directory.

The sync registry remains at the repository root. Its hashes use target paths
such as `AGENTS.md` and `.codex/config.toml`, even though source files now live
under `workflow/`; existing registered targets therefore keep their saved
baselines.
