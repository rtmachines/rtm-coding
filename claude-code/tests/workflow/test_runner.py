#!/usr/bin/env python3
"""Check that infrastructure failures cannot masquerade as detected Rust bugs."""
import importlib.util
import pathlib
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('runner', pathlib.Path(__file__).parents[1]/'run-workflow-regressions.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class RunnerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root/'logs').mkdir()
        self.run_check = runner.Run(self.root)
    def tearDown(self):
        self.tmp.cleanup()
    def command(self, code):
        return [sys.executable, '-c', code]
    def test_unrelated_failure_is_not_a_detected_bug(self):
        self.assertFalse(self.run_check.check('compile-error', self.command('print("compiler error");raise SystemExit(101)'), self.root, 101, ['Undefined Behavior']))
    def test_zero_tests_do_not_satisfy_required_test(self):
        self.assertFalse(self.run_check.check('empty', self.command('print("0 passed; 0 failed")'), self.root, 0, ['1 passed; 0 failed']))
    def test_timeout_is_not_a_detected_bug(self):
        self.assertFalse(self.run_check.check('hang', self.command('import time;time.sleep(10)'), self.root, 101, ['failed'], timeout=0.05))
        self.assertIsNone(self.run_check.results[0]['exit'])
    def test_matching_counterexample_is_accepted(self):
        self.assertTrue(self.run_check.check('counterexample', self.command('print("left: 0");raise SystemExit(101)'), self.root, 101, ['left: 0']))
    def test_nonzero_exit_does_not_satisfy_success(self):
        self.assertFalse(self.run_check.check('interrupted', self.command('print("1 passed; 0 failed");raise SystemExit(124)'), self.root, 0, ['1 passed; 0 failed']))

if __name__ == '__main__':
    unittest.main()
