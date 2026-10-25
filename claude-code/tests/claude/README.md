# Claude regression tests

Run the deterministic script contracts with:

```bash
bash tests/test-claude.sh
python tests/claude/test_runner.py
```

The shell entrypoint installs Claude's workflow into a temporary repository and runs the shared context, gates, report-validator, and reviewdog contracts against that installation. Fixtures cover missing semantic APIs, incomplete Miri/aliasing, Loom and cancellation evidence, escalation, and approval after evidence closes a risk. These synthetic report-contract checks are not model reviews.

## Full oracle run and fresh reviews

Use a new output directory. Preparation extracts the 11 existing source fixtures, installs the current Claude workflow, and writes `review-requests.json`. It does not run a model, import old reports, or fabricate fresh reviews.

```bash
python tests/run-claude-regressions.py /tmp/claude-regression-run --phase prepare
python tests/run-claude-regressions.py /tmp/claude-regression-run --phase diagnostics
```

Diagnostics reuse all 49 Rust and infrastructure checks from the existing workflow runner. The installation/contract check selects Claude's installed scripts. Rust fixtures use the existing offline toolchains, Miri and Loom; `MIRI_TOOLCHAIN` may select an already installed toolchain. Failed commands, missing tools, timeouts, and incomplete diagnostics remain failures. To repeat diagnostics while preserving the old attempt, add `--rerun`.

Run each request independently through the actual native Claude CLI. Keep its successful JSON or JSONL output within the run directory, alongside the resulting `report.md` and diagnostic artifacts. Native CLI execution and any workspace-trust/agent/settings setup are separate from this runner. For example, after case 01 has actually completed:

```bash
python tests/run-claude-regressions.py /tmp/claude-regression-run \
  --phase record --case 01 --transcript reviews/01/claude.json
```

`record` requires a successful native result with a session ID whose result text matches the saved report (ignoring surrounding whitespace), and binds the transcript and report hashes to the Claude suite fingerprint and reviewed source snapshot. Ask the native CLI's main agent to return the full final report, and save that same text as `report.md`. A wrapper response such as “READY” does not count as report evidence. The runner refuses missing reports, empty/failed transcripts, changed sources, stale kit versions, and replacement of recorded provenance. This binds supplied execution evidence; it does not independently authenticate a transcript or replace semantic review of the actual report.

After the actual reviews, independently assess their explanations and evidence. Write `semantic-assessment.json`, keyed by case ID, with a boolean `pass`, a nonempty `reason`, and an `evidence` list of existing paths relative to the run directory. Then assess:

```bash
python tests/run-claude-regressions.py /tmp/claude-regression-run --phase assess
```

The runner produces `review-results.json` and `SUMMARY.md`. Exit 0 requires all diagnostics, report contracts, expected verdicts, unchanged sources, native provenance, and semantic assessments to pass. Missing fresh reports remain `PENDING`; a diagnostics-only run is never an overall pass. Fresh reviews may be deferred, but the result stays incomplete. Exit 2 indicates incomplete reviews/semantic assessment after successful diagnostics; other failures return 1.

The Claude identity includes its templates, optional skills, installer, bundled Rust knowledge, shared tests, and source archives. Codex's default identity format remains unchanged. Claude provenance is a standalone evidence format; this entrypoint does not claim compatibility with the existing Codex CI evidence-bundle exporter. Never relabel historical Codex reports as fresh Claude reviews.

Claude input snapshots bind bytes and modes for every Git-tracked and nonignored untracked file, including manifests, requirements, configuration, nested providers, and the installed `.claude` workflow. Git-ignored build outputs and graph caches are excluded. Symlinks bind their link-target bytes without being followed and may target only direct regular files already in the Git-visible inventory. Escaping, indirect, dangling, ignored-target, directory-target, and ancestor symlinks, plus non-file inputs such as submodules, are rejected as unsupported. Codex's existing source snapshot format is preserved.

## Opt-in native hook transport regression

```bash
CLAUDE_NATIVE_TESTS=1 python3 tests/claude/test_native.py
```

This separate smoke test requires an already installed and authenticated Claude CLI.
It uses the account's configured model and consumes normal account usage. It does not
log in, change workspace trust, install tools or run Cargo. The test registers the
installed agent's exact Stop hook through an explicit CLI agent definition in an
isolated fixture, supplies an intentionally invalid `DONE`, requires native rejection
feedback, and validates the subsequent complete `INCOMPLETE` control report. It tests
hook transport, not Rust analysis, project-folder trust, or fresh review behavior.

Evidence is preserved in a printed `/tmp/claude-native-stop-*` directory with
`status.json`, native events and debug output. Set `CLAUDE_NATIVE_OUTPUT_DIR` to an
existing parent directory to choose its location, or `CLAUDE_NATIVE_BINARY` to an
installed CLI path. Missing opt-in or CLI yields `NOT RUN`/skip and direct invocation
exits 2. Authentication failures, timeouts, ignored hook errors or invalid final
reports fail the test; a successful CLI exit alone never means PASS. Unit fixtures
also reject the observed failure mode where the host logs a Stop-hook error but still
returns `DONE` successfully. Debug logs are local diagnostic artifacts; inspect them
before sharing them outside the project.
