#!/usr/bin/env python3
"""Claude entrypoint integration checks; these do not invoke a model."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

KIT = Path(__file__).resolve().parents[2]
RUNNER = KIT / "tests/run-claude-regressions.py"
spec = importlib.util.spec_from_file_location("claude_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ClaudePreparationTests(unittest.TestCase):
    def test_positive_control_has_tracked_regressions_without_changing_codex(self):
        cases = [case for case in runner.workflow.CATALOG if case["id"] in ("01", "02")]
        with tempfile.TemporaryDirectory() as directory, patch.object(runner.workflow, "CATALOG", cases):
            root = Path(directory) / "claude"
            runner.workflow.prepare(root, runtime="claude")
            repo = root / "cases/02"
            tests = repo / "tests/regressions.rs"
            self.assertTrue(tests.is_file(), "Claude positive control needs its checked-in regression tests")
            self.assertFalse((root / "cases/01/tests/regressions.rs").exists())
            tracked = runner.workflow.shell(["git", "ls-files", "--error-unmatch", "tests/regressions.rs"], repo)
            self.assertEqual(tracked.returncode, 0, tracked.stderr)
            clean = runner.workflow.shell(["git", "status", "--porcelain", "--", "tests/regressions.rs"], repo)
            self.assertEqual(clean.stdout, "")
            inputs = json.loads((root / "inputs.json").read_text())
            self.assertEqual(inputs["02"]["files"]["tests/regressions.rs"]["sha256"],
                             hashlib.sha256(tests.read_bytes()).hexdigest())
            for command in [
                ["cargo", "fmt", "--all", "--", "--check"],
                ["cargo", "clippy", "--offline", "--locked", "--all-targets", "--all-features", "--", "-D", "warnings"],
                ["cargo", "test", "--offline", "--locked", "--all-features"],
            ]:
                result = runner.workflow.shell(command, repo)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if command[1] == "test":
                    self.assertIn("6 passed; 0 failed", result.stdout)
                    for name in ("tenant_isolation", "insufficient_funds", "unicode_preview",
                                 "expiry_boundary", "fee_rounding", "invalid_limit"):
                        self.assertIn(f"test {name} ... ok", result.stdout)
            codex = Path(directory) / "codex"
            runner.workflow.prepare(codex)
            self.assertFalse((codex / "cases/02/tests/regressions.rs").exists())

    def test_prepare_installs_claude_and_missing_reviews_never_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            prepared = subprocess.run(
                [sys.executable, str(RUNNER), str(root), "--phase", "prepare"],
                cwd=KIT, capture_output=True, text=True, timeout=180, check=False,
            )
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            identity = json.loads((root / "suite-identity.json").read_text())
            self.assertEqual(identity["runtime"], "claude")
            requests = json.loads((root / "review-requests.json").read_text())
            self.assertEqual(len(requests), 11)
            inputs = json.loads((root / "inputs.json").read_text())
            for request in requests:
                repo = Path(request["repo"])
                self.assertTrue((repo / ".claude/skills/rust-pr-review/scripts/check-report.sh").is_file())
                self.assertIn("CLAUDE.md", request["request"])
                self.assertFalse((Path(request["output"]) / "report.md").exists())
                if request["id"] in ("01", "02"):
                    requirements = (repo / "REQUIREMENTS.md").read_bytes()
                    self.assertIn(b"Rust u16::from_str, including an optional leading +", requirements)
                    self.assertEqual(inputs[request["id"]]["files"]["REQUIREMENTS.md"]["sha256"],
                                     hashlib.sha256(requirements).hexdigest())
            assessed = subprocess.run(
                [sys.executable, str(RUNNER), str(root), "--phase", "assess"],
                cwd=KIT, capture_output=True, text=True, timeout=30, check=False,
            )
            self.assertNotEqual(assessed.returncode, 0)
            results = json.loads((root / "review-results.json").read_text())
            self.assertEqual([item["status"] for item in results], ["PENDING"] * 11)


class ClaudeEvidenceTests(unittest.TestCase):
    """Synthetic boundary fixtures only; no fixture is a fresh model review."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "cases/01"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "src/lib.rs").write_text("pub fn value() -> u8 { 1 }\n")
        for command in [
            ["git", "init", "-q"],
            ["git", "add", "src"],
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
             "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"],
        ]:
            subprocess.run(command, cwd=self.repo, check=True, capture_output=True)
        (self.root / "suite-identity.json").write_text(json.dumps(runner.suite_identity(KIT, "claude")))
        inputs = {"01": runner.workflow.snapshot(self.repo, runtime="claude")}
        (self.root / "inputs.json").write_text(json.dumps(inputs))
        self.output = self.root / "reviews/01"
        self.output.mkdir(parents=True)
        self.report = self.output / "report.md"
        self.report.write_text("Synthetic provenance test; not a model report.\n")
        self.transcript = self.output / "native.json"
        self.transcript.write_text(json.dumps({
            "type": "result", "is_error": False,
            "session_id": "synthetic-validator-fixture", "result": self.report.read_text(),
        }))

    def tearDown(self):
        self.temporary.cleanup()

    def record(self):
        runner.record_review(self.root, "01", Path("reviews/01/native.json"))

    def test_unbound_report_is_rejected(self):
        self.assertTrue(runner.review_errors(self.root, "01"))

    def test_current_native_binding_is_accepted(self):
        self.record()
        self.assertEqual(runner.review_errors(self.root, "01"), [])

    def test_codex_provenance_is_rejected(self):
        self.record()
        path = self.output / "provenance.json"
        metadata = json.loads(path.read_text())
        metadata["runtime"] = "codex"
        path.write_text(json.dumps(metadata))
        self.assertTrue(runner.review_errors(self.root, "01"))

    def test_changed_report_is_rejected(self):
        self.record()
        self.report.write_text("Replaced report\n")
        self.assertTrue(runner.review_errors(self.root, "01"))

    def test_changed_source_is_rejected(self):
        self.record()
        (self.repo / "src/lib.rs").write_text("pub fn value() -> u8 { 2 }\n")
        self.assertTrue(runner.review_errors(self.root, "01"))

    def test_already_dirty_inputs_outside_src_cannot_change_after_review(self):
        names = [
            "Cargo.toml", "Cargo.lock", "REQUIREMENTS.md", "build.rs",
            ".cargo/config.toml", ".claude/skills/rust-pr-review/SKILL.md",
            "crates/provider/src/lib.rs",
        ]
        for name in names:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("committed\n")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
             "-c", "commit.gpgsign=false", "commit", "-qm", "all review inputs"],
            cwd=self.repo, check=True, capture_output=True,
        )
        names.append("provider/ffi.c")  # Nonignored, already-untracked provider input.
        for name in names:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("reviewed but dirty\n")
        initial = runner.workflow.snapshot(self.repo, runtime="claude")
        (self.root / "inputs.json").write_text(json.dumps({"01": initial}))
        self.record()
        for name in names:
            with self.subTest(path=name):
                path = self.repo / name
                path.write_text("changed after review\n")
                self.assertEqual(runner.workflow.snapshot(self.repo, runtime="claude")["status"], initial["status"])
                self.assertTrue(runner.review_errors(self.root, "01"))
                path.write_text("reviewed but dirty\n")

    def test_stale_suite_is_rejected(self):
        self.record()
        path = self.root / "suite-identity.json"
        metadata = json.loads(path.read_text())
        metadata["fingerprint"] = "old-kit"
        path.write_text(json.dumps(metadata))
        self.assertTrue(runner.review_errors(self.root, "01"))

    def test_missing_or_changed_transcript_is_rejected(self):
        self.record()
        self.transcript.write_text("{}")
        self.assertTrue(runner.review_errors(self.root, "01"))
        self.transcript.unlink()
        self.assertTrue(runner.review_errors(self.root, "01"))

    def test_failed_or_empty_native_run_cannot_be_recorded(self):
        for text in ["", "{}", '{"type":"result","session_id":"test","is_error":true}']:
            with self.subTest(transcript=text):
                self.transcript.write_text(text)
                with self.assertRaises(ValueError):
                    self.record()

    def test_record_does_not_overwrite_previous_provenance(self):
        self.record()
        with self.assertRaises(ValueError):
            self.record()

    def test_native_result_must_match_the_saved_report(self):
        metadata = json.loads(self.transcript.read_text())
        metadata["result"] = "READY"
        self.transcript.write_text(json.dumps(metadata))
        with self.assertRaises(ValueError):
            self.record()


class ClaudeIdentityTests(unittest.TestCase):
    def test_bundled_knowledge_changes_invalidate_claude_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            kit = Path(directory)
            files = {
                "install.sh": "installer",
                "install-claude.sh": "Claude installer",
                "vendored.tsv": "sources",
                "THIRD_PARTY_NOTICES.md": "notices",
                "tests/workflow/cases.json": "[]",
                "tests/e2e/results/2026-10-24/oracle/regressions.rs": "oracle",
                "codex-template/.agents/skills/rust-skills/SKILL.md": "knowledge v1",
            }
            for name, text in files.items():
                path = kit / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            before = runner.suite_identity(kit, "claude")
            (kit / "codex-template/.agents/skills/rust-skills/SKILL.md").write_text("knowledge v2")
            after = runner.suite_identity(kit, "claude")
            self.assertNotEqual(before["fingerprint"], after["fingerprint"])
            self.assertEqual(after["runtime"], "claude")
            self.assertNotIn("runtime", runner.suite_identity(kit))


class ClaudeSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "src/lib.rs").write_text("source\n")
        (self.repo / "Cargo.toml").write_text("manifest\n")
        (self.repo / ".gitignore").write_text("/target/\n/.code-review-graph/\n")
        for command in [
            ["git", "init", "-q"], ["git", "add", "."],
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
             "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"],
        ]:
            subprocess.run(command, cwd=self.repo, check=True, capture_output=True)

    def tearDown(self):
        self.temporary.cleanup()

    def snapshot(self):
        return runner.workflow.snapshot(self.repo, runtime="claude")

    def test_ignored_build_and_graph_outputs_do_not_change_binding(self):
        initial = self.snapshot()
        for name in ("target/debug/binary", ".code-review-graph/graph.db"):
            path = self.repo / name
            path.parent.mkdir(parents=True)
            path.write_bytes(b"generated output")
        self.assertEqual(self.snapshot(), initial)

    def test_internal_symlink_hashes_link_target_without_dereferencing(self):
        (self.repo / "source-link").symlink_to("src/lib.rs")
        result = self.snapshot()["files"]["source-link"]
        self.assertEqual(result, {
            "type": "symlink", "sha256": hashlib.sha256(b"src/lib.rs").hexdigest(),
        })

    def test_escaping_symlink_is_rejected(self):
        (self.root / "outside").write_bytes(b"must not be read")
        (self.repo / "source-link").symlink_to("../outside")
        with self.assertRaisesRegex(ValueError, "escaping symlink"):
            self.snapshot()

    def test_tracked_symlink_to_ignored_input_is_rejected(self):
        with (self.repo / ".gitignore").open("a") as stream:
            stream.write("/ignored_impl.rs\n")
        (self.repo / "ignored_impl.rs").write_bytes(b"unbound provider")
        (self.repo / "src/link.rs").symlink_to("../ignored_impl.rs")
        subprocess.run(["git", "add", "src/link.rs"], cwd=self.repo, check=True, capture_output=True)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.snapshot()

    def test_symlink_to_deleted_tracked_target_is_rejected(self):
        (self.repo / "source-link").symlink_to("Cargo.toml")
        (self.repo / "Cargo.toml").unlink()
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.snapshot()

    def test_symlink_to_directory_is_rejected(self):
        (self.repo / "source-link").symlink_to("src", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.snapshot()

    def test_indirect_symlink_is_rejected_without_following_chain(self):
        (self.repo / "a-link").symlink_to("src/lib.rs")
        (self.repo / "b-link").symlink_to("a-link")
        with self.assertRaisesRegex(ValueError, "indirect symlink"):
            self.snapshot()

    def test_symlink_replacing_tracked_parent_is_rejected(self):
        path = self.repo / "nested/lib.rs"
        path.parent.mkdir()
        path.write_text("tracked source\n")
        subprocess.run(["git", "add", "nested"], cwd=self.repo, check=True, capture_output=True)
        shutil.rmtree(path.parent)
        path.parent.symlink_to("src", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.snapshot()

    def test_deleted_tracked_input_is_recorded_as_missing(self):
        (self.repo / "Cargo.toml").unlink()
        self.assertEqual(self.snapshot()["files"]["Cargo.toml"], {"type": "missing"})

    def test_newline_in_git_filename_remains_bound_to_its_bytes(self):
        path = self.repo / "provider\ninput.rs"
        path.write_bytes(b"first")
        initial = self.snapshot()
        path.write_bytes(b"second")
        changed = self.snapshot()
        self.assertEqual(initial["status"], changed["status"])
        self.assertNotEqual(initial["files"][path.name], changed["files"][path.name])

    def test_permission_changes_are_bound_when_git_ignores_modes(self):
        subprocess.run(["git", "config", "core.filemode", "false"], cwd=self.repo,
                       check=True, capture_output=True)
        initial = self.snapshot()
        path = self.repo / "src/lib.rs"
        path.chmod(path.stat().st_mode | 0o100)
        changed = self.snapshot()
        self.assertEqual(initial["status"], changed["status"])
        self.assertNotEqual(initial["files"]["src/lib.rs"], changed["files"]["src/lib.rs"])

    def test_default_codex_snapshot_keeps_its_existing_format(self):
        actual = runner.workflow.snapshot(self.repo)
        self.assertEqual(set(actual), {"files", "status", "head"})
        self.assertEqual(actual["files"], {"src/lib.rs": hashlib.sha256(b"source\n").hexdigest()})


if __name__ == "__main__":
    unittest.main()
