#!/usr/bin/env python3
"""Run the shared Rust oracles and assess separately recorded native Claude reviews.

prepare creates 11 review requests but never invokes or impersonates a model.
After each actual Claude CLI run, use record with its native JSON/JSONL transcript.
Synthetic report-contract checks are provided separately by tests/test-claude.sh.
"""
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_runner", KIT / "tests/run-workflow-regressions.py")
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)
from support import digest, suite_identity


def read_json(path):
    return json.loads(path.read_text())


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_suite(root):
    recorded = read_json(root / "suite-identity.json")
    current = suite_identity(KIT, "claude")
    if recorded != current:
        raise ValueError("Claude suite identity is absent or stale; prepare a new run with the current kit")
    return recorded


def native_result(transcript, report):
    text = transcript.read_text()
    if not text.strip():
        raise ValueError("Native Claude transcript is empty")
    try:
        parsed = json.loads(text)
        records = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    results = [entry for entry in records if isinstance(entry, dict) and entry.get("type") == "result"]
    if not results or not results[-1].get("session_id") or results[-1].get("is_error") is not False:
        raise ValueError("Transcript lacks a successful native Claude result with a session_id")
    result = results[-1].get("result")
    if not isinstance(result, str) or result.strip() != report.read_text().strip():
        raise ValueError("Native Claude result does not match the saved review report")
    return results[-1]


def review_binding(root, case):
    suite = check_suite(root)
    inputs = read_json(root / "inputs.json")
    if case not in inputs:
        raise ValueError(f"Unknown review case: {case}")
    if workflow.snapshot(root / "cases" / case, runtime="claude") != inputs[case]:
        raise ValueError(f"Reviewed source changed for case {case}")
    report = root / "reviews" / case / "report.md"
    if not report.read_text().strip():
        raise ValueError("Review report is empty")
    return {
        "schema": 1,
        "runtime": "claude",
        "case": case,
        "suite": suite["fingerprint"],
        "input": digest(inputs[case]),
        "report_sha256": file_hash(report),
    }


def record_review(root, case, transcript):
    transcript = (root / transcript).resolve()
    if not transcript.is_relative_to(root) or not transcript.is_file():
        raise ValueError("Transcript must be a file within this run directory")
    result = native_result(transcript, root / "reviews" / case / "report.md")
    binding = review_binding(root, case)
    binding.update(
        transcript=str(transcript.relative_to(root)),
        transcript_sha256=file_hash(transcript),
        session_id=result["session_id"],
    )
    destination = root / "reviews" / case / "provenance.json"
    if destination.exists():
        raise ValueError("Review provenance already exists; preserve this run and prepare a new one")
    destination.write_text(json.dumps(binding, indent=2) + "\n")
    print(f"Recorded native Claude evidence for case {case}; semantic assessment is still required")


def review_errors(root, case):
    try:
        expected = review_binding(root, case)
        actual = read_json(root / "reviews" / case / "provenance.json")
        if any(actual.get(key) != value for key, value in expected.items()):
            return ["Claude provenance does not match the runtime, suite, source, or report"]
        transcript = (root / actual["transcript"]).resolve()
        if not transcript.is_relative_to(root) or not transcript.is_file():
            return ["Native Claude transcript is missing or outside this run"]
        if file_hash(transcript) != actual["transcript_sha256"]:
            return ["Native Claude transcript hash changed"]
        if native_result(transcript, root / "reviews" / case / "report.md")["session_id"] != actual["session_id"]:
            return ["Native Claude session differs from recorded provenance"]
        return []
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [str(error)]


def preserve_diagnostics(root, rerun):
    if not (root / "diagnostics.json").exists():
        return
    if not rerun:
        raise ValueError("Diagnostics already exist; use --rerun to preserve and repeat them")
    attempts = root / "attempts"
    attempts.mkdir(exist_ok=True)
    previous = attempts / str(len(list(attempts.iterdir())) + 1)
    previous.mkdir()
    for name in ["diagnostics.json", "diagnostics-complete.json", "logs", "probes"]:
        if (root / name).exists():
            shutil.move(root / name, previous / name)
    (root / "logs").mkdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--phase", choices=["all", "prepare", "diagnostics", "record", "assess"], default="all")
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument("--case", choices=[case["id"] for case in workflow.CATALOG])
    parser.add_argument("--transcript", type=Path, help="Native Claude CLI JSON or JSONL, relative to the run directory")
    args = parser.parse_args()
    root = args.directory.resolve()
    try:
        if args.phase in ("all", "prepare"):
            workflow.prepare(root, runtime="claude")
        else:
            check_suite(root)
        if args.phase == "record":
            if not args.case or not args.transcript:
                parser.error("record requires --case and --transcript")
            record_review(root, args.case, args.transcript)
        if args.phase in ("all", "diagnostics"):
            preserve_diagnostics(root, args.rerun)
            passed = workflow.diagnostics(root, runtime="claude")
            if args.phase == "diagnostics":
                return 0 if passed else 1
        if args.phase in ("all", "assess"):
            return workflow.assess(root, runtime="claude", review_guard=review_errors)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Claude regression run failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
