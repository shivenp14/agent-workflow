import importlib.util
import json
import copy
import stat
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_workflow.py"
spec = importlib.util.spec_from_file_location("sync_workflow", SCRIPT)
sync = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sync
spec.loader.exec_module(sync)


class SyncWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.target = self.root / "project"
        self.target.mkdir()
        self.registry = self.root / "registry.json"
        self.real_registry = sync.ROOT / ".workflow-sync-state.json"
        self.real_registry_before = self.real_registry.read_bytes() if self.real_registry.exists() else None
        self.registry_patcher = patch.object(sync, "REGISTRY", self.registry)
        self.registry_patcher.start()

    def tearDown(self):
        try:
            current = self.real_registry.read_bytes() if self.real_registry.exists() else None
            self.assertEqual(current, self.real_registry_before, "test modified the real workflow registry")
        finally:
            self.registry_patcher.stop()
            self.temp.cleanup()

    def registry_value(self, hashes=None):
        return {"version": 1, "targets": {str(self.target): {"hashes": hashes or {}}}}

    def test_sync_is_idempotent_and_preserves_unrelated_files_and_toml_tables(self):
        config = self.target / ".codex" / "config.toml"
        config.parent.mkdir()
        config.write_text('[project]\nname = "demo"\n', encoding="utf-8")
        unrelated = self.target / "notes.txt"
        unrelated.write_text("keep me", encoding="utf-8")
        state = self.registry_value()
        first = sync.sync_one(str(self.target), state, False)
        self.assertTrue(first)
        parsed = tomllib.loads(config.read_text(encoding="utf-8"))
        self.assertEqual(parsed["project"]["name"], "demo")
        self.assertEqual(parsed["agents"], tomllib.loads((sync.ROOT / ".codex/config.toml").read_text())["agents"])
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep me")
        second = sync.sync_one(str(self.target), state, False)
        self.assertEqual(second, [f"unchanged: {self.target}"])
        created_file = self.target / ".codex" / "agents" / "explorer.toml"
        self.assertEqual(stat.S_IMODE(created_file.stat().st_mode), 0o644)

    def test_atomic_replacement_preserves_existing_file_mode(self):
        state = self.registry_value()
        sync.sync_one(str(self.target), state, False)
        file = self.target / ".codex" / "agents" / "explorer.toml"
        file.chmod(0o640)
        source_bytes = sync.source_bytes
        with patch.object(sync, "source_bytes", side_effect=lambda rel: source_bytes(rel) + b"\n# updated\n" if rel == ".codex/agents/explorer.toml" else source_bytes(rel)):
            sync.sync_one(str(self.target), state, False)
        self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o640)

    def test_retry_recovers_when_target_writes_succeed_but_state_save_fails(self):
        state = self.registry_value()
        sync.sync_one(str(self.target), state, False)
        stale_state = copy.deepcopy(state)
        source_bytes = sync.source_bytes

        def changed_source(rel):
            data = source_bytes(rel)
            if rel == "AGENTS.md":
                return data + b"\nSource update after original sync.\n"
            if rel == ".codex/config.toml":
                return data + b"\n# source update after original sync\n"
            return data

        with patch.object(sync, "source_bytes", side_effect=changed_source), patch.object(sync, "save_registry", side_effect=OSError("injected registry failure")):
            with self.assertRaisesRegex(OSError, "injected registry failure"):
                sync.sync_one(str(self.target), state, False)
        with patch.object(sync, "source_bytes", side_effect=changed_source):
            plan = sync.sync_one(str(self.target), stale_state, True)
        self.assertEqual(plan, [f"unchanged: {self.target}"])

    def test_dry_run_does_not_create_targets_or_registry_state(self):
        state = self.registry_value()
        plan = sync.sync_one(str(self.target), state, True)
        self.assertTrue(any(line.startswith("create:") for line in plan))
        self.assertFalse((self.target / "AGENTS.md").exists())
        self.assertEqual(state["targets"][str(self.target)]["hashes"], {})

    def test_managed_edits_fail_but_outside_markdown_edits_survive(self):
        state = self.registry_value()
        sync.sync_one(str(self.target), state, False)
        agents = self.target / "AGENTS.md"
        data = agents.read_bytes()
        agents.write_bytes(data + b"\nLocal project note.\n")
        sync.sync_one(str(self.target), state, False)
        self.assertIn(b"Local project note.", agents.read_bytes())
        changed = agents.read_bytes().replace(b"For substantial software tasks", b"For altered software tasks", 1)
        agents.write_bytes(changed)
        with self.assertRaisesRegex(sync.SyncError, "locally edited managed content"):
            sync.sync_one(str(self.target), state, True)

    def test_exact_historical_mixed_sources_migrate(self):
        old_agents = b"# Historical workflow policy\n"
        old_config = b"[agents]\nenabled = true\n\nlegacy_default = true\n"
        (self.target / "AGENTS.md").write_bytes(b"# Local preface\n\n" + old_agents + b"\n# Local suffix\n")
        config = self.target / ".codex" / "config.toml"
        config.parent.mkdir()
        config.write_bytes(old_config + b"[project]\nname = 'migrated'\n")
        with patch.object(sync, "legacy_candidates", side_effect=lambda rel: [old_agents] if rel == "AGENTS.md" else [old_config]):
            sync.sync_one(str(self.target), self.registry_value(), True)
            state = self.registry_value()
            sync.sync_one(str(self.target), state, False)
        self.assertIn(b"# Local preface", (self.target / "AGENTS.md").read_bytes())
        self.assertIn(b"# Local suffix", (self.target / "AGENTS.md").read_bytes())
        self.assertEqual(tomllib.loads(config.read_text())["project"]["name"], "migrated")

    def test_conflict_preflight_leaves_all_target_files_untouched(self):
        (self.target / "AGENTS.md").write_text("# Existing local instructions\n", encoding="utf-8")
        bad = self.target / ".codex" / "agents" / "reviewer.toml"
        bad.parent.mkdir(parents=True)
        bad.write_text("local agent", encoding="utf-8")
        with self.assertRaisesRegex(sync.SyncError, "conflict in"):
            sync.sync_one(str(self.target), self.registry_value(), False)
        self.assertEqual((self.target / "AGENTS.md").read_text(), "# Existing local instructions\n")
        self.assertFalse((self.target / ".codex/config.toml").exists())

    def test_target_symlink_is_rejected(self):
        real = self.root / "real"
        real.mkdir()
        link = self.root / "link"
        link.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(sync.SyncError, "non-symlink directory"):
            sync.sync_one(str(link), self.registry_value(), True)

    def test_owned_file_symlink_is_rejected(self):
        outside = self.root / "outside.md"
        outside.write_text("leave this alone", encoding="utf-8")
        (self.target / "AGENTS.md").symlink_to(outside)
        with self.assertRaisesRegex(sync.SyncError, "unsafe symlink"):
            sync.sync_one(str(self.target), self.registry_value(), True)
        self.assertEqual(outside.read_text(encoding="utf-8"), "leave this alone")

    def test_all_preflights_every_registered_target_before_writing(self):
        good = self.root / "good"
        bad = self.root / "bad"
        good.mkdir()
        bad.mkdir()
        (bad / "AGENTS.md").write_text("local content\n", encoding="utf-8")
        registry = {"version": 1, "targets": {str(good): {"hashes": {}}, str(bad): {"hashes": {}}}}
        self.registry.write_text(json.dumps(registry), encoding="utf-8")
        with patch.object(sync, "REGISTRY", self.registry), redirect_stdout(StringIO()):
            self.assertEqual(sync.main(["--all"]), 2)
        self.assertFalse((good / "AGENTS.md").exists())

    def test_registry_round_trip(self):
        self.assertEqual(sync.main(["--register", str(self.target)]), 0)
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(sync.main(["--list"]), 0)
        self.assertEqual(output.getvalue().strip(), str(self.target))
        self.assertEqual(json.loads(self.registry.read_text())["targets"][str(self.target)]["hashes"], {})

    def test_unregister_removes_target_after_directory_deletion(self):
        self.assertEqual(sync.main(["--register", str(self.target)]), 0)
        self.target.rmdir()
        with redirect_stdout(StringIO()):
            self.assertEqual(sync.main(["--unregister", str(self.target)]), 0)
        self.assertEqual(json.loads(self.registry.read_text())["targets"], {})

    def test_project_keys_in_agents_table_are_a_conflict(self):
        config = self.target / ".codex" / "config.toml"
        config.parent.mkdir()
        config.write_text('[agents]\nenabled = true\nproject_mode = "custom"\n', encoding="utf-8")
        with self.assertRaisesRegex(sync.SyncError, "conflict in"):
            sync.sync_one(str(self.target), self.registry_value(), True)

    def test_registry_register_list_and_dry_run_are_local(self):
        state = {"version": 1, "targets": {}}
        with patch.object(sync, "REGISTRY", self.registry):
            with patch.object(sync, "load_registry", return_value=state), patch.object(sync, "save_registry") as save:
                self.assertEqual(sync.main(["--register", str(self.target), "--dry-run"]), 0)
                save.assert_not_called()
            self.assertFalse(self.registry.exists())


if __name__ == "__main__":
    unittest.main()
