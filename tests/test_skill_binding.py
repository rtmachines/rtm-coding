"""Mutation tests for the publication boundary; no fabricated review reports."""
import shutil
import tempfile
import unittest
from pathlib import Path

from check_skill_binding import ROOT, check


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in ['skills', 'tests/vendor/rust-review-kit/codex-template/.agents/skills']:
            shutil.copytree(ROOT / relative, self.root / relative)
        self.skill = self.root / 'skills/rust-pr-review/SKILL.md'

    def test_unchanged_sources(self):
        check(self.root)

    def test_changed_skill_rejected(self):
        self.skill.write_text(self.skill.read_text() + '\nChanged instruction\n')
        with self.assertRaises(ValueError):
            check(self.root)

    def test_missing_skill_rejected(self):
        self.skill.unlink()
        with self.assertRaises(ValueError):
            check(self.root)

    def test_new_unreviewed_file_rejected(self):
        self.skill.with_name('extra.md').write_text('New instructions')
        with self.assertRaises(ValueError):
            check(self.root)

    def test_symlink_rejected(self):
        target = self.root / 'outside.md'
        target.write_bytes(self.skill.read_bytes())
        self.skill.unlink()
        self.skill.symlink_to(target)
        with self.assertRaises(ValueError):
            check(self.root)

    def test_companion_change_rejected(self):
        (self.root / 'skills/rust-best-practices/SKILL.md').write_text('Changed handbook')
        with self.assertRaises(ValueError):
            check(self.root)


if __name__ == '__main__':
    unittest.main()
