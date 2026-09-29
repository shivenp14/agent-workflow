import importlib.util
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = SOURCE_ROOT / "workflow"
SCRIPT = SOURCE_ROOT / "scripts" / "update_models.py"
spec = importlib.util.spec_from_file_location("update_models", SCRIPT)
update = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = update
spec.loader.exec_module(update)

SYNC_SCRIPT = SOURCE_ROOT / "scripts" / "sync_workflow.py"
sync_spec = importlib.util.spec_from_file_location("sync_workflow_for_model_tests", SYNC_SCRIPT)
sync = importlib.util.module_from_spec(sync_spec)
sys.modules[sync_spec.name] = sync
sync_spec.loader.exec_module(sync)


class UpdateModelsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in (update.CONFIG, *update.AGENT_FILES, *update.DOC_FILES):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(WORKFLOW_ROOT / relative, destination)

    def tearDown(self):
        self.temp.cleanup()

    def contents(self):
        return {relative: (self.root / relative).read_bytes()
                for relative in (update.CONFIG, *update.AGENT_FILES, *update.DOC_FILES)}

    def run_update(self, *args):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = update.main(list(args), root=self.root)
        self.stdout = stdout.getvalue()
        self.stderr = stderr.getvalue()
        return result

    def test_show_reports_consistent_source_defaults(self):
        self.assertEqual(self.run_update("--show"), 0)
        self.assertIn("orchestrator: gpt-6.1-sol (GPT-6.1 Sol)", self.stdout)
        self.assertIn("subagent: gpt-6-luna (GPT-6 Luna)", self.stdout)

    def test_orchestrator_only_updates_its_doc_fields(self):
        old_config = (self.root / update.CONFIG).read_bytes()
        old_agents = {name: (self.root / name).read_bytes() for name in update.AGENT_FILES}
        self.assertEqual(self.run_update("--orchestrator", "vendor-model_2", "--orchestrator-display-name", "Vendor Model Two"), 0)
        self.assertEqual((self.root / update.CONFIG).read_bytes(), old_config)
        for name in update.AGENT_FILES:
            self.assertEqual((self.root / name).read_bytes(), old_agents[name])
        for name in update.DOC_FILES:
            data = (self.root / name).read_text()
            self.assertIn("orchestrator:full:vendor-model_2", data)
            self.assertIn("Vendor Model Two", data)
            self.assertIn("subagent:full:gpt-6-luna", data)
            self.assertIn("GPT-6 Luna", data)

    def test_subagent_updates_config_agents_docs_and_preserves_reasoning(self):
        self.assertEqual(self.run_update("--subagent", "provider-worker-v3", "--subagent-display-name", "Provider Worker V3"), 0)
        config = (self.root / update.CONFIG).read_text()
        self.assertIn('default_subagent_model = "provider-worker-v3"', config)
        self.assertIn('default_subagent_reasoning_effort = "high"', config)
        for name in update.AGENT_FILES:
            self.assertIn('model = "provider-worker-v3"', (self.root / name).read_text())
        for name in update.DOC_FILES:
            data = (self.root / name).read_text()
            self.assertIn("subagent:full:provider-worker-v3", data)
            self.assertIn("Provider Worker V3", data)
            self.assertIn("orchestrator:full:gpt-6.1-sol", data)
        test_doc = (self.root / update.DOC_FILES[1]).read_text()
        self.assertIn("subagent:short:provider-worker-v3", test_doc)
        self.assertIn("V3", test_doc)

    def test_same_id_for_both_roles_then_role_only_update_stays_independent(self):
        self.assertEqual(self.run_update("--orchestrator", "shared-model", "--orchestrator-display-name", "Shared Primary", "--subagent", "shared-model", "--subagent-display-name", "Shared Worker"), 0)
        self.assertEqual(self.run_update("--orchestrator", "next-primary", "--orchestrator-display-name", "Next Primary"), 0)
        self.assertIn("orchestrator:full:next-primary", (self.root / update.DOC_FILES[0]).read_text())
        self.assertIn("subagent:full:shared-model", (self.root / update.DOC_FILES[0]).read_text())
        self.assertIn('default_subagent_model = "shared-model"', (self.root / update.CONFIG).read_text())
        for name in update.AGENT_FILES:
            self.assertIn('model = "shared-model"', (self.root / name).read_text())

    def test_display_name_that_matches_id_does_not_corrupt_role_marker(self):
        self.assertEqual(self.run_update("--orchestrator", "worker-v1", "--orchestrator-display-name", "worker-v1"), 0)
        self.assertEqual(self.run_update("--orchestrator", "worker-v1", "--orchestrator-display-name", "Worker One"), 0)
        for name in update.DOC_FILES:
            data = (self.root / name).read_text()
            self.assertIn("orchestrator:full:worker-v1 -->Worker One", data)

    def test_repeated_custom_updates_and_noop_leave_files_unchanged(self):
        args = ("--subagent", "odd_vendor.model-4", "--subagent-display-name", "Odd Vendor Model Four")
        self.assertEqual(self.run_update(*args), 0)
        before = {path: (self.root / path).read_bytes() for path in (update.CONFIG, *update.AGENT_FILES, *update.DOC_FILES)}
        self.assertEqual(self.run_update(*args), 0)
        self.assertEqual(self.contents(), before)
        timestamps = {path: (self.root / path).stat().st_mtime_ns for path in before}
        self.assertEqual(self.run_update("--subagent", "odd_vendor.model-4", "--subagent-display-name", "Odd Vendor Model Four"), 0)
        self.assertEqual({path: (self.root / path).stat().st_mtime_ns for path in before}, timestamps)

    def test_current_defaults_are_noop_without_display_name_options(self):
        before = self.contents()
        timestamps = {path: (self.root / path).stat().st_mtime_ns for path in before}
        self.assertEqual(self.run_update("--orchestrator", "gpt-6.1-sol", "--subagent", "gpt-6-luna"), 0)
        self.assertEqual(self.contents(), before)
        self.assertEqual({path: (self.root / path).stat().st_mtime_ns for path in before}, timestamps)

    def test_inferred_gpt_label_keeps_version_punctuation(self):
        self.assertEqual(self.run_update("--orchestrator", "gpt-6.2-sol"), 0)
        for name in update.DOC_FILES:
            self.assertIn("orchestrator:full:gpt-6.2-sol -->GPT-6.2 Sol", (self.root / name).read_text())

    def test_dry_run_prints_diff_without_mutation(self):
        before = self.contents()
        self.assertEqual(self.run_update("--subagent", "new-worker", "--dry-run"), 0)
        self.assertIn("update: workflow/.codex/config.toml", self.stdout)
        self.assertIn('-default_subagent_model = "gpt-6-luna"', self.stdout)
        self.assertIn('+default_subagent_model = "new-worker"', self.stdout)
        self.assertEqual(self.contents(), before)

    def test_invalid_ids_and_schema_fail_before_any_write(self):
        before = self.contents()
        for model_id in ("", "two words", "bad;id", "-leading", "trailing-", "model\ninjected"):
            with self.subTest(model_id=model_id):
                self.assertEqual(self.run_update(f"--subagent={model_id}"), 2)
                self.assertEqual(self.contents(), before)
        config = self.root / update.CONFIG
        config.write_text(config.read_text().replace('default_subagent_model = "gpt-6-luna"', 'default_subagent_model = "other"'))
        broken = self.contents()
        self.assertEqual(self.run_update("--orchestrator", "new-primary"), 2)
        self.assertEqual(self.contents(), broken)

    def test_late_document_preflight_failure_prevents_config_write(self):
        doc = self.root / update.DOC_FILES[1]
        doc.write_text(doc.read_text().replace("agent-workflow-model:subagent:full:gpt-6-luna", "agent-workflow-model:subagent:full:broken-id", 1))
        before = self.contents()
        self.assertEqual(self.run_update("--subagent", "new-worker"), 2)
        self.assertEqual(self.contents(), before)

    def test_docs_and_unrelated_config_text_and_reasoning_are_preserved(self):
        config = self.root / update.CONFIG
        config.write_text(config.read_text() + '\n[project]\nlabel = "keep this"\n')
        test_doc = self.root / update.DOC_FILES[1]
        test_doc.write_text(test_doc.read_text() + "\nUnmarked reference to Luna for historical discussion.\n")
        self.assertEqual(self.run_update("--subagent", "another-worker", "--subagent-display-name", "Another Worker"), 0)
        self.assertIn('label = "keep this"', config.read_text())
        self.assertIn('default_subagent_reasoning_effort = "high"', config.read_text())
        self.assertIn("Unmarked reference to Luna for historical discussion.", test_doc.read_text())

    def test_atomic_write_preserves_permission_bits(self):
        target = self.root / update.CONFIG
        target.chmod(0o640)
        self.assertEqual(self.run_update("--subagent", "permission-check"), 0)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)

    def test_wrapper_show_works_from_arbitrary_working_directory(self):
        result = subprocess.run([str(SOURCE_ROOT / "scripts" / "update-models"), "--show"],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("orchestrator: gpt-6.1-sol (GPT-6.1 Sol)", result.stdout)
        self.assertIn("subagent: gpt-6-luna (GPT-6 Luna)", result.stdout)

    def test_model_update_then_sync_uses_workflow_source_and_target_paths(self):
        source = self.root / "workflow-source"
        for relative in sync.OWNED:
            destination = source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(WORKFLOW_ROOT / relative, destination)
        # Model docs and configuration are allowlisted under their target paths.
        target = self.root / "target-project"
        target.mkdir()
        registry_path = self.root / "sync-state.json"
        with patch.object(sync, "WORKFLOW", source), patch.object(sync, "REGISTRY", registry_path):
            self.assertEqual(update.main(["--subagent", "integration-worker"], root=source), 0)
            state = {"version": 1, "targets": {str(target): {"hashes": {}}}}
            sync.sync_one(str(target), state, False)
        target_config = (target / ".codex/config.toml").read_text()
        self.assertIn('default_subagent_model = "integration-worker"', target_config)
        self.assertIn("integration-worker", (target / ".codex/agents/explorer.toml").read_text())
        self.assertIn("integration-worker", (target / "docs/agent/architecture.md").read_text())
        self.assertIn(".codex/config.toml", state["targets"][str(target)]["hashes"])
        self.assertNotIn("workflow/.codex/config.toml", state["targets"][str(target)]["hashes"])


if __name__ == "__main__":
    unittest.main()
