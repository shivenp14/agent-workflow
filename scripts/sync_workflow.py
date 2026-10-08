#!/usr/bin/env python3
"""Install this repository's agent workflow into one or more local projects."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflow"
REGISTRY = ROOT / ".workflow-sync-state.json"
MARKDOWN_BEGIN = "<!-- agent-workflow:begin -->"
MARKDOWN_END = "<!-- agent-workflow:end -->"
TOML_BEGIN = "# agent-workflow:begin"
TOML_END = "# agent-workflow:end"
OWNED = (
    ".gitignore",
    "AGENTS.md",
    ".codex/config.toml",
    ".codex/agents/explorer.toml",
    ".codex/agents/implementer.toml",
    ".codex/agents/reviewer.toml",
    ".agents/skills/orchestrate/SKILL.md",
    ".agents/skills/orchestrate/references/state-schema.md",
    ".agents/skills/orchestrate/references/worker-contracts.md",
    ".agents/skills/orchestrate/references/retry-policy.md",
    ".agents/skills/review-change/SKILL.md",
    ".agents/skills/verify-change/SKILL.md",
    "docs/agent/architecture.md",
    "docs/agent/testing.md",
    ".agent-state/README.md",
)
MIXED = {"AGENTS.md", ".codex/config.toml"}


class SyncError(Exception):
    pass


@dataclass
class Change:
    relative: str
    path: Path
    data: bytes
    managed_hash: str
    action: str


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_registry() -> dict:
    if REGISTRY.is_symlink():
        raise SyncError(f"registry is a symlink: {REGISTRY}")
    if not REGISTRY.exists():
        return {"version": 1, "targets": {}}
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SyncError(f"cannot read registry {REGISTRY}: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("targets"), dict):
        raise SyncError(f"invalid registry format: {REGISTRY}")
    return data


def save_registry(registry: dict) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(REGISTRY, (json.dumps(registry, indent=2, sort_keys=True) + "\n").encode(), default_mode=0o600)


def atomic_write(path: Path, data: bytes, default_mode: int = 0o644) -> None:
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else default_mode
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def source_bytes(relative: str) -> bytes:
    path = WORKFLOW / relative
    if path.is_symlink() or not path.is_file():
        raise SyncError(f"workflow source is missing or unsafe: workflow/{relative}")
    return path.read_bytes()


def historical_bytes(relative: str) -> list[bytes]:
    """Return exact versions, including history before files moved to workflow/."""
    found: list[bytes] = []
    seen: set[bytes] = set()
    # Keep the target-relative path stable while checking both repository paths:
    # existing targets may contain a bootstrap from before the source move.
    for git_path in (f"workflow/{relative}", relative):
        try:
            commits = subprocess.run(
                ["git", "log", "--all", "--format=%H", "--", git_path],
                cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            ).stdout.splitlines()
        except (OSError, subprocess.CalledProcessError):
            continue
        for commit in commits:
            result = subprocess.run(
                ["git", "show", f"{commit}:{git_path}"], cwd=ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0 and result.stdout not in seen:
                seen.add(result.stdout)
                found.append(result.stdout)
    return found


def marker_region(data: bytes, begin: bytes, end: bytes, label: str) -> tuple[int, int, bytes] | None:
    lines = data.splitlines(keepends=True)
    begin_hits = [i for i, line in enumerate(lines) if line.rstrip(b"\r\n") == begin]
    end_hits = [i for i, line in enumerate(lines) if line.rstrip(b"\r\n") == end]
    if not begin_hits and not end_hits:
        return None
    if len(begin_hits) != 1 or len(end_hits) != 1 or begin_hits[0] >= end_hits[0]:
        raise SyncError(f"malformed or duplicated {label} markers; repair the markers manually")
    start, stop = begin_hits[0], end_hits[0]
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    return offsets[start], offsets[stop + 1], b"".join(lines[start + 1:stop])


def marker_wrap(body: bytes, begin: bytes, end: bytes) -> bytes:
    if body and not body.endswith((b"\n", b"\r")):
        body += b"\n"
    return begin + b"\n" + body + end + b"\n"


def replace_region(existing: bytes, old_region: tuple[int, int, bytes] | None,
                   body: bytes, begin: bytes, end: bytes) -> bytes:
    wrapped = marker_wrap(body, begin, end)
    if old_region:
        start, stop, _ = old_region
        return existing[:start] + wrapped + existing[stop:]
    if existing and not existing.endswith(b"\n"):
        existing += b"\n"
    if existing and not existing.endswith(b"\n\n"):
        existing += b"\n"
    return existing + wrapped


def legacy_candidates(relative: str) -> list[bytes]:
    current = source_bytes(relative)
    historical = historical_bytes(relative)
    return list(dict.fromkeys([current, *historical]))


def toml_agents_table(data: bytes) -> tuple[int, int, bytes] | None:
    """Locate a simple [agents] table in TOML source text, preserving its bytes."""
    lines = data.splitlines(keepends=True)
    headers = []
    offset = 0
    for i, line in enumerate(lines):
        match = re.match(rb"\s*\[([^\]]+)\]\s*(?:#.*)?(?:\r?\n)?$", line)
        if match:
            headers.append((i, offset, match.group(1).strip()))
        offset += len(line)
    matches = [n for n, (_, _, name) in enumerate(headers) if name == b"agents"]
    if not matches:
        return None
    if len(matches) != 1:
        raise SyncError("target .codex/config.toml has duplicate [agents] tables")
    n = matches[0]
    start_line, start, _ = headers[n]
    stop = headers[n + 1][1] if n + 1 < len(headers) else len(data)
    return start, stop, data[start:stop]


def parsed_toml(data: bytes, rel: str) -> dict:
    try:
        return tomllib.loads(data.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise SyncError(f"{rel} is not valid TOML: {exc}") from exc


def verify_toml(data: bytes) -> None:
    parsed = parsed_toml(data, ".codex/config.toml")
    source = parsed_toml(source_bytes(".codex/config.toml"), "workflow/.codex/config.toml")
    if parsed.get("agents") != source.get("agents"):
        raise SyncError("merged TOML does not contain the workflow's complete [agents] table")


def prepare_markdown(target: Path, rel: str, previous: str | None) -> Change:
    source = source_bytes(rel)
    path = target / rel
    exists = path.exists() or path.is_symlink()
    if exists and (path.is_symlink() or not path.is_file()):
        raise SyncError(f"unsafe target path: {path}")
    existing = path.read_bytes() if exists else b""
    region = marker_region(existing, MARKDOWN_BEGIN.encode(), MARKDOWN_END.encode(), rel)
    candidates = legacy_candidates(rel)
    if region:
        managed = region[2]
        if previous and digest(managed) != previous and managed != source:
            raise SyncError(f"locally edited managed content: {path}; restore its marked block before syncing")
        if not previous and managed not in candidates:
            raise SyncError(f"unrecorded managed block differs from known workflow versions: {path}")
        updated = replace_region(existing, region, source, MARKDOWN_BEGIN.encode(), MARKDOWN_END.encode())
        return Change(rel, path, updated, digest(source), "update" if updated != existing else "unchanged")
    if not exists or not existing.strip():
        updated = marker_wrap(source, MARKDOWN_BEGIN.encode(), MARKDOWN_END.encode())
        return Change(rel, path, updated, digest(source), "create")
    # Existing unmarked whole-file or embedded historical copies are safe to adopt
    # only when one exact candidate occurs exactly once.
    matches = [(candidate, existing.find(candidate)) for candidate in candidates if candidate and existing.count(candidate) == 1]
    # Exact whole-file copies are unambiguous even when one historical version
    # happens to be a prefix of another. For embedded copies, prefer the longest
    # exact candidate at a shared offset and reject genuinely competing matches.
    exact = [candidate for candidate in candidates if existing == candidate]
    if exact:
        candidate, start = max(exact, key=len), 0
        matches = [(candidate, start)]
    elif matches:
        max_len = max(len(candidate) for candidate, _ in matches)
        longest = [(candidate, start) for candidate, start in matches if len(candidate) == max_len]
        offsets = {start for _, start in longest}
        if len(longest) == 1 or len(offsets) == 1:
            candidate, start = longest[0]
            matches = [(candidate, start)]
        else:
            matches = []
    if len(matches) == 1:
        candidate, start = matches[0]
        updated = existing[:start] + marker_wrap(source if candidate == source else candidate,
                                                 MARKDOWN_BEGIN.encode(), MARKDOWN_END.encode()) + existing[start + len(candidate):]
        region2 = marker_region(updated, MARKDOWN_BEGIN.encode(), MARKDOWN_END.encode(), rel)
        assert region2 is not None
        if previous and digest(region2[2]) != previous:
            raise SyncError(f"unrecorded legacy block conflicts with saved state: {path}")
        if candidate != source:
            updated = replace_region(updated, region2, source, MARKDOWN_BEGIN.encode(), MARKDOWN_END.encode())
        return Change(rel, path, updated, digest(source), "migrate" if updated != existing else "unchanged")
    raise SyncError(
        f"conflict in {path}: unmarked instructions are not an exact known workflow copy. "
        "Place <!-- agent-workflow:begin --> and <!-- agent-workflow:end --> around only the workflow-owned text, "
        "leaving project instructions outside, then retry."
    )


def prepare_toml(target: Path, rel: str, previous: str | None) -> Change:
    source = source_bytes(rel)
    source_table = toml_agents_table(source)
    if source_table is None:
        raise SyncError("workflow/.codex/config.toml has no [agents] table")
    table = source_table[2]
    path = target / rel
    exists = path.exists() or path.is_symlink()
    if exists and (path.is_symlink() or not path.is_file()):
        raise SyncError(f"unsafe target path: {path}")
    existing = path.read_bytes() if exists else b""
    parsed_toml(existing, rel) if existing.strip() else {}
    region = marker_region(existing, TOML_BEGIN.encode(), TOML_END.encode(), rel)
    if region:
        managed = region[2]
        if previous and digest(managed) != previous and managed != table:
            raise SyncError(f"locally edited managed content: {path}; restore its marked table before syncing")
        if not previous and managed != table and managed not in [x for candidate in legacy_candidates(rel)
                                                                  if (x := (toml_agents_table(candidate) or (0, 0, b""))[2])]:
            raise SyncError(f"unrecorded managed [agents] table differs from known workflow versions: {path}")
        updated = replace_region(existing, region, table, TOML_BEGIN.encode(), TOML_END.encode())
    else:
        target_table = toml_agents_table(existing) if existing.strip() else None
        if not target_table:
            updated = replace_region(existing, None, table, TOML_BEGIN.encode(), TOML_END.encode())
        else:
            candidates = [toml_agents_table(x)[2] for x in legacy_candidates(rel) if toml_agents_table(x)]
            if target_table[2] not in candidates:
                raise SyncError(
                    f"conflict in {path}: [agents] contains local keys or is not an exact known workflow table. "
                    "Move project-specific settings to another TOML table, then add # agent-workflow:begin and "
                    "# agent-workflow:end around the workflow-owned [agents] table."
                )
            updated = existing[:target_table[0]] + marker_wrap(table, TOML_BEGIN.encode(), TOML_END.encode()) + existing[target_table[1]:]
    verify_toml(updated)
    if updated == existing:
        action = "unchanged"
    elif region:
        action = "update"
    elif target_table:
        action = "migrate"
    else:
        action = "create" if not existing else "update"
    return Change(rel, path, updated, digest(table), action)


def normalized_target(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path)
    return Path(os.path.abspath(path))


def target_root(raw: str) -> Path:
    path = normalized_target(raw)
    if path.is_symlink() or not path.is_dir():
        raise SyncError(f"target must be an existing non-symlink directory: {path}")
    return path


def check_safe_parents(target: Path, relative: str) -> None:
    current = target
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise SyncError(f"unsafe symlink in target path: {current}")
        if current.exists() and current != target / relative and not current.is_dir():
            raise SyncError(f"target parent is not a directory: {current}")


def sync_one(raw: str, registry: dict, dry_run: bool) -> list[str]:
    target = target_root(raw)
    key = str(target)
    target_state = registry["targets"].get(key, {})
    hashes = target_state.get("hashes", {})
    if not isinstance(hashes, dict):
        raise SyncError(f"invalid saved hashes for target {target}")
    changes: list[Change] = []
    for rel in OWNED:
        check_safe_parents(target, rel)
        if rel == "AGENTS.md":
            change = prepare_markdown(target, rel, hashes.get(rel))
        elif rel == ".codex/config.toml":
            change = prepare_toml(target, rel, hashes.get(rel))
        else:
            source = source_bytes(rel)
            path = target / rel
            exists = path.exists() or path.is_symlink()
            if exists and (path.is_symlink() or not path.is_file()):
                raise SyncError(f"unsafe target path: {path}")
            old = path.read_bytes() if exists else None
            old_hash = digest(old) if old is not None else None
            previous = hashes.get(rel)
            known_legacy = old in historical_bytes(rel) if old is not None and previous is None else False
            if old is not None and old_hash != digest(source) and (previous is None or old_hash != previous) and not known_legacy:
                raise SyncError(f"locally edited or unknown owned file: {path}; move local content elsewhere before syncing")
            change = Change(rel, path, source, digest(source), "create" if old is None else "update" if old != source else "unchanged")
        changes.append(change)

    # Validate all prospective results and paths before any target mutation.
    for change in changes:
        check_safe_parents(target, change.relative)
        if change.relative == ".codex/config.toml":
            verify_toml(change.data)
    plan = [f"{change.action}: {change.path}" for change in changes if change.action != "unchanged"]
    if dry_run:
        return plan or [f"unchanged: {target}"]
    for change in changes:
        if change.action != "unchanged":
            atomic_write(change.path, change.data)
    registry["targets"][key] = {"hashes": {change.relative: change.managed_hash for change in changes}}
    save_registry(registry)
    return plan or [f"unchanged: {target}"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="sync every registered target")
    group.add_argument("--register", metavar="PATH", help="register a target path")
    group.add_argument("--unregister", metavar="PATH", help="remove a registered target")
    group.add_argument("--list", action="store_true", help="list registered targets")
    parser.add_argument("target", nargs="?", help="target project directory")
    parser.add_argument("--dry-run", action="store_true", help="show changes without writing target or registry files")
    args = parser.parse_args(argv)
    try:
        registry = load_registry()
        if args.register:
            target = str(target_root(args.register))
            if not args.dry_run:
                registry["targets"].setdefault(target, {"hashes": {}})
                save_registry(registry)
            print(("would register" if args.dry_run else "registered") + f": {target}")
            return 0
        if args.unregister:
            # Unregister must work after a project directory was deleted.
            target = str(normalized_target(args.unregister))
            if target not in registry["targets"]:
                raise SyncError(f"target is not registered: {target}")
            if not args.dry_run:
                del registry["targets"][target]
                save_registry(registry)
            print(("would unregister" if args.dry_run else "unregistered") + f": {target}")
            return 0
        if args.list:
            for target in sorted(registry["targets"]):
                print(target)
            return 0
        if args.all:
            if args.target:
                parser.error("do not provide a positional target with --all")
            targets = sorted(registry["targets"])
            if not targets:
                raise SyncError("no registered targets; register one with --register PATH")
        elif args.target:
            targets = [args.target]
        else:
            parser.error("provide a target directory or use --all")
        # Preflight every target before writing any target, including --all.
        plans = []
        for raw in targets:
            plans.append((raw, sync_one(raw, registry, True)))
        if args.dry_run:
            for _, lines in plans:
                for line in lines:
                    print(line)
            return 0
        # Sync sequentially. sync_one performs complete per-target validation.
        # --all uses a cloned registry so failed target preflight does not persist partial registry state.
        final_registry = load_registry()
        for raw, _ in plans:
            lines = sync_one(raw, final_registry, False)
            for line in lines:
                print(line)
        return 0
    except SyncError as exc:
        print(f"sync-workflow: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"sync-workflow: file operation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
