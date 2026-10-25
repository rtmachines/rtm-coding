"""Mutate genuine Claude evidence; never create substitute model reviews.

Run after automatic diagnostics with CLAUDE_EVIDENCE_RUN pointing at that run.
Missing prerequisites are errors, never successful skips.
"""
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tests/check_claude_evidence.py"
EVIDENCE = ROOT / "claude-code/docs/verification/2026-10-25-claude-parity"


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("CLAUDE_EVIDENCE_RUN")
        if not configured:
            raise RuntimeError("CLAUDE_EVIDENCE_RUN must identify a completed automatic Claude run")
        cls.fresh_run = Path(configured).resolve()
        cls.archive = EVIDENCE / "claude-review-evidence.tar.gz"
        cls.manifest = json.loads((EVIDENCE / "archive-manifest.json").read_text())
        with tarfile.open(cls.archive) as archive:
            cls.members = {
                member.name: (member, archive.extractfile(member).read() if member.isfile() else None)
                for member in archive
            }

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def execute(self, archive=None, manifest=None, run=None):
        command = [sys.executable, str(CHECKER), str(run or self.fresh_run)]
        if archive is not None:
            command.extend(["--archive", str(archive), "--manifest", str(manifest)])
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)

    def rewritten(self, changes=None, missing=(), extras=(), modes=None):
        destination = self.root / "changed.tar"
        with tarfile.open(destination, "w") as archive:
            for name, (original, data) in self.members.items():
                if name in missing:
                    continue
                member = copy.copy(original)
                payload = (changes or {}).get(name, data)
                if member.isfile():
                    member.size = len(payload)
                if name in (modes or {}):
                    member.mode = modes[name]
                archive.addfile(member, io.BytesIO(payload) if member.isfile() else None)
            for member, data in extras:
                archive.addfile(member, io.BytesIO(data) if data is not None else None)
        manifest = dict(self.manifest, archive=destination.name,
                        sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                        bytes=destination.stat().st_size)
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        return destination, manifest_path

    def json_change(self, path, update):
        value = json.loads(self.members[path][1])
        update(value)
        return {path: json.dumps(value).encode()}

    def native_records(self, path):
        data = self.members[path][1]
        try:
            value = json.loads(data)
            return value if isinstance(value, list) else [value]
        except json.JSONDecodeError:
            return [json.loads(line) for line in data.splitlines() if line.strip()]

    def rejected(self, category, **mutations):
        result = self.execute(*self.rewritten(**mutations))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(category, result.stderr)

    def test_genuine_bundle_accepts_against_fresh_automatic_run(self):
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("49/49", result.stdout)
        self.assertIn("11/11", result.stdout)

    def test_missing_archive_fails(self):
        result = self.execute(self.root / "missing.tar", EVIDENCE / "archive-manifest.json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_changed_archive_digest_fails(self):
        manifest = dict(self.manifest, sha256="0" * 64)
        path = self.root / "manifest.json"
        path.write_text(json.dumps(manifest))
        result = self.execute(self.archive, path)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Archive integrity", result.stderr)

    def test_stale_suite_fails(self):
        changes = self.json_change("run/suite-identity.json", lambda value: value.update(fingerprint="stale"))
        self.rejected("Suite identity", changes=changes)

    def test_changed_reviewed_inputs_fail(self):
        changes = self.json_change("run/inputs.json", lambda value: value["01"].update(head="stale"))
        self.rejected("Reviewed inputs", changes=changes)

    def test_changed_archived_source_or_mode_fails(self):
        path = "run/cases/01/src/lib.rs"
        self.rejected("Archived source", changes={path: self.members[path][1] + b"\n// mutation\n"})
        self.rejected("Archived source", modes={path: 0o600})

    def test_missing_archived_source_fails(self):
        self.rejected("Archived source", missing={"run/cases/01/Cargo.toml"})

    def test_changed_report_fails(self):
        path = "run/reviews/01/report.md"
        self.rejected("Report provenance", changes={path: self.members[path][1] + b"\nMutation\n"})

    def test_changed_native_transcript_fails(self):
        provenance = json.loads(self.members["run/reviews/01/provenance.json"][1])
        path = "run/" + provenance["transcript"]
        self.rejected("Native transcript", changes={path: self.members[path][1] + b"\n"})

    def test_failed_native_result_cannot_be_rebound(self):
        path = "run/reviews/01/provenance.json"
        provenance = json.loads(self.members[path][1])
        transcript_path = "run/" + provenance["transcript"]
        records = self.native_records(transcript_path)
        result = [item for item in records if item.get("type") == "result"][-1]
        result["is_error"] = True
        payload = json.dumps(records).encode()
        provenance["transcript_sha256"] = hashlib.sha256(payload).hexdigest()
        self.rejected("Native result", changes={transcript_path: payload, path: json.dumps(provenance).encode()})

    def test_invalid_report_cannot_be_rebound(self):
        provenance_path = "run/reviews/01/provenance.json"
        provenance = json.loads(self.members[provenance_path][1])
        transcript_path = "run/" + provenance["transcript"]
        records = self.native_records(transcript_path)
        [item for item in records if item.get("type") == "result"][-1]["result"] = "## Verdict: REQUEST_CHANGES\n"
        report = b"## Verdict: REQUEST_CHANGES\n"
        payload = json.dumps(records).encode()
        provenance.update(transcript_sha256=hashlib.sha256(payload).hexdigest(),
                          report_sha256=hashlib.sha256(report).hexdigest())
        self.rejected("Report contract", changes={transcript_path: payload,
                      "run/reviews/01/report.md": report, provenance_path: json.dumps(provenance).encode()})

    def test_missing_report_or_unexpected_case_fails(self):
        self.rejected("Reports", missing={"run/reviews/01/report.md"})
        extra = tarfile.TarInfo("run/reviews/12/report.md")
        extra.size = 1
        self.rejected("Case IDs", extras=[(extra, b"x")])

    def test_missing_or_failed_semantic_evidence_fails(self):
        assessment = json.loads(self.members["run/semantic-assessment.json"][1])
        missing = next(path for path in assessment["01"]["evidence"] if path.endswith(".log"))
        self.rejected("Semantic evidence", missing={"run/" + missing})
        changes = self.json_change("run/semantic-assessment.json", lambda value: value["01"].update({"pass": False}))
        self.rejected("Semantic assessment", changes=changes)

    def test_unsafe_archive_members_fail(self):
        for name, kind in [("../outside", tarfile.REGTYPE), ("/tmp/outside", tarfile.REGTYPE),
                           ("run/./alias", tarfile.REGTYPE), ("run/link", tarfile.SYMTYPE),
                           ("run/hardlink", tarfile.LNKTYPE), ("run/device", tarfile.CHRTYPE)]:
            with self.subTest(name=name):
                extra = tarfile.TarInfo(name)
                extra.type = kind
                extra.linkname = "/tmp/outside"
                extra.size = 1 if extra.isfile() else 0
                self.rejected("Unsafe archive", extras=[(extra, b"x" if extra.isfile() else None)])

    def test_duplicate_archive_member_fails(self):
        member, data = self.members["run/inputs.json"]
        self.rejected("Duplicate archive", extras=[(member, data)])

    def test_archived_git_hooks_are_never_executed(self):
        sentinel = self.root / "executed"
        data = f"#!/bin/sh\ntouch '{sentinel}'\n".encode()
        member = tarfile.TarInfo("run/cases/01/.git/hooks/post-index-change")
        member.mode = 0o755
        member.size = len(data)
        result = self.execute(*self.rewritten(extras=[(member, data)]))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(sentinel.exists())

    def test_incomplete_or_failed_fresh_diagnostics_fail(self):
        copied = self.root / "fresh"
        copied.mkdir()
        for name in ("suite-identity.json", "inputs.json", "diagnostics.json", "diagnostics-complete.json"):
            shutil.copyfile(self.fresh_run / name, copied / name)
        diagnostics = json.loads((copied / "diagnostics.json").read_text())
        for mutation in (diagnostics[:-1], [dict(item, **({"pass": False} if index == 0 else {}))
                                          for index, item in enumerate(diagnostics)]):
            (copied / "diagnostics.json").write_text(json.dumps(mutation))
            result = self.execute(run=copied)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Automatic diagnostics", result.stderr)

    def test_fresh_input_edit_is_rejected(self):
        copied = self.root / "fresh"
        copied.mkdir()
        for name in ("suite-identity.json", "inputs.json", "diagnostics.json", "diagnostics-complete.json"):
            shutil.copyfile(self.fresh_run / name, copied / name)
        shutil.copytree(self.fresh_run / "cases/01", copied / "cases/01",
                        ignore=shutil.ignore_patterns("target", "*-target", ".code-review-graph"))
        source = copied / "cases/01/src/lib.rs"
        source.write_bytes(source.read_bytes() + b"\n// second dirty edit\n")
        result = self.execute(run=copied)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Reviewed inputs changed", result.stderr)

    def test_stale_fresh_workflow_is_rejected(self):
        copied = self.root / "fresh"
        copied.mkdir()
        suite = json.loads((self.fresh_run / "suite-identity.json").read_text())
        suite["fingerprint"] = "stale"
        (copied / "suite-identity.json").write_text(json.dumps(suite))
        result = self.execute(run=copied)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Suite identity", result.stderr)

    def test_symlink_in_kit_is_rejected_before_loading_code(self):
        spec = importlib.util.spec_from_file_location("evidence_gate", CHECKER)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        kit = self.root / "kit"
        kit.mkdir()
        (kit / "unreviewed-link").symlink_to("missing-target")
        with self.assertRaisesRegex(ValueError, "symlink"):
            gate.check(self.fresh_run, kit=kit)

    def test_reviews_require_distinct_native_sessions(self):
        provenance_path = "run/reviews/01/provenance.json"
        provenance = json.loads(self.members[provenance_path][1])
        second = json.loads(self.members["run/reviews/02/provenance.json"][1])
        transcript_path = "run/" + provenance["transcript"]
        records = self.native_records(transcript_path)
        [item for item in records if item.get("type") == "result"][-1]["session_id"] = second["session_id"]
        payload = json.dumps(records).encode()
        provenance.update(session_id=second["session_id"], transcript_sha256=hashlib.sha256(payload).hexdigest())
        self.rejected("Native session", changes={transcript_path: payload,
                      provenance_path: json.dumps(provenance).encode()})


if __name__ == "__main__":
    unittest.main()
