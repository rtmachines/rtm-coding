#!/usr/bin/env bash
# Installer contract tests: no network, preserved user state, safe destinations.
set -euo pipefail
kit="$(cd "$(dirname "$0")/.." && pwd)"
python3 - "$kit" <<'PY'
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

KIT = Path(sys.argv.pop())
PIN = "a1e290d53d43a85421ff16dde23b5f8ec0b48539"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="claude-install-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "project with ' quotes $ and ` marks"
        self.repo.mkdir()
        (self.repo / "Cargo.toml").write_text('[package]\nname="fixture"\nversion="0.1.0"\n')
        bins = self.root / "bin"
        bins.mkdir()
        self.network = self.root / "network-attempts"
        for name in ("curl", "wget", "ssh", "npm", "npx", "uv"):
            path = bins / name
            path.write_text('#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$NETWORK_LOG"\nexit 97\n')
            path.chmod(0o755)
        # Keep this installation test independent of Rust toolchains.
        for name in ("cargo", "rust-analyzer", "gh"):
            path = bins / name
            path.write_text('#!/bin/sh\nexit 0\n')
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{bins}:{os.environ['PATH']}", NETWORK_LOG=str(self.network))

    def install(self, *args, ok=True):
        result = subprocess.run(["bash", str(KIT / "install-claude.sh"), "--no-ci", *args, str(self.repo)],
                                env=self.env, text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def settings(self):
        return json.loads((self.repo / ".claude/settings.json").read_text())

    def test_offline_pinned_knowledge_and_licenses(self):
        self.install()
        source = KIT / "codex-template/.agents/skills/rust-skills"
        installed = self.repo / ".claude/skills/rust-skills"
        files = [p for p in source.rglob("*") if p.is_file()]
        self.assertGreater(len(list(source.glob("rules/*.md"))), 250)
        for path in files:
            target = installed / path.relative_to(source)
            self.assertTrue(target.is_file(), str(target))
            self.assertEqual(target.read_bytes(), path.read_bytes())
        metadata = self.repo / ".claude/rust-review-kit"
        self.assertIn(PIN, (metadata / "vendored.tsv").read_text())
        self.assertIn(PIN, (metadata / "THIRD_PARTY_NOTICES.md").read_text())
        self.assertTrue(list((metadata / "licenses").glob("*")))
        self.assertFalse(self.network.exists(), self.network.read_text() if self.network.exists() else "")

    def test_default_permissions_and_native_hooks(self):
        self.install()
        config = self.settings()
        self.assertFalse(any(config.get("enabledPlugins", {}).values()))
        self.assertNotIn("extraKnownMarketplaces", config)
        self.assertFalse(config.get("permissions", {}).get("allow", []))
        self.assertNotIn("Stop", config["hooks"])
        commit = config["hooks"]["PreToolUse"][0]
        self.assertEqual(commit["matcher"], "Bash")
        hook = commit["hooks"][0]
        self.assertNotIn("if", hook, "The adapter must see alternate Git roots before deciding whether to gate")
        self.assertEqual(hook["command"], "bash")
        self.assertEqual(hook["args"], ["${CLAUDE_PROJECT_DIR}/.claude/hooks/rust-gate.sh", "commit"])
        self.assertEqual(hook["onFailure"], "block")

    def test_force_preserves_custom_files_and_settings(self):
        folder = self.repo / ".claude/skills/rust-pr-review"
        folder.mkdir(parents=True)
        (folder / "custom-notes.md").write_text("user notes")
        (folder / "SKILL.md").write_text("old kit")
        config = {"model": "user-choice", "permissions": {"allow": ["Bash(custom-check)"]},
                  "enabledPlugins": {"rust-analyzer-lsp@claude-plugins-official": False, "mine@example": True},
                  "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "custom-stop"}]}]}}
        (self.repo / ".claude/settings.json").write_text(json.dumps(config))
        self.install("--force")
        self.assertEqual((folder / "custom-notes.md").read_text(), "user notes")
        self.assertEqual((folder / "SKILL.md").read_bytes(), (KIT / "template/.claude/skills/rust-pr-review/SKILL.md").read_bytes())
        merged = self.settings()
        self.assertEqual(merged["model"], config["model"])
        self.assertEqual(merged["enabledPlugins"], config["enabledPlugins"])
        self.assertEqual(merged["permissions"]["allow"], config["permissions"]["allow"])
        self.assertEqual(merged["hooks"]["Stop"], config["hooks"]["Stop"])
        self.assertEqual(json.loads((self.repo / ".claude/rust-review-kit/settings.json.before-install").read_text()), config)

    def test_idempotent_and_no_force_keeps_owned_file(self):
        self.install()
        original = (self.repo / ".claude/settings.json").read_bytes()
        owned = self.repo / ".claude/skills/rust-pr-review/SKILL.md"
        owned.write_text("customized skill")
        self.install()
        self.assertEqual(owned.read_text(), "customized skill")
        self.assertEqual((self.repo / ".claude/settings.json").read_bytes(), original)
        self.assertEqual((self.repo / "CLAUDE.md").read_text().count("rust-review-kit:begin"), 1)

    def test_force_updates_only_marked_claude_block(self):
        (self.repo / "CLAUDE.md").write_text("user before\n<!-- rust-review-kit:begin -->\nold policy\n<!-- rust-review-kit:end -->\nuser after\n")
        self.install("--force")
        text = (self.repo / "CLAUDE.md").read_text()
        self.assertTrue(text.startswith("user before\n"))
        self.assertTrue(text.endswith("\nuser after\n"))
        self.assertNotIn("old policy", text)
        self.assertEqual(text.count("rust-review-kit:begin"), 1)

    def test_malformed_claude_markers_preserve_user_prose(self):
        for text in ("before\n<!-- rust-review-kit:begin -->\nuser after\n",
                     "before\n<!-- rust-review-kit:end -->\nafter\n",
                     "<!-- rust-review-kit:begin -->\n<!-- rust-review-kit:begin -->\n<!-- rust-review-kit:end -->\n"):
            with self.subTest(content=text):
                (self.repo / "CLAUDE.md").write_text(text)
                self.install("--force", ok=False)
                self.assertEqual((self.repo / "CLAUDE.md").read_text(), text)

    def test_legacy_global_hook_migration_preserves_custom_stop(self):
        folder = self.repo / ".claude"
        folder.mkdir()
        legacy = {"type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/rust-gate.sh", "args": ["stop"], "timeout": 900}
        custom = {"type": "command", "command": "custom-stop"}
        (folder / "settings.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [legacy, custom]}]}}))
        self.install("--force")
        self.assertEqual(self.settings()["hooks"]["Stop"], [{"hooks": [custom]}])

    def test_symlink_destinations_rejected_without_outside_writes(self):
        for relative in (".claude", ".claude/skills/rust-skills", ".claude/settings.json", "CLAUDE.md", ".claude/rust-review-kit/licenses"):
            with self.subTest(path=relative):
                repo = self.root / ("symlink-" + relative.replace("/", "-"))
                repo.mkdir()
                previous = self.repo
                self.repo = repo
                outside = self.root / (repo.name + "-outside")
                if relative.endswith(".json") or relative == "CLAUDE.md":
                    outside.write_text("{}")
                else:
                    outside.mkdir()
                    (outside / "sentinel").write_text("do not touch")
                target = repo / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(outside)
                self.install("--force", ok=False)
                self.assertTrue(target.is_symlink())
                if outside.is_dir():
                    self.assertEqual([p.name for p in outside.iterdir()], ["sentinel"])
                else:
                    self.assertEqual(outside.read_text(), "{}")
                self.repo = previous

    def test_invalid_settings_preserved(self):
        folder = self.repo / ".claude"
        folder.mkdir()
        for text in ("broken json", "[]", "null", '{"hooks":[]}'):
            with self.subTest(content=text):
                (folder / "settings.json").write_text(text)
                self.install("--force", ok=False)
                self.assertEqual((folder / "settings.json").read_text(), text)

    def test_plugins_only_when_explicit(self):
        self.install("--zeroize", "--pr-toolkit")
        plugins = self.settings()["enabledPlugins"]
        self.assertTrue(plugins["zeroize-audit@trailofbits"])
        self.assertTrue(plugins["pr-review-toolkit@claude-plugins-official"])
        self.assertNotIn("rust-review@trailofbits", plugins)


unittest.main(verbosity=2, defaultTest=os.environ.get("INSTALL_TEST", None))
PY
