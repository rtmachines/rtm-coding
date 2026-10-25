#!/usr/bin/env python3
"""Opt-in native hook transport check, separate from fresh Rust reviews.

CLAUDE_NATIVE_TESTS=1 python3 tests/claude/test_native.py
Requires an already authenticated Claude CLI and uses its configured model/account.
Never logs in, changes trust, installs tools, or calls Cargo.
"""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import unittest


KIT = Path(__file__).resolve().parents[2]


def incomplete_report():
    spec = importlib.util.spec_from_file_location("native_hook_fixture", KIT / "tests/test-claude-hooks.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    return fixture.report("INCOMPLETE").replace(": PASS (fixture)", ": NOT RUN (native transport probe)").replace(
        "spec: PASS (fixture requirements)", "spec: NOT RUN (transport probe only)")


def native_evidence_errors(events, validate):
    """A successful CLI exit/hook-error notification alone is never sufficient."""
    errors = []
    rejected_initial = False
    feedback_after_rejection = False
    for event in events:
        if event.get("type") not in {"assistant", "user"}:
            continue
        if event.get("parent_tool_use_id") is not None:
            continue
        blocks = event.get("message", {}).get("content", [])
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if block.get("type") != "text":
                continue
            text = block.get("text", "")
            if event.get("type") == "assistant" and text.strip() == "DONE":
                rejected_initial = True
            if event.get("type") == "user" and rejected_initial and "Stop hook feedback:" in text:
                feedback_after_rejection = True
    if not rejected_initial:
        errors.append("The negative DONE candidate was not observed; rejection was not exercised")
    if not feedback_after_rejection:
        errors.append("The host did not send Stop rejection feedback after DONE")
    results = [item for item in events if item.get("type") == "result"
               and isinstance(item.get("result"), str) and item["result"].strip()]
    if not results:
        errors.append("No nonempty native result was recorded")
        return errors
    result = results[-1]
    if result.get("is_error") is not False or not result.get("session_id"):
        errors.append("The native result did not complete successfully with a session ID")
    final = result["result"].strip()
    if not final.startswith("## Verdict: INCOMPLETE\n"):
        errors.append("The final result is not the complete INCOMPLETE control report")
    if not validate(final):
        errors.append("The final result fails the current standalone report validator")
    return errors


def stop_hook_definition(agent_file):
    """Read the current template's single command Stop hook without PyYAML.

    Intentionally reject unsupported schema changes instead of silently testing a
    hard-coded hook different from the installed agent.
    """
    frontmatter = agent_file.read_text().split("---", 2)[1]
    match = re.search(r"^  Stop:\n((?:    .*\n|\n)+)", frontmatter, re.MULTILINE)
    if not match:
        raise ValueError("Agent Stop hook missing")
    lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    if lines[:2] != ["- hooks:", "- type: command"]:
        raise ValueError("Unexpected agent Stop hook structure")
    hook = {"type": "command"}
    for line in lines[2:]:
        key, separator, value = line.partition(": ")
        if not separator or key not in {"command", "args", "onFailure", "timeout"}:
            raise ValueError(f"Unsupported Stop hook field: {line}")
        if key in hook:
            raise ValueError(f"Duplicate Stop hook field: {key}")
        hook[key] = json.loads(value) if value.startswith(("[", '"')) or key == "timeout" else value
    if not {"type", "command", "args"} <= set(hook):
        raise ValueError("Incomplete Stop hook definition")
    return hook


class NativeEvidenceAssessment(unittest.TestCase):
    def test_successful_exit_with_ignored_hook_failure_is_rejected(self):
        events = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "DONE"}]}},
            {"type": "system", "subtype": "notification", "text": "Stop hook error occurred"},
            {"type": "system", "message": "Native runtime diagnostic"},
            {"type": "result", "is_error": False, "session_id": "synthetic", "result": "DONE"},
        ]
        self.assertTrue(native_evidence_errors(events, lambda text: False))

    def test_missing_native_events_are_not_a_pass(self):
        self.assertTrue(native_evidence_errors([], lambda text: True))

    def test_actual_rejection_and_valid_final_are_required(self):
        report = incomplete_report()
        events = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "DONE"}]}},
            {"type": "user", "message": {"content": [{"type": "text", "text": "Stop hook feedback: emit full report"}]}},
            {"type": "result", "is_error": False, "session_id": "synthetic", "result": report},
            {"type": "result", "is_error": False, "session_id": "synthetic", "result": ""},
        ]
        self.assertEqual(native_evidence_errors(events, lambda text: text == report.strip()), [])
        self.assertTrue(native_evidence_errors(events, lambda text: False))

    def test_native_authentication_or_api_error_is_not_success(self):
        events = [{"type": "result", "is_error": True, "session_id": "synthetic", "result": incomplete_report()}]
        self.assertTrue(native_evidence_errors(events, lambda text: True))


class NativeClaudeStop(unittest.TestCase):
    def test_stop_rejects_invalid_report_and_accepts_complete_incomplete(self):
        if os.environ.get("CLAUDE_NATIVE_TESTS") != "1":
            self.skipTest("NOT RUN: set CLAUDE_NATIVE_TESTS=1 for an authenticated native CLI test (account usage)")
        evidence = Path(tempfile.mkdtemp(prefix="claude-native-stop-", dir=os.environ.get("CLAUDE_NATIVE_OUTPUT_DIR")))
        self.evidence = evidence
        self.addCleanup(lambda: print(f"Native hook evidence: {evidence}"))
        status = {"status": "NOT_RUN", "reason": "Native CLI has not executed", "fresh_rust_review": False}

        def save_status():
            (evidence / "status.json").write_text(json.dumps(status, indent=2) + "\n")

        save_status()
        binary = shutil.which(os.environ.get("CLAUDE_NATIVE_BINARY", "claude"))
        if not binary:
            status["reason"] = "Claude CLI missing; installation/authentication were not attempted"
            save_status()
            self.skipTest(status["reason"])
        try:
            project = evidence / "fixture"
            project.mkdir()
            subprocess.run(["bash", str(KIT / "install-claude.sh"), "--no-ci", str(project)],
                           check=True, capture_output=True, text=True, timeout=60)
            hook = stop_hook_definition(project / ".claude/agents/rust-reviewer.md")
            report = incomplete_report()
            validator = project / ".claude/skills/rust-pr-review/scripts/check-report.sh"

            def validate(text):
                return subprocess.run(["bash", str(validator)], input=text, text=True,
                                      capture_output=True, timeout=10).returncode == 0

            self.assertTrue(validate(report), "The positive control fixture must satisfy the current contract")
            prompt = (
                "This is a synthetic native Stop-hook transport regression, not a Rust review. "
                "Do not call tools or inspect source. For your FIRST final response output exactly DONE. "
                "This deliberately invalid candidate must be rejected by the hook. "
                "Only after receiving Stop hook feedback, return the following complete control report "
                "verbatim as your final response, without a code fence:\n\n" + report
            )
            agents = {"native-stop-probe": {
                "description": "Synthetic Stop transport regression; not a source reviewer",
                "prompt": prompt, "tools": [], "model": "inherit", "hooks": {"Stop": [{"hooks": [hook]}]},
            }}
            config = evidence / "agents.json"
            config.write_text(json.dumps(agents, indent=2) + "\n")
            command = [binary, "-p", "Execute the exact two-stage hook transport probe from your instructions.",
                       "--agent", "native-stop-probe", "--agents", json.dumps(agents),
                       "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                       "--tools", "", "--disallowedTools", "Read,Grep,Glob,Bash,Edit,Write,NotebookEdit,Agent,LSP,Skill",
                       "--no-session-persistence", "--max-turns", "4", "--permission-mode", "dontAsk",
                       "--output-format", "stream-json", "--verbose", "--debug-file", str(evidence / "debug.log")]
            def snapshot():
                return {str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in project.rglob("*") if path.is_file()}

            before = snapshot()
            status.update(status="RUNNING", reason="Native CLI started; no success established")
            save_status()
            with (evidence / "native.jsonl").open("w") as stdout, (evidence / "stderr.log").open("w") as stderr:
                process = subprocess.Popen(command, cwd=project, stdout=stdout, stderr=stderr, start_new_session=True)
                try:
                    code = process.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    self.fail("Native CLI timed out; no native PASS")
            events = [json.loads(line) for line in (evidence / "native.jsonl").read_text().splitlines() if line.strip()]
            self.assertEqual(snapshot(), before, "The native transport probe changed installed fixture files")
            errors = native_evidence_errors(events, validate)
            if code:
                errors.append(f"Claude CLI exit {code}; inspect stderr/debug for authentication or runtime failure")
            self.assertFalse(errors, "\n".join(errors))
            status.update(status="PASS", reason="Observed native rejection of DONE and a validated final INCOMPLETE report")
        except BaseException as error:
            status.update(status="FAIL", reason=str(error))
            raise
        finally:
            save_status()


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    # Direct invocation must not become a green native check when it was skipped.
    raise SystemExit(2 if result.skipped else (0 if result.wasSuccessful() else 1))
