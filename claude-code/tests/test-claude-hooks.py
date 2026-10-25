#!/usr/bin/env python3
"""Native Claude hook contracts; synthetic Cargo output is not a Rust review."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]


def report(verdict='APPROVE'):
    return f'''## Verdict: {verdict}
Synthetic adapter fixture; not executed review evidence.
## Tooling
- rust-lsp: UNAVAILABLE (synthetic missing integration)
- lsp-used: NO (no semantic API)
- lsp-evidence: Discovery found no integration.
- lsp-limitations: Source inspection substituted; inference unverified.
## Gates
- fmt: PASS (fixture)
- clippy: PASS (fixture)
- tests: PASS (fixture)
- doctests: N/A (included in tests)
- deny: PASS (fixture)
## Memory safety
- memory-scope: NONE (safe code)
- miri: N/A (safe code)
- aliasing: N/A (safe code)
- memory-evidence: N/A (safe code)
- aliasing-evidence: N/A (safe code)
## Concurrency
- async-scope: NONE (synchronous code)
- deadlocks: N/A (no locks)
- cancellation: N/A (no future)
- task-lifecycle: N/A (no task)
- async-evidence: N/A (synchronous code)
- sync-scope: NONE (no protocol)
- loom: N/A (no protocol)
- synchronization: N/A (no protocol)
- model-evidence: N/A (no protocol)
## Spec
- spec: PASS (fixture requirements)
- missing: none
- unrequested: none
- contradictions: none
## Findings
No findings.
## Residual risks
Synthetic fixture, not proof of actual checks.
'''


class Hooks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo with spaces'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.repo / 'Cargo.toml').write_text('[workspace]\nmembers=[]\n')
        (self.repo / 'deny.toml').write_text('[licenses]\nallow=["MIT"]\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.git('branch', 'baseline')
        self.scripts = self.repo / '.claude/skills/rust-pr-review/scripts'
        # Use the installed Claude payload; no synthetic substitute validator.
        shutil.copytree(KIT / 'template/.claude/skills/rust-pr-review/scripts', self.scripts)
        self.bin = self.root / 'bin'; self.bin.mkdir()
        cargo = self.bin / 'cargo'
        cargo.write_text('''#!/bin/bash
printf '%s\\n' "$*" >> "$CARGO_CALLS"
case "$*" in
  "nextest --version") exit 1;;
  "deny --version") exit "${DENY_MISSING:-0}";;
  "clippy "*) exit "${CLIPPY_EXIT:-0}";;
esac
exit 0
''')
        cargo.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ['PATH'],
                        CLAUDE_PROJECT_DIR=str(self.repo), TMPDIR=str(self.root),
                        CARGO_CALLS=str(self.root/'cargo-calls'), RUST_GATE_BASE='baseline')
        for key in ['RUST_GATE_SKIP', 'RUST_GATE_FEATURES', 'RUST_REVIEWDOG']:
            self.env.pop(key, None)

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, check=True, capture_output=True, text=True)

    def hook(self, name, payload=None, mode=None, raw=None, env=None):
        command=['bash', str(KIT/'template/.claude/hooks'/name)]
        if mode: command.append(mode)
        return subprocess.run(command, input=raw if raw is not None else json.dumps(payload or {}),
                              text=True, capture_output=True, cwd=self.repo, env=env or self.env, timeout=10)

    def review(self, text, **extra):
        return self.hook('check-review-report.sh', dict(session_id='fixture', hook_event_name='SubagentStop', agent_type='rust-reviewer', last_assistant_message=text, **extra))

    def assertReportAccepted(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '', result.stdout)

    def assertReportBlocked(self, result, handback=False):
        self.assertEqual(result.returncode, 0, result.stderr)
        output=json.loads(result.stdout)
        if handback:
            self.assertEqual(output['hookSpecificOutput']['hookEventName'], 'PreToolUse')
            self.assertEqual(output['hookSpecificOutput']['permissionDecision'], 'deny')
        else:
            self.assertEqual(output['decision'], 'block')
            self.assertTrue(output['reason'].strip())

    def broken_jq(self, formatting_only=False):
        actual=shutil.which('jq')
        self.assertIsNotNone(actual)
        stub=self.bin/'jq'
        if formatting_only:
            stub.write_text('#!/usr/bin/env python3\nimport os,sys\n'
                            'if "-n" in sys.argv[1:]:\n'
                            '    print("partial invalid JSON")\n'
                            '    sys.exit(127)\n'
                            f'os.execv({actual!r}, [{actual!r}, *sys.argv[1:]])\n')
        else:
            stub.write_text('#!/bin/sh\nexit 127\n')
        stub.chmod(0o755)

    def test_missing_jq_still_emits_explicit_block_for_all_review_hooks(self):
        self.broken_jq()
        for mode in ['stop','handback']:
            with self.subTest(mode=mode):
                self.assertReportBlocked(self.hook('check-review-report.sh', raw='{}', mode=mode), handback=mode=='handback')
        with self.subTest(mode='Bash'):
            result, decision=self.guard('', raw='{}')
            self.assertEqual(result.returncode,0)
            self.assertEqual(decision,'deny')

    def test_formatter_failure_after_parsing_still_emits_clean_block_json(self):
        self.broken_jq(formatting_only=True)
        with self.subTest(mode='stop'):
            self.assertReportBlocked(self.review('## Verdict: APPROVE'))
        with self.subTest(mode='handback'):
            payload={'tool_name':'SubagentHandback','tool_input':{'message':'## Verdict: APPROVE'}}
            self.assertReportBlocked(self.hook('check-review-report.sh',payload,'handback'),handback=True)
        with self.subTest(mode='Bash'):
            result, decision=self.guard('git commit -m x')
            self.assertEqual(result.returncode,0)
            self.assertEqual(decision,'deny')

    def test_report_missing_and_malformed_fail_closed(self):
        for raw in ['{}', '{', '{"last_assistant_message":null}', '{"last_assistant_message":42}',
                    '{"last_assistant_message":"  "}', '[]']:
            with self.subTest(raw=raw):
                self.assertReportBlocked(self.hook('check-review-report.sh', raw=raw))

    def test_valid_report_passes(self):
        self.assertReportAccepted(self.review(report()))

    def test_handback_validates_report_before_delivery(self):
        payload={'hook_event_name':'PreToolUse', 'tool_name':'SubagentHandback',
                 'tool_input':{'message':report()}}
        self.assertReportAccepted(self.hook('check-review-report.sh', payload, 'handback'))
        payload['tool_input']['message']='## Verdict: APPROVE'
        self.assertReportBlocked(self.hook('check-review-report.sh', payload, 'handback'), handback=True)
        payload['last_assistant_message']=report()
        self.assertReportBlocked(self.hook('check-review-report.sh', payload, 'handback'), handback=True)

    def test_handback_missing_report_does_not_pass(self):
        for message in [None, 7, '', '  ']:
            payload={'tool_name':'SubagentHandback', 'tool_input':{'message':message}}
            self.assertReportBlocked(self.hook('check-review-report.sh', payload, 'handback'), handback=True)

    def transcript(self, text=None, result_id='handback-1', is_error=False, after=None):
        records=[{'type':'assistant','message':{'role':'assistant','content':[
            {'type':'tool_use', 'id':'handback-1','name':'SubagentHandback',
             'input':{'message':report() if text is None else text}}]}},
            {'type':'user','message':{'role':'user','content':[
                {'type':'tool_result','tool_use_id':result_id,'is_error':is_error,'content':'Delivered'}]}}]
        records.extend(after or [])
        path=self.root/'agent-transcript.jsonl'
        path.write_text(''.join(json.dumps(row)+'\n' for row in records))
        return path

    def test_stop_accepts_last_successful_handback_from_native_transcript(self):
        path=self.transcript(after=[{'type':'assistant','message':{'role':'assistant',
            'content':[{'type':'text','text':'Review delivered.'}]}}])
        for field in ['agent_transcript_path','transcript_path']:
            with self.subTest(field=field):
                for closing in ['', 'Review delivered.']:
                    self.assertReportAccepted(self.review(closing, **{field:str(path)}))

    def test_stop_supports_observed_native_handback_result_shape(self):
        path=self.transcript()
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        result=rows[-1]['message']['content'][0]
        result.pop('is_error')
        result['content']=[{'type':'text','text':'{"success":true,"message":"Report delivered to your caller."}'}]
        path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        self.assertReportAccepted(self.review('Review delivered.', agent_transcript_path=str(path)))

    def test_stop_transcript_missing_malformed_or_unpaired_fails(self):
        path=self.root/'transcript.jsonl'
        self.assertReportBlocked(self.review('', agent_transcript_path=str(path)))
        for raw in ['{', '[]\n', json.dumps({'type':'assistant','message':{'content':[
                    {'type':'tool_use','id':'h','name':'SubagentHandback','input':{'message':report()}}]}})+'\n']:
            path.write_text(raw)
            self.assertReportBlocked(self.review('', agent_transcript_path=str(path)))
        for kwargs in [{'result_id':'wrong-id'}, {'is_error':True}, {'text':'## Verdict: APPROVE'}]:
            path=self.transcript(**kwargs)
            for attempt in range(3):
                self.assertReportBlocked(self.review('', agent_transcript_path=str(path), stop_hook_active=attempt>0))

    def test_stop_rejects_handback_followed_by_other_tool_or_new_request(self):
        later_tools=[{'type':'assistant','message':{'role':'assistant','content':[
            {'type':'tool_use','id':'bash-2','name':'Bash','input':{'command':'cargo test'}}]}}]
        later_request=[{'type':'user','message':{'role':'user','content':'Review another change now.'}}]
        for after in [later_tools, later_request]:
            path=self.transcript(after=after)
            self.assertReportBlocked(self.review('', agent_transcript_path=str(path)))

    def test_invalid_final_report_cannot_borrow_earlier_valid_handback(self):
        path=self.transcript()
        self.assertReportBlocked(self.review('## Verdict: APPROVE', agent_transcript_path=str(path)))
        self.assertReportBlocked(self.review(42, agent_transcript_path=str(path)))

    def test_transcript_parsing_is_bounded_and_rejects_fifo(self):
        large=self.root/'large.jsonl'
        with large.open('wb') as stream:
            stream.truncate(33*1024*1024)
        self.assertReportBlocked(self.review('', agent_transcript_path=str(large)))
        fifo=self.root/'pipe.jsonl'; os.mkfifo(fifo)
        self.assertReportBlocked(self.review('', agent_transcript_path=str(fifo)))

    def test_repeated_invalid_report_never_becomes_success(self):
        for attempt in range(5):
            self.assertReportBlocked(self.review('## Verdict: APPROVE', stop_hook_active=attempt > 0))

    def test_missing_validator_does_not_pass(self):
        (self.scripts/'check-report.sh').unlink()
        self.assertReportBlocked(self.review(report()))

    def test_unrun_gate_blocks_approval_but_allows_incomplete(self):
        text=report().replace('clippy: PASS', 'clippy: NOT RUN')
        self.assertReportBlocked(self.review(text))
        self.assertReportAccepted(self.review(text.replace('Verdict: APPROVE', 'Verdict: INCOMPLETE')))

    def test_safety_gap_requires_escalation(self):
        text=report().replace('memory-scope: NONE (safe code)', 'memory-scope: REQUIRED (FFI)')
        text=text.replace('miri: N/A (safe code)', 'miri: NOT RUN (missing targeted probe)')
        text=text.replace('aliasing: N/A (safe code)', 'aliasing: UNRESOLVED (vendor contract absent)')
        text=text.replace('memory-evidence: N/A (safe code)', 'memory-evidence: Missing target probe')
        text=text.replace('aliasing-evidence: N/A (safe code)', 'aliasing-evidence: Missing vendor guarantee')
        self.assertReportBlocked(self.review(text))
        self.assertReportAccepted(self.review(text.replace('Verdict: APPROVE', 'Verdict: ESCALATE')))

    def test_incomplete_loom_never_approves(self):
        text=report().replace('sync-scope: NONE (no protocol)', 'sync-scope: REQUIRED (publication)')
        text=text.replace('loom: N/A (no protocol)', 'loom: NOT RUN (one-permutation cap)')
        text=text.replace('synchronization: N/A (no protocol)', 'synchronization: PASS (ordering argument)')
        text=text.replace('model-evidence: N/A (no protocol)', 'model-evidence: Exploration stopped at configured cap')
        self.assertReportBlocked(self.review(text))
        self.assertReportAccepted(self.review(text.replace('Verdict: APPROVE', 'Verdict: ESCALATE')))

    def test_missing_cancellation_contract_requires_escalation(self):
        text=report().replace('async-scope: NONE (synchronous code)', 'async-scope: REQUIRED (async provider)')
        text=text.replace('deadlocks: N/A (no locks)', 'deadlocks: PASS (bounded forced interleaving)')
        text=text.replace('cancellation: N/A (no future)', 'cancellation: NOT RUN (provider contract missing)')
        text=text.replace('task-lifecycle: N/A (no task)', 'task-lifecycle: PASS (abort and join checked)')
        text=text.replace('async-evidence: N/A (synchronous code)', 'async-evidence: Missing provider cancellation contract')
        self.assertReportBlocked(self.review(text))
        self.assertReportAccepted(self.review(text.replace('Verdict: APPROVE', 'Verdict: ESCALATE')))

    def commit(self, command='git commit -m update', **env):
        return self.hook('rust-gate.sh', {'hook_event_name':'PreToolUse','tool_name':'Bash','tool_input':{'command':command}}, 'commit', env=dict(self.env, **env))

    def test_commit_does_not_reuse_success_for_new_configuration(self):
        self.assertEqual(self.commit().returncode, 0)
        self.assertEqual(self.commit(CLIPPY_EXIT='101').returncode, 2)

    def test_legacy_skip_variable_cannot_bypass_failed_commit(self):
        self.assertEqual(self.commit(CLIPPY_EXIT='101', RUST_GATE_SKIP='1').returncode, 2)

    def test_missing_gate_runner_blocks_commit(self):
        (self.scripts/'gates.sh').unlink()
        self.assertEqual(self.commit().returncode, 2)

    def test_missing_deny_cannot_pass(self):
        self.assertEqual(self.commit(DENY_MISSING='1').returncode, 2)
        (self.repo/'deny.toml').unlink()
        self.assertEqual(self.commit().returncode, 2)

    def test_commit_gate_ignores_unrelated_bash(self):
        for cmd in ['git status', 'echo "git commit -m hi"', 'git show --format=commit HEAD']:
            self.assertEqual(self.commit(cmd, CLIPPY_EXIT='101').returncode, 0)
        self.assertFalse((self.root/'cargo-calls').exists())

    def test_alternate_git_root_is_not_validated_as_current_tree(self):
        for cmd in ['git -C /elsewhere commit -m x', 'git --git-dir=/elsewhere/.git commit -m x']:
            self.assertEqual(self.commit(cmd).returncode, 2)
        self.assertFalse((self.root/'cargo-calls').exists())

    def test_compound_prefixed_or_option_commits_require_standalone_command(self):
        for cmd in ['RUSTFLAGS=-Dwarnings git commit -m x', 'env RUSTFLAGS=-Dwarnings git commit -m x',
                    'cargo test && git commit -m x', 'cargo test; git commit -m x',
                    'cargo test\ngit commit -m x', 'git --no-pager commit -m x',
                    'git commit -m x && cd /elsewhere && git commit -m y']:
            with self.subTest(cmd=cmd):
                self.assertEqual(self.commit(cmd, CLIPPY_EXIT='101').returncode, 2)
        self.assertFalse((self.root/'cargo-calls').exists())

    def test_changed_bash_directory_is_not_validated_as_current_tree(self):
        other=self.root/'other'; other.mkdir()
        subprocess.run(['git', 'init', '-q', str(other)], check=True)
        payload={'hook_event_name':'PreToolUse', 'cwd':str(other), 'tool_input':{'command':'git commit -m x'}}
        self.assertEqual(self.hook('rust-gate.sh', payload, 'commit').returncode, 2)
        self.assertFalse((self.root/'cargo-calls').exists())

    def test_report_stop_does_not_run_cargo_or_force_source_fixes(self):
        text=report('REQUEST_CHANGES').replace('clippy: PASS', 'clippy: FAIL')
        result=self.hook('rust-gate.sh', {'hook_event_name':'Stop','last_assistant_message':text}, 'stop', env=dict(self.env, CLIPPY_EXIT='101'))
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.root/'cargo-calls').exists())

    def test_nonreview_stop_does_not_run_cargo(self):
        (self.repo/'src').mkdir();(self.repo/'src/lib.rs').write_text('// changed\n')
        result=self.hook('rust-gate.sh', {'hook_event_name':'Stop','last_assistant_message':'Progress update.'}, 'stop')
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.root/'cargo-calls').exists())

    def guard(self, command, raw=None, cwd=None):
        payload={'tool_name':'Bash','tool_input':{'command':command}}
        if cwd is not None:
            payload['cwd']=str(cwd)
        result=self.hook('reviewer-bash-guard.sh', payload, raw=raw)
        data=json.loads(result.stdout) if result.stdout.strip() else {}
        return result, data.get('hookSpecificOutput',{}).get('permissionDecision')

    def test_guard_never_autoapproves_diagnostic_programs(self):
        for cmd in ['cargo test --offline --locked', 'cargo +nightly miri test --offline',
                    'cargo deny --locked --offline check', 'bash .claude/skills/rust-pr-review/scripts/gates.sh']:
            with self.subTest(cmd=cmd):
                result, decision=self.guard(cmd)
                self.assertEqual(result.returncode,0)
                self.assertIsNone(decision)

    def test_guard_preserves_normal_permissions_for_isolated_probes(self):
        for cmd in ['python /tmp/review/probe.py', 'cargo test > /tmp/review/log.txt',
                    'cargo test --offline 2>&1', 'CARGO_NET_OFFLINE=true cargo test',
                    'mkdir -p /tmp/review', 'cp src/lib.rs /tmp/review/lib.rs',
                    'bash /tmp/review/run-probe.sh', 'cargo test\ngit push']:
            with self.subTest(cmd=cmd):
                result, decision=self.guard(cmd)
                self.assertEqual(result.returncode,0)
                self.assertIsNone(decision)

    def test_guard_preserves_native_probe_logs_and_heredoc_authorisation(self):
        examples=[
            'cd /tmp/review/exact && export CARGO_NET_OFFLINE=true; L=../logs\ncargo test > $L/test.log 2>&1',
            'mkdir -p /tmp/review/logs && cd /tmp/review && sha256sum Cargo.toml > source.sha256; cat source.sha256',
            "cat > /tmp/review/probe/x.rs <<'EOF'\nfn a() -> u8 { 1 }\nEOF\necho $?",
            "python3 - <<'PY'\nprint('fn a() -> u8 { 1 }')\nPY",
            "python3 -c \"print('git commit; fn a() -> u8')\"",
            "sed -i 's/use old/use new/' /tmp/review/probe/src/lib.rs",
        ]
        for command in examples:
            with self.subTest(command=command):
                result, decision=self.guard(command)
                self.assertEqual(result.returncode,0)
                self.assertIsNone(decision)

    def test_guard_resolves_simple_relative_destinations_using_native_cwd(self):
        scratch=self.root/'isolated-probe';scratch.mkdir()
        for command in ['cargo test > logs.txt', 'sed -i s/a/b/ src/lib.rs', 'mkdir -p src', 'cargo fmt']:
            with self.subTest(command=command):
                result, decision=self.guard(command,cwd=scratch)
                self.assertEqual(result.returncode,0)
                self.assertIsNone(decision)
        source_dir=self.repo/'src';source_dir.mkdir()
        self.assertEqual(self.guard('echo change > lib.rs',cwd=source_dir)[1],'deny')

    def test_guard_denies_explicit_mutation(self):
        for cmd in ['git commit -m x', 'git checkout main', 'cargo fmt', 'cargo clippy --fix',
                    'cargo install x', 'git diff --output=src/lib.rs', 'echo change > src/lib.rs',
                    'sed -i s/a/b/ src/lib.rs',
                    'rm src/lib.rs', 'cp /tmp/fixed.rs src/lib.rs', 'mkdir src/generated']:
            self.assertEqual(self.guard(cmd)[1], 'deny', cmd)

    def test_guard_malformed_payload_denied(self):
        for raw in ['{}','{','{"tool_input":{"command":7}}']:
            self.assertEqual(self.guard('', raw)[1], 'deny')

    def test_router_does_not_automatically_delegate_escalations(self):
        result=self.hook('review-router.sh', {'prompt':'Review this Rust diff'})
        self.assertEqual(result.returncode, 0)
        context=json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
        self.assertIn('rust-pr-review', context)
        self.assertNotIn('run /rust-review:rust-review', context)


if __name__=='__main__':
    unittest.main()
