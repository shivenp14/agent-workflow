#!/usr/bin/env python3
"""Update model assignments consistently across this workflow source tree."""

from __future__ import annotations

import argparse
import difflib
import os
import re
import stat
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "workflow"
CONFIG = ".codex/config.toml"
AGENT_FILES = (
    ".codex/agents/explorer.toml",
    ".codex/agents/implementer.toml",
    ".codex/agents/reviewer.toml",
)
DOC_FILES = ("docs/agent/architecture.md", "docs/agent/testing.md")
DOC_FIELD = re.compile(
    r"<!-- agent-workflow-model:(orchestrator|subagent):(full|short):((?:[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9]|[A-Za-z0-9])) -->"
    r"([^<\r\n]+)<!-- /agent-workflow-model -->"
)
MODEL_ID = re.compile(r"(?:[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9]|[A-Za-z0-9])\Z")


class UpdateError(Exception):
    """An invalid model request or inconsistent workflow source tree."""


@dataclass(frozen=True)
class PlannedFile:
    relative: str
    path: Path
    old: bytes
    new: bytes


def _read_source(root: Path, relative: str) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise UpdateError(f"workflow source is missing or unsafe: {relative}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise UpdateError(f"cannot read {relative}: {exc}") from exc


def _toml(data: bytes, relative: str) -> dict:
    try:
        return tomllib.loads(data.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise UpdateError(f"{relative} is not valid TOML: {exc}") from exc


def _model_line(data: bytes, relative: str, key: str, expected: str) -> bytes:
    """Validate a root-level TOML model field and return its source line."""
    matches = list(re.finditer(rb"(?m)^([ \t]*" + re.escape(key.encode()) + rb"[ \t]*=[ \t]*)\"([^\"\r\n]*)\"([ \t]*(?:#.*)?)$", data))
    if len(matches) != 1:
        raise UpdateError(f"{relative} must contain exactly one {key} string field")
    if matches[0].group(2).decode("utf-8", errors="replace") != expected:
        raise UpdateError(f"{relative} {key} does not match the current workflow model")
    return matches[0].group(0)


def _replace_config_model(data: bytes, expected: str, replacement: str) -> bytes:
    lines = data.splitlines(keepends=True)
    agents_start: int | None = None
    agents_stop = len(lines)
    for index, line in enumerate(lines):
        match = re.match(rb"\s*\[([^\]]+)\]\s*(?:#.*)?(?:\r?\n)?$", line)
        if not match:
            continue
        name = match.group(1).strip()
        if agents_start is not None:
            agents_stop = index
            break
        if name == b"agents":
            if agents_start is not None:
                raise UpdateError(".codex/config.toml has duplicate [agents] tables")
            agents_start = index
    if agents_start is None:
        raise UpdateError(".codex/config.toml is missing its [agents] table")
    field = re.compile(rb'^(\s*default_subagent_model\s*=\s*)"([^"\r\n]*)"(\s*(?:#.*)?)$')
    hits = [i for i in range(agents_start + 1, agents_stop) if field.match(lines[i].rstrip(b"\r\n"))]
    if len(hits) != 1:
        raise UpdateError(".codex/config.toml [agents] must contain exactly one default_subagent_model")
    index = hits[0]
    match = field.match(lines[index].rstrip(b"\r\n"))
    assert match is not None
    if match.group(2).decode() != expected:
        raise UpdateError(".codex/config.toml default_subagent_model does not match the current workflow model")
    ending = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = match.group(1) + b'"' + replacement.encode() + b'"' + match.group(3) + ending
    return b"".join(lines)


def _validate_requests(args: argparse.Namespace) -> dict[str, tuple[str, str | None]]:
    requested: dict[str, tuple[str, str | None]] = {}
    for role, model_id, display in (
        ("orchestrator", args.orchestrator, args.orchestrator_display_name),
        ("subagent", args.subagent, args.subagent_display_name),
    ):
        if model_id is None:
            if display is not None:
                raise UpdateError(f"--{role}-display-name requires --{role}")
            continue
        if not MODEL_ID.fullmatch(model_id):
            raise UpdateError(f"invalid {role} model ID; use a non-empty slug containing only letters, digits, '.', '_' or '-'")
        if display is not None and (not display.strip() or any(ch in display for ch in "<>\r\n") or any(ord(ch) < 32 for ch in display)):
            raise UpdateError(f"invalid {role} display name; use non-empty single-line text without angle brackets")
        requested[role] = (model_id, display.strip() if display is not None else None)
    return requested


def _short_name(display: str) -> str:
    return display.split()[-1]


def _infer_display(model_id: str) -> str:
    """Make a readable default label; callers can supply an explicit label."""
    gpt_model = re.fullmatch(r"gpt-([0-9]+(?:\.[0-9]+)*?)-(.+)", model_id, re.IGNORECASE)
    if gpt_model:
        suffix = re.split(r"[-_.]+", gpt_model.group(2))
        return f"GPT-{gpt_model.group(1)} " + " ".join(word.capitalize() for word in suffix)
    words = re.split(r"[-_.]+", model_id)
    return " ".join(word.upper() if word.lower() == "gpt" else word.capitalize() for word in words)


def _doc_fields(data: bytes, relative: str) -> list[tuple[str, str, str, str]]:
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise UpdateError(f"{relative} is not UTF-8 text") from exc
    found = [(match.group(1), match.group(2), match.group(3), match.group(4)) for match in DOC_FIELD.finditer(text)]
    expected = {
        "docs/agent/architecture.md": {"orchestrator": 1, "subagent": 1},
        "docs/agent/testing.md": {"orchestrator": 3, "subagent": 4},
    }[relative]
    counts = {role: sum(1 for found_role, _, _, _ in found if found_role == role) for role in expected}
    if counts != expected:
        raise UpdateError(f"{relative} has unexpected workflow model fields (expected {expected}, found {counts})")
    return found


def _current_displays(doc_bytes: dict[str, bytes]) -> tuple[dict[str, str], dict[str, str]]:
    displays: dict[str, str] = {}
    ids: dict[str, str] = {}
    short_values: dict[str, list[str]] = {"orchestrator": [], "subagent": []}
    for relative, data in doc_bytes.items():
        for role, style, model_id, value in _doc_fields(data, relative):
            if role in ids and ids[role] != model_id:
                raise UpdateError(f"documentation has inconsistent {role} model IDs")
            ids[role] = model_id
            if style == "full":
                if role in displays and displays[role] != value:
                    raise UpdateError(f"documentation has inconsistent {role} display names")
                displays[role] = value
            else:
                short_values[role].append(value)
    for role in displays:
        if any(value != _short_name(displays[role]) for value in short_values[role]):
            raise UpdateError(f"documentation has inconsistent {role} short display names")
    if set(displays) != {"orchestrator", "subagent"}:
        raise UpdateError("documentation is missing full display names for a workflow model")
    return displays, ids


def build_plan(root: Path, requested: dict[str, tuple[str, str | None]]) -> tuple[dict[str, str], dict[str, str], list[PlannedFile]]:
    config_data = _read_source(root, CONFIG)
    config = _toml(config_data, CONFIG)
    agents = config.get("agents")
    if not isinstance(agents, dict) or not isinstance(agents.get("default_subagent_model"), str):
        raise UpdateError(".codex/config.toml must define [agents].default_subagent_model as a string")
    current = {"subagent": agents["default_subagent_model"]}
    _replace_config_model(config_data, current["subagent"], current["subagent"])

    agent_data = {relative: _read_source(root, relative) for relative in AGENT_FILES}
    for relative, data in agent_data.items():
        parsed = _toml(data, relative)
        if not isinstance(parsed.get("model"), str):
            raise UpdateError(f"{relative} must define a root model string")
        _model_line(data, relative, "model", parsed["model"])
        if relative == AGENT_FILES[0]:
            agent_model = parsed["model"]
        elif parsed["model"] != agent_model:
            raise UpdateError("worker agent model fields do not agree")

    docs = {relative: _read_source(root, relative) for relative in DOC_FILES}
    displays, doc_ids = _current_displays(docs)
    current["orchestrator"] = doc_ids["orchestrator"]
    if doc_ids["subagent"] != current["subagent"] or agent_model != current["subagent"]:
        raise UpdateError("worker agent and documentation model IDs do not match [agents].default_subagent_model")
    selected: dict[str, tuple[str, str]] = {}
    for role, (model, display) in requested.items():
        label = display if display is not None else displays[role] if model == current[role] else _infer_display(model)
        selected[role] = (model, label)
    for role, (model, display) in selected.items():
        current[role] = model
        displays[role] = display

    planned: list[PlannedFile] = []
    new_config = config_data
    if "subagent" in selected:
        new_config = _replace_config_model(config_data, agents["default_subagent_model"], current["subagent"])
    if new_config != config_data:
        planned.append(PlannedFile(CONFIG, root / CONFIG, config_data, new_config))

    if "subagent" in selected:
        for relative, data in agent_data.items():
            new = re.sub(rb'(?m)^(\s*model\s*=\s*)"[^"\r\n]*"', lambda m: m.group(1) + b'"' + current["subagent"].encode() + b'"', data, count=1)
            if new != data:
                planned.append(PlannedFile(relative, root / relative, data, new))

    for relative, data in docs.items():
        fields = _doc_fields(data, relative)
        text = data.decode("utf-8")
        def replace(match: re.Match[str]) -> str:
            role, style = match.group(1), match.group(2)
            if role not in selected:
                return match.group(0)
            display = displays[role]
            value = display if style == "full" else _short_name(display)
            return f"<!-- agent-workflow-model:{role}:{style}:{current[role]} -->{value}<!-- /agent-workflow-model -->"
        updated = DOC_FIELD.sub(replace, text).encode("utf-8")
        if updated != data:
            planned.append(PlannedFile(relative, root / relative, data, updated))

    return current, displays, planned


def atomic_write(path: Path, data: bytes) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
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


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Agent workflow (replace MODEL_ID with the requested model ID):
  ./scripts/update-models --show
  ./scripts/update-models --orchestrator MODEL_ID --dry-run
  ./scripts/update-models --subagent MODEL_ID --dry-run
  ./scripts/update-models --orchestrator MODEL_ID --subagent MODEL_ID --dry-run

Apply: repeat the preview command without --dry-run, then verify with --show.
Distribute when requested: ./scripts/sync-workflow --all --dry-run, then --all.

Scope: orchestrator changes update documentation recommendations; runtime
selection remains in T3 Code. Subagent changes update all worker model fields.
Reasoning settings are preserved. Model availability is not checked.
Paths resolve from the script location, independent of the working directory.
Exit codes: 0 = success/no changes; 2 = invalid input/source or I/O error.
See docs/agent/models.md for display-name options and conflict handling.""",
    )
    result.add_argument("--orchestrator", metavar="MODEL_ID", help="set the documented primary/orchestrator model")
    result.add_argument("--subagent", metavar="MODEL_ID", help="set the default spawned-worker model")
    result.add_argument("--orchestrator-display-name", metavar="NAME", help="documentation label for the orchestrator model")
    result.add_argument("--subagent-display-name", metavar="NAME", help="documentation label for the spawned-worker model")
    result.add_argument("--dry-run", action="store_true", help="show exact planned edits without writing files")
    result.add_argument("--show", action="store_true", help="show current role model IDs and documentation labels")
    return result


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    args = parser().parse_args(argv)
    try:
        requested = _validate_requests(args)
        if not args.show and not requested:
            raise UpdateError("choose --orchestrator, --subagent, or --show")
        current, displays, plan = build_plan(root, requested)
        # Plan construction validates all target files and computes every output before a write.
        doc_bytes = {relative: _read_source(root, relative) for relative in DOC_FILES}
        if args.show:
            print(f"orchestrator: {current['orchestrator']} ({displays['orchestrator']})")
            print(f"subagent: {current['subagent']} ({displays['subagent']})")
        if not plan:
            if not args.show:
                print("No changes needed.")
            return 0
        for item in plan:
            print(f"update: workflow/{item.relative}")
            if args.dry_run:
                before = item.old.decode("utf-8").splitlines(keepends=True)
                after = item.new.decode("utf-8").splitlines(keepends=True)
                diff = difflib.unified_diff(before, after,
                                            fromfile=f"workflow/{item.relative}",
                                            tofile=f"workflow/{item.relative}")
                sys.stdout.writelines(diff)
        if not args.dry_run:
            for item in plan:
                atomic_write(item.path, item.new)
        return 0
    except (UpdateError, OSError) as exc:
        print(f"update-models: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
