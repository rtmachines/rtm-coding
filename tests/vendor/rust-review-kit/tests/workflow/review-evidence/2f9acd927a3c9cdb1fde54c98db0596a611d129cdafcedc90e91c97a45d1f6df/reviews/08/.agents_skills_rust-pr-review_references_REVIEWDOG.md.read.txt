# Optional local reviewdog

Run from the reviewed Cargo workspace:

```bash
RUST_REVIEWDOG=1 bash .agents/skills/rust-pr-review/scripts/gates.sh
```

The helper runs Clippy once, preserves raw uncolored short diagnostics and its exit
code in a printed temporary evidence directory, then feeds that file to reviewdog.
It uses the local reporter only and installs nothing. Missing reviewdog falls back
to the raw diagnostics. Its errors/status are separate from the Clippy gate.
`RUST_REVIEWDOG_BIN` can select an existing executable by name or absolute path.
Retain the evidence files until the review is complete.

Default filtering is `nofilter`. For tracked branch plus working-tree changes, set
`RUST_REVIEWDOG_BASE` to the already resolved review base SHA. For working-tree-only
review, use HEAD. For a committed-only scope, use matching checkout/CI evidence;
this helper's diff includes local edits. Invalid bases fall back to unfiltered output.
Git diff excludes untracked files: omit the base when they are in scope.

Always derive the `clippy` gate from Clippy's exit status, not reviewdog's report or
exit status. Inspect raw output on compilation failure, parser failure or an empty
report. A successful reviewdog process with zero displayed diagnostics is not a
passing lint check. Record presentation failures/omissions separately in the report;
reviewdog does not replace Miri, Loom, tests or semantic review.

If the project already has `.reviewdog.yml` or `.reviewdog.yaml`, prefer its relevant
lint runners with `-reporter=local -filter-mode=nofilter -fail-level=warning` for
project presentation. Still run the Clippy gate independently: config runners may
filter, mask failures or use different flags. Do not automatically execute every
runner. Do not feed RTK-condensed output to a parser; use `rtk bypass` for a producer
if it is intercepted. The helper calls Cargo directly without a condensing wrapper.
Remote reporters require an explicit request to publish results.
