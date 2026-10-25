#!/usr/bin/env python3
"""Exercise CI's missing, partial, stale and complete evidence paths."""
import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import manage
from support import binding, diagnostics_complete, suite_identity

spec=importlib.util.spec_from_file_location('regression_runner',manage.RUNNER)
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

REPORT='''## Verdict: APPROVE
## Tooling
- rust-lsp: AVAILABLE (synthetic fixture)
- lsp-used: YES (synthetic semantic query)
- lsp-evidence: Test fixture query returned the expected definition; no live MCP claim.
- lsp-limitations: NONE within this synthetic validator fixture.
## Gates
- fmt: PASS
- clippy: PASS
- tests: PASS
- doctests: PASS
- deny: PASS
## Memory safety
- memory-scope: NONE
- miri: N/A
- aliasing: N/A
- memory-evidence: N/A
- aliasing-evidence: N/A
## Concurrency
- async-scope: NONE
- deadlocks: N/A no locks
- cancellation: N/A no futures
- task-lifecycle: N/A no tasks
- async-evidence: N/A
- sync-scope: NONE
- loom: N/A
- synchronization: N/A
- model-evidence: N/A
## Spec
- spec: PASS
- missing: none
- unrequested: none
- contradictions: none
## Findings
No findings.
## Residual risks
Test fixture for the acceptance mechanism, not an actual code review.
'''

class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)/'run';self.root.mkdir()
        for name in ['reviews','logs']: (self.root/name).mkdir()
        self.write('suite-identity.json',{'schema':1,'fingerprint':'current','files':{}})
        self.write('inputs.json',{'01':{'source':'unchanged'}})
        self.write('diagnostics.json',[{'name':'actual-test','pass':True}])
        self.write('diagnostics-complete.json',{'completed':True,'checks':1})
        self.catalog=patch.object(runner,'CATALOG',[{'id':'01','name':'Example','verdicts':['APPROVE']}]);self.catalog.start()
        self.snapshot=patch.object(runner,'snapshot',return_value={'source':'unchanged'});self.snapshot.start()
    def tearDown(self):
        self.catalog.stop();self.snapshot.stop();self.tmp.cleanup()
    def write(self,name,value):
        (self.root/name).write_text(json.dumps(value))
    def assess(self):
        with contextlib.redirect_stdout(io.StringIO()):return runner.assess(self.root)
    def complete_reviews(self):
        (self.root/'reviews/01').mkdir(exist_ok=True)
        (self.root/'reviews/01/report.md').write_text(REPORT)
        (self.root/'reviews/01/test.log').write_text('real test log fixture')
        self.write('semantic-assessment.json',{'01':{'pass':True,'reason':'Inspected example evidence','evidence':['reviews/01/test.log']}})
    def test_missing_report_is_pending_not_success(self):
        self.assertEqual(self.assess(),2)
        self.assertIn('Overall: INCOMPLETE/FAIL',(self.root/'SUMMARY.md').read_text())
    def test_report_without_semantic_assessment_is_pending(self):
        self.complete_reviews();(self.root/'semantic-assessment.json').unlink()
        self.assertEqual(self.assess(),2)
    def test_missing_evidence_is_pending(self):
        self.complete_reviews();(self.root/'reviews/01/test.log').unlink()
        self.assertEqual(self.assess(),2)
    def test_complete_reports_and_evidence_pass(self):
        self.complete_reviews();self.assertEqual(self.assess(),0)
    def test_negative_semantic_review_fails(self):
        self.complete_reviews();data=json.loads((self.root/'semantic-assessment.json').read_text());data['01']['pass']=False
        self.write('semantic-assessment.json',data);self.assertEqual(self.assess(),1)
    def test_invalid_report_fails(self):
        self.complete_reviews();(self.root/'reviews/01/report.md').write_text('APPROVE')
        self.assertEqual(self.assess(),1)
    def test_source_change_fails(self):
        self.complete_reviews()
        with patch.object(runner,'snapshot',return_value={'source':'changed'}):self.assertEqual(self.assess(),1)
    def test_incomplete_or_empty_diagnostics_cannot_pass(self):
        self.complete_reviews()
        for marker,records in [({'completed':False,'checks':1},[{'name':'a','pass':True}]),({'completed':True,'checks':2},[{'name':'a','pass':True}]),({'completed':True,'checks':0},[])]:
            self.write('diagnostics-complete.json',marker);self.write('diagnostics.json',records)
            self.assertFalse(diagnostics_complete(self.root));self.assertEqual(self.assess(),1)
    def test_failed_diagnostics_cannot_pass(self):
        self.complete_reviews();self.write('diagnostics.json',[{'name':'a','pass':False}])
        self.assertEqual(self.assess(),1)
    def test_missing_bundle_gate_returns_nonzero(self):
        with patch.object(manage,'check_identity'),patch.object(manage,'assess',return_value=2):
            self.assertEqual(manage.gate(self.root,pathlib.Path(self.tmp.name)/'absent'),2)
    def test_stale_bundle_is_rejected(self):
        bundle=pathlib.Path(self.tmp.name)/'bundle';bundle.mkdir()
        (bundle/'bundle.json').write_text(json.dumps({'binding':{'suite':'old'},'files':{}}))
        with self.assertRaisesRegex(ValueError,'Stale'):manage.import_evidence(self.root,bundle)
    def test_tampered_evidence_is_rejected(self):
        bundle=pathlib.Path(self.tmp.name)/'bundle';bundle.mkdir()
        (bundle/'semantic-assessment.json').write_text('{}')
        (bundle/'bundle.json').write_text(json.dumps({'binding':binding(self.root),'files':{'semantic-assessment.json':'wrong'}}))
        with self.assertRaisesRegex(ValueError,'hash mismatch'):manage.import_evidence(self.root,bundle)
    def test_export_import_complete_bundle(self):
        self.complete_reviews();bundle=pathlib.Path(self.tmp.name)/'bundle'
        with patch.object(manage,'check_identity'),patch.object(manage,'assess',side_effect=lambda root:self.assess()):
            manage.export(self.root,bundle)
        import shutil
        shutil.rmtree(self.root/'reviews');(self.root/'reviews').mkdir();(self.root/'semantic-assessment.json').unlink()
        manage.import_evidence(self.root,bundle)
        self.assertEqual(self.assess(),0)
    def test_wrong_workflow_fails_before_import(self):
        with patch.object(manage,'suite_identity',return_value={'fingerprint':'different'}):
            with self.assertRaisesRegex(ValueError,'different workflow'):manage.check_identity(self.root)

class EvidenceGateCLITests(unittest.TestCase):
    """Real export/gate processes and Git snapshots; no mocked acceptance checks.

    The single-case report and diagnostics are synthetic acceptance fixtures,
    never exported into the actual kit's review-evidence directory.
    """

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='review-gate-cli-')
        self.addCleanup(temporary.cleanup)
        self.base = pathlib.Path(temporary.name)
        self.kit = self.base / 'kit'
        self.root = self.base / 'reviewed'
        self.repo = self.root / 'cases/01'
        for relative in [
            'tests/workflow/ci/manage.py',
            'tests/workflow/ci/support.py',
            'tests/run-workflow-regressions.py',
            'codex-template/.agents/skills/rust-pr-review/scripts/check-report.sh',
            'codex-template/.agents/skills/rust-pr-review/SKILL.md',
        ]:
            target = self.kit / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(manage.KIT / relative, target)
        catalog = [{'id': '01', 'name': 'Synthetic CLI acceptance fixture',
                    'verdicts': ['APPROVE'], 'archive': 'fixture.bin'}]
        self.write_json(self.kit / 'tests/workflow/cases.json', catalog)
        # Required identity inputs; prepare/diagnostics are deliberately not run.
        for relative in ['install.sh', 'vendored.tsv', 'THIRD_PARTY_NOTICES.md',
                         'tests/e2e/results/fixture.bin',
                         'tests/e2e/results/2026-10-24/oracle/regressions.rs']:
            target = self.kit / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('Synthetic identity fixture, not executable evidence.\n')
        self.source = self.repo / 'src/lib.rs'
        self.source.parent.mkdir(parents=True)
        self.source.write_text('pub fn value() -> u8 { 1 }\n')
        self.command(['git', 'init', '-q'], self.repo)
        self.command(['git', 'add', '.'], self.repo)
        self.command(['git', '-c', 'user.name=Fixture',
                      '-c', 'user.email=fixture@example.invalid',
                      '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                      'commit', '-qm', 'Synthetic fixture'], self.repo)
        self.write_json(self.root / 'inputs.json', {'01': runner.snapshot(self.repo)})
        self.write_json(self.root / 'suite-identity.json', suite_identity(self.kit))
        self.write_json(self.root / 'diagnostics.json',
                        [{'name': 'synthetic-completion-fixture', 'pass': True}])
        self.write_json(self.root / 'diagnostics-complete.json',
                        {'completed': True, 'checks': 1})
        (self.root / 'logs').mkdir()
        review = self.root / 'reviews/01'
        review.mkdir(parents=True)
        (review / 'report.md').write_text(REPORT)
        (review / 'test.log').write_text('Synthetic evidence for CLI acceptance only.\n')
        self.write_json(self.root / 'semantic-assessment.json', {
            '01': {'pass': True, 'reason': 'Synthetic acceptance fixture only',
                   'evidence': ['reviews/01/test.log']}})
        self.cli('export', self.root, expected=0)
        self.bundle = (self.kit / 'tests/workflow/review-evidence' /
                       binding(self.root)['suite'])
        # Simulate a new CI artifact, not a second import into an existing review.
        self.clean = self.base / 'ci-input'
        shutil.copytree(self.root, self.clean)
        shutil.rmtree(self.clean / 'reviews')
        (self.clean / 'reviews').mkdir()
        (self.clean / 'semantic-assessment.json').unlink()
        for name in ['SUMMARY.md', 'review-results.json']:
            (self.clean / name).unlink(missing_ok=True)

    @staticmethod
    def write_json(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    def command(self, args, cwd):
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def cli(self, action, root, expected, explicit=False):
        args = [sys.executable, str(self.kit / 'tests/workflow/ci/manage.py'),
                action, str(root)]
        if explicit:
            args += ['--destination', str(self.bundle)]
        result = subprocess.run(args, cwd=self.kit, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def change_workflow(self):
        path = self.kit / 'codex-template/.agents/skills/rust-pr-review/SKILL.md'
        path.write_text(path.read_text() + '\nRequire another independent review.\n')

    def change_source(self):
        path = self.clean / 'cases/01/src/lib.rs'
        path.write_text('pub fn value() -> u8 { 2 }\n')

    def assert_no_import(self):
        self.assertFalse(any((self.clean / 'reviews').rglob('report.md')))
        self.assertFalse((self.clean / 'semantic-assessment.json').exists())

    def test_current_bundle_accepted_via_default_ci_lookup(self):
        output = self.cli('gate', self.clean, expected=0)
        self.assertIn('Overall: PASS', output)
        self.assertEqual((self.clean / 'reviews/01/report.md').read_text(), REPORT)
        results = json.loads((self.clean / 'review-results.json').read_text())
        self.assertEqual(results[0]['status'], 'PASS')
        self.assertTrue(results[0]['unchanged'])

    def test_changed_workflow_rejects_old_run_before_import(self):
        self.change_workflow()
        output = self.cli('gate', self.clean, expected=1, explicit=True)
        self.assertIn('different workflow version', output)
        self.assert_no_import()

    def test_changed_workflow_rejects_old_bundle_with_rebound_run(self):
        self.change_workflow()
        self.write_json(self.clean / 'suite-identity.json', suite_identity(self.kit))
        output = self.cli('gate', self.clean, expected=1, explicit=True)
        self.assertIn('Stale review evidence', output)
        self.assert_no_import()

    def test_changed_source_and_manifest_reject_old_bundle(self):
        self.change_source()
        self.write_json(self.clean / 'inputs.json',
                        {'01': runner.snapshot(self.clean / 'cases/01')})
        output = self.cli('gate', self.clean, expected=1)
        self.assertIn('Stale review evidence', output)
        self.assert_no_import()

    def test_changed_source_with_stale_manifest_fails_integrity_assessment(self):
        self.change_source()
        output = self.cli('gate', self.clean, expected=1)
        self.assertIn('Overall: INCOMPLETE/FAIL', output)
        results = json.loads((self.clean / 'review-results.json').read_text())
        self.assertFalse(results[0]['unchanged'])
        self.assertEqual(results[0]['status'], 'FAIL')


if __name__=='__main__':unittest.main()
