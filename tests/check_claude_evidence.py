"""Bind archived native Claude evidence to a newly completed automatic run.

Archive contents are data only: no extraction, archived scripts, or archived Git
commands. Only the checked-out report validator and fresh-run Git are executed.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "claude-code"
DEFAULT_ARCHIVE = KIT / "docs/verification/2026-10-25-claude-parity/claude-review-evidence.tar.gz"


def unique_object(pairs):
    """Reject ambiguous duplicate JSON keys in evidence and manifests."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(data):
    return json.loads(data, object_pairs_hook=unique_object)


def read_json(path):
    return parse_json(path.read_bytes())


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def relative_path(name):
    """Accept one unambiguous relative POSIX path, without normalization."""
    if (not isinstance(name, str) or not name or "\\" in name or "\0" in name
            or any(part in ("", ".", "..") for part in name.split("/"))
            or PurePosixPath(name).is_absolute()):
        raise ValueError(f"Unsafe archive path: {name!r}")
    return name


class ArchiveData:
    """Read regular archive members without materializing files or Git metadata."""

    def __init__(self, archive):
        self.archive = archive
        self.members = {}
        for member in archive:
            name = member.name[:-1] if member.isdir() and member.name.endswith("/") else member.name
            relative_path(name)
            if not (name == "run" or name.startswith("run/")) or not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsafe archive member: {name}")
            if name in self.members:
                raise ValueError(f"Duplicate archive member: {name}")
            self.members[name] = member
        for name in self.members:
            for ancestor in PurePosixPath(name).parents:
                parent = self.members.get(str(ancestor))
                if parent is not None and not parent.isdir():
                    raise ValueError(f"Unsafe archive non-directory ancestor: {name}")

    def read(self, relative, category="Evidence"):
        name = "run/" + relative_path(relative)
        member = self.members.get(name)
        if member is None or not member.isfile():
            raise ValueError(f"{category} missing regular file: {relative}")
        with self.archive.extractfile(member) as stream:
            return stream.read()

    def json(self, relative, category="Evidence"):
        return parse_json(self.read(relative, category))


def validate_diagnostics(records, marker):
    """A complete fresh run must contain all 49 distinct successful controls."""
    if (not isinstance(records, list) or len(records) != 49
            or marker.get("completed") is not True or marker.get("checks") != 49
            or any(not isinstance(item, dict) or item.get("pass") is not True
                   or not isinstance(item.get("name"), str) or not item["name"] for item in records)
            or len({item["name"] for item in records}) != 49):
        raise ValueError("Automatic diagnostics require 49 distinct completed PASS controls")


def trusted_support(kit):
    for path in kit.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Suite identity cannot include symlink: {path.relative_to(kit)}")
    spec = importlib.util.spec_from_file_location("claude_publication_support", kit / "tests/workflow/ci/support.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fresh_snapshot(repo, support):
    """Run Git only in trusted, newly prepared CI cases, never inside evidence."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                              text=True, timeout=30).stdout

    return {"files": support.git_input_files(repo), "status": git("status", "--porcelain"),
            "head": git("rev-parse", "HEAD").strip()}


def validate_native(data, provenance, report):
    if sha256(data) != provenance.get("transcript_sha256"):
        raise ValueError("Native transcript hash differs from provenance")
    text = data.decode("utf-8")
    try:
        parsed = parse_json(text)
        records = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        records = [parse_json(line) for line in text.splitlines() if line.strip()]
    results = [item for item in records if isinstance(item, dict) and item.get("type") == "result"]
    if (not results or results[-1].get("is_error") is not False
            or not isinstance(results[-1].get("session_id"), str) or not results[-1]["session_id"]
            or results[-1]["session_id"] != provenance.get("session_id")
            or not isinstance(results[-1].get("result"), str)
            or results[-1]["result"].strip() != report.strip()):
        raise ValueError("Native result must be successful and match the report and recorded session")


def check(run: Path, archive: Path = DEFAULT_ARCHIVE, manifest: Path | None = None,
          kit: Path = KIT) -> None:
    """Accept only complete native evidence bound to this kit and fresh run."""
    manifest = manifest or archive.with_name("archive-manifest.json")
    support = trusted_support(kit)
    current = support.suite_identity(kit, "claude")
    if read_json(run / "suite-identity.json") != current:
        raise ValueError("Suite identity of fresh automatic run differs from current Claude kit")
    diagnostics = read_json(run / "diagnostics.json")
    validate_diagnostics(diagnostics, read_json(run / "diagnostics-complete.json"))
    inputs = read_json(run / "inputs.json")
    catalog = read_json(kit / "tests/workflow/cases.json")
    cases = {item["id"]: item for item in catalog}
    if len(cases) != 11 or set(inputs) != set(cases):
        raise ValueError("Case IDs in automatic inputs must match the 11 reviewed cases")
    metadata = read_json(manifest)
    with archive.open("rb") as stream:
        archive_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    if (metadata.get("sha256") != archive_hash or metadata.get("bytes") != archive.stat().st_size
            or metadata.get("archive") != archive.name or metadata.get("suite") != current["fingerprint"]):
        raise ValueError("Archive integrity or suite differs from its manifest")
    with tarfile.open(archive) as tar:
        evidence = ArchiveData(tar)
        if evidence.json("suite-identity.json") != current:
            raise ValueError("Suite identity of native evidence differs from current Claude kit")
        if evidence.json("inputs.json") != inputs:
            raise ValueError("Reviewed inputs differ from newly prepared automatic inputs")
        historical = evidence.json("diagnostics.json")
        validate_diagnostics(historical, evidence.json("diagnostics-complete.json"))
        if {item["name"] for item in historical} != {item["name"] for item in diagnostics}:
            raise ValueError("Automatic diagnostics names differ from the reviewed suite")
        for section in ("cases", "reviews"):
            actual = {name.split("/")[2] for name in evidence.members
                      if name.startswith(f"run/{section}/")}
            if actual != set(cases):
                raise ValueError(f"Case IDs in archived {section} differ from the catalog")
        reports = {name for name, member in evidence.members.items()
                   if member.isfile() and name.startswith("run/reviews/") and name.endswith("/report.md")}
        if reports != {f"run/reviews/{case}/report.md" for case in cases}:
            raise ValueError("Reports must contain exactly one report for each reviewed case")
        audit = evidence.json("semantic-assessment.json", "Semantic assessment")
        if not isinstance(audit, dict) or set(audit) != set(cases):
            raise ValueError("Semantic assessment must cover exactly the 11 reviewed cases")
        sessions = set()
        with tempfile.TemporaryDirectory(prefix="claude-evidence-reports-") as temporary:
            for case, item in cases.items():
                if fresh_snapshot(run / "cases" / case, support) != inputs[case]:
                    raise ValueError(f"Reviewed inputs changed in fresh case {case}")
                for path, expected in inputs[case]["files"].items():
                    relative = f"cases/{case}/{relative_path(path)}"
                    data = evidence.read(relative, "Archived source")
                    member = evidence.members["run/" + relative]
                    if (expected.get("type") != "file" or sha256(data) != expected.get("sha256")
                            or stat.S_IMODE(member.mode) != expected.get("mode")):
                        raise ValueError(f"Archived source bytes or mode differ: {relative}")
                report_bytes = evidence.read(f"reviews/{case}/report.md", "Reports")
                report = report_bytes.decode("utf-8")
                provenance = evidence.json(f"reviews/{case}/provenance.json", "Report provenance")
                expected = {"schema": 1, "runtime": "claude", "case": case,
                            "suite": current["fingerprint"], "input": support.digest(inputs[case]),
                            "report_sha256": sha256(report_bytes)}
                if any(provenance.get(key) != value for key, value in expected.items()):
                    raise ValueError(f"Report provenance differs for case {case}")
                transcript = provenance.get("transcript")
                if not relative_path(transcript).startswith(f"reviews/{case}/"):
                    raise ValueError(f"Native transcript is outside case {case}")
                validate_native(evidence.read(transcript, "Native transcript"), provenance, report)
                if provenance["session_id"] in sessions:
                    raise ValueError("Native session IDs must be distinct for the 11 independent reviews")
                sessions.add(provenance["session_id"])
                report_path = Path(temporary) / f"{case}.md"
                report_path.write_bytes(report_bytes)
                validator = kit / "template/.claude/skills/rust-pr-review/scripts/check-report.sh"
                validation = subprocess.run(["bash", str(validator), str(report_path)], cwd=kit,
                                            capture_output=True, text=True, timeout=30, check=False)
                verdict = re.findall(r"^## Verdict: (\w+)$", report, re.MULTILINE)
                if validation.returncode or len(verdict) != 1 or verdict[0] not in item["verdicts"]:
                    raise ValueError(f"Report contract or expected verdict failed for case {case}: "
                                     + validation.stderr.strip())
                assessment = audit[case]
                if (not isinstance(assessment, dict) or assessment.get("pass") is not True
                        or not isinstance(assessment.get("reason"), str) or not assessment["reason"].strip()
                        or not isinstance(assessment.get("evidence"), list) or not assessment["evidence"]):
                    raise ValueError(f"Semantic assessment is incomplete or failed for case {case}")
                for path in assessment["evidence"]:
                    evidence.read(path, "Semantic evidence")
    print("PASS: 49/49 fresh automatic controls; 11/11 native Claude reviews and semantic assessments")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="Freshly prepared and completed automatic Claude run")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        check(args.run.resolve(), args.archive.resolve(), args.manifest)
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError, tarfile.TarError,
            subprocess.SubprocessError) as error:
        print(f"Claude evidence gate FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
