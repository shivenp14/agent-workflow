# Syncing the workflow into project repositories

`scripts/sync-workflow` (or `python3 scripts/sync_workflow.py`) copies the repository's allowlisted workflow files into a project directory. It supports Python 3.11 or newer.

```sh
./scripts/sync-workflow /path/to/project --dry-run
./scripts/sync-workflow /path/to/project
./scripts/sync-workflow --register /path/to/project
./scripts/sync-workflow --all --dry-run
./scripts/sync-workflow --all
./scripts/sync-workflow --list
./scripts/sync-workflow --unregister /path/to/project
```

The local registry and each target's last installed hashes are stored in the ignored `.workflow-sync-state.json` file at the workflow repository root. Registration does not change a target. `--all` first validates every registered target, then syncs them; an invalid target prevents target writes. `--dry-run` performs the same validation and prints the planned changes without changing targets or the registry. The sync never deletes unrelated files.

`AGENTS.md` is managed between `<!-- agent-workflow:begin -->` and `<!-- agent-workflow:end -->`. `.codex/config.toml` manages the complete `[agents]` table between `# agent-workflow:begin` and `# agent-workflow:end`; other TOML tables remain project-owned and are preserved. Any custom keys or settings in `[agents]` cause a conflict because the complete table belongs to this workflow. Resolve those settings deliberately with the project owner, then leave a single workflow-owned `[agents]` table; do not rename settings into another table unless the consuming tool supports that table.

An empty or missing mixed file gets a managed block appended. An existing unmarked workflow copy is adopted only when it exactly matches a current or available historical source version, either as the whole file or as one unambiguous embedded block. If local text is mixed into the old workflow block, the command stops rather than guessing. Follow the conflict message and place the markers around only the workflow-owned text, keeping project instructions outside. Invalid or duplicate markers and invalid merged TOML also stop the sync.

Dedicated workflow files are replaced only when absent, unchanged since the last recorded sync, or an exact known historical copy. For marked files, edits inside the managed block are detected from the recorded hash while edits outside it are preserved. Move local changes out of an owned file or restore its managed region before retrying. The tool uses atomic replacement for each file and writes updated hash state after target files.
