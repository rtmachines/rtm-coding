# Real Rust workflow evaluation

This fixture exercises the installed Codex review workflow using real Git, Cargo,
rustfmt, Clippy, nextest (when installed), doctests and cargo-deny. It has no third-party
Rust dependencies. Build/check commands are authorized only in these generated fixtures.

## Reproduce the fixture and oracle

From the kit root, choose a new directory (must not already exist):

```sh
bash tests/e2e/create-fixture.sh /tmp/rust-review-evaluation
bash tests/e2e/verify-regressions.sh /tmp/rust-review-evaluation
```

The first script installs the kit, commits a correct baseline, verifies all gates,
then introduces six defects. Four are committed, one is an unstaged modification,
and one is in an untracked module. It creates `origin/main` locally without a remote.
No GitHub account, push or publication is used. cargo-deny may fetch its advisory DB.
The second script verifies held-out regression tests against faulty and corrected
copies in debug and release profiles, without modifying the reviewed tree.

## Independent review protocol

Give a fresh reviewing agent only:

- the absolute path of `repo/`;
- its installed `.agents/skills/rust-pr-review/SKILL.md`;
- the request to review branch plus dirty/untracked changes vs `origin/main` against
  `REQUIREMENTS.md`;
- permission to run fixture checks and save a report in an external output directory.

Do not disclose the seed list, `oracle/`, this README or the sibling probe copies.
Require the report to pass the installed `check-report.sh`. Compare it with the
oracle only after the report is finished. Check source hashes/Git status before and
after to ensure the reviewer did not fix or otherwise alter the target.

A control review should use the baseline code plus a correct `parse_limit` implementation
in a separate Git repository. It should pass gates and produce APPROVE with no defects.
This tests false positives as well as detection. Automated script tests alone do not
measure model review quality. A single successful six-case experiment does not establish
a general recall rate, nor does it exercise remote GitHub CI/branch protection.

## Expected seeded cases (for evaluation only)

| Case | Trigger | Expected consequence |
|---|---|---|
| Tenant isolation | same user ID in different tenants | unauthorized record access |
| Overdraw | debit(10, 11) | Some(0) instead of None |
| Unicode preview | preview("żółw", 1) | panic at UTF-8 byte boundary |
| Token expiry | now == expires_at | token remains accepted |
| Fee rounding | fee(1999, 250) | 0 instead of 49 cents |
| Invalid limit | parse_limit("bogus") | panic instead of None |

The existing five unit tests intentionally cover only happy paths. The existing
doctest covers fee rounding. Thus semantic findings should add value beyond green
Clippy and unit tests. The checker may describe fee rounding under the failed gate
rather than duplicate it as a finding; count detection by underlying cause.

Advanced unsafe/FFI, cancellation, deadlock and atomic-publication evaluation:
[ADVANCED.md](ADVANCED.md).

All evaluated scenarios are consolidated in the [workflow regression suite](../workflow/README.md).
