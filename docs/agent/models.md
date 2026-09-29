# Updating workflow model assignments

Use `scripts/update-models` from this source repository to keep model IDs and
their documentation labels in sync. The command reads and updates the shared
files under `workflow/`: it changes the primary orchestrator recommendation
in the documentation and the spawned-worker model in the runtime configuration
and all three worker definitions. The command output names those source files
with the `workflow/` prefix.

For agents, use this sequence:

1. Inspect with `--show` and use the exact model ID requested by the user.
2. Preview the requested role flags with `--dry-run`.
3. Apply the same flags without `--dry-run`.
4. Verify with `--show` and repeat the preview; it should report no changes.
5. Sync target projects only when distribution is part of the user's request.

Commands resolve files relative to the script location, independent of the
current working directory. From another checkout, invoke the script by its
absolute path in this source repo. Target projects do not receive these
scripts. Exit code 0 means success, including a no-op; exit code 2 means
invalid input, inconsistent workflow source fields, or an I/O error. Resolve
reported errors before retrying, rather than bypassing validation with manual
edits.

```sh
./scripts/update-models --show
./scripts/update-models --orchestrator MODEL_ID --dry-run
./scripts/update-models --orchestrator MODEL_ID --orchestrator-display-name "Readable Name"
./scripts/update-models --subagent MODEL_ID --subagent-display-name "Readable Name" --dry-run
./scripts/update-models --orchestrator MODEL_ID --subagent MODEL_ID --dry-run
```

The IDs are supplied by the operator. The script checks their slug syntax but
does not query a service or claim that a model is available. Display names can
be supplied when the model ID does not produce a useful label; otherwise a
readable label is inferred. Short references in the evaluation recommendations
use the last word of that label.

`--dry-run` prints a unified diff for every planned file and performs no
writes. Without it, the command validates the complete source schema first,
then atomically replaces only changed files while preserving their permission
bits. Repeating a request is safe, and a no-op leaves file timestamps alone.
The script preserves reasoning settings and unrelated TOML and documentation
text. Its model fields are marked in the documentation source so references
remain tied to their role even when two roles use the same model ID.

After changing source files, review the planned distribution with:

```sh
./scripts/sync-workflow --all --dry-run
./scripts/sync-workflow --all
```

The model update affects `workflow/` only. It does not distribute changes to
registered projects automatically.
