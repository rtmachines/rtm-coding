#!/usr/bin/env bash
# Creates an isolated real Git/Cargo project. Never modifies an existing directory.
set -euo pipefail
kit=$(cd "$(dirname "$0")/../.." && pwd)
root=${1:?Usage: create-fixture.sh NEW_DIRECTORY}
[[ ! -e "$root" ]] || { echo 'Destination already exists' >&2; exit 2; }
mkdir -p "$root/repo/src" "$root/evidence" "$root/oracle"
root=$(cd "$root" && pwd)
repo="$root/repo"
cat > "$repo/Cargo.toml" <<'MANIFEST'
[package]
name = "ledger-preview"
version = "0.1.0"
edition = "2024"
license = "MIT"
publish = false
MANIFEST
cat > "$repo/.gitignore" <<'IGNORE'
/target/
/.code-review-graph/
IGNORE
cat > "$repo/deny.toml" <<'DENY'
[advisories]
[licenses]
allow = ["MIT", "Apache-2.0"]
[bans]
multiple-versions = "deny"
[sources]
unknown-registry = "deny"
unknown-git = "deny"
DENY
cat > "$repo/REQUIREMENTS.md" <<'SPEC'
# Ledger preview refactor

Preserve the existing public contracts while simplifying the implementation.
- Reading a record requires both matching tenant_id AND matching user_id.
- debit(balance, amount) returns None for insufficient funds; no successful zero
  balance may be returned for an overdraw.
- preview(text, max_chars) returns the first at most max_chars Unicode scalar values
  as a String; arbitrary UTF-8 input must not panic.
- A token is usable only while now < expires_at; the exact expiry instant is expired.
- fee(amount_cents, basis_points) floors amount_cents * basis_points / 10_000.
  All u32 inputs must be handled without overflow or intermediate rounding.
- Add parse_limit(raw) -> Option<u16>: malformed, negative and out-of-range inputs
  must return None. Expose it at the crate root.
No transport, storage, authentication provider or new dependency is required.
SPEC
cat > "$repo/src/lib.rs" <<'RUST'
//! Helpers for a tenant-aware ledger API.

#[derive(Debug, Clone, Copy)]
pub struct Identity {
    pub tenant_id: u64,
    pub user_id: u64,
}

pub fn can_read(actor: Identity, owner: Identity) -> bool {
    actor.tenant_id == owner.tenant_id && actor.user_id == owner.user_id
}

pub fn debit(balance: u64, amount: u64) -> Option<u64> {
    balance.checked_sub(amount)
}

pub fn preview(text: &str, max_chars: usize) -> String {
    text.chars().take(max_chars).collect()
}

pub fn token_usable(now: u64, expires_at: u64) -> bool {
    now < expires_at
}

/// Compute a fee in cents, flooring fractional cents.
///
/// ```
/// assert_eq!(ledger_preview::fee(1_999, 250), 49);
/// ```
pub fn fee(amount_cents: u32, basis_points: u32) -> u64 {
    u64::from(amount_cents) * u64::from(basis_points) / 10_000
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn owner_can_read() {
        let id = Identity { tenant_id: 1, user_id: 7 };
        assert!(can_read(id, id));
    }

    #[test]
    fn funded_debit() {
        assert_eq!(debit(100, 40), Some(60));
    }

    #[test]
    fn ascii_preview() {
        assert_eq!(preview("invoice", 3), "inv");
    }

    #[test]
    fn token_before_expiry() {
        assert!(token_usable(99, 100));
    }

    #[test]
    fn whole_fee() {
        assert_eq!(fee(10_000, 250), 250);
    }
}
RUST
bash "$kit/install.sh" "$repo" > "$root/evidence/install.log"
cat >> "$repo/REVIEW.md" <<'POLICY'

## Fixture project policy

This is an unpublished crate with no dependencies. Required checks: fmt, clippy,
unit tests, doctests and cargo-deny. Requirements are in REQUIREMENTS.md.
No Miri or semver-checks gate applies (no unsafe code; publish=false).
POLICY
(
  cd "$repo"
  cargo generate-lockfile --offline
  cargo fmt --all
  git init -q
  git config user.name 'Workflow Fixture'
  git config user.email 'fixture@example.invalid'
  git add .
  git commit -qm 'Baseline ledger helpers and review configuration'
  git branch baseline
  git update-ref refs/remotes/origin/main HEAD
  git rev-parse HEAD > "$root/evidence/base.sha"
  bash .agents/skills/rust-pr-review/scripts/gates.sh > "$root/evidence/baseline-gates.txt" 2> "$root/evidence/baseline-gates.log"
)
# Seed faults only after proving the baseline passes actual Cargo checks.
sed -i 's/actor.tenant_id == owner.tenant_id \&\& actor.user_id == owner.user_id/actor.user_id == owner.user_id/;s/balance.checked_sub(amount)/Some(balance.saturating_sub(amount))/;s/text.chars().take(max_chars).collect()/text[..text.len().min(max_chars)].to_owned()/;s/u64::from(amount_cents) \* u64::from(basis_points) \/ 10_000/u64::from(amount_cents \/ 10_000) * u64::from(basis_points)/' "$repo/src/lib.rs"
(
  cd "$repo"
  cargo fmt --all
  git add src/lib.rs
  git commit -qm 'Simplify ledger helper calculations'
  git rev-parse HEAD > "$root/evidence/head.sha"
)
# Exercise dirty-tree and untracked source discovery as well as committed changes.
sed -i 's/now < expires_at/now <= expires_at/' "$repo/src/lib.rs"
printf '\nmod limits;\npub use limits::parse_limit;\n' >> "$repo/src/lib.rs"
cat > "$repo/src/limits.rs" <<'RUST'
pub fn parse_limit(raw: &str) -> Option<u16> {
    Some(raw.parse::<u16>().unwrap())
}
RUST
(cd "$repo" && cargo fmt --all)
cat > "$root/oracle/expected.tsv" <<'ORACLE'
tenant-isolation	can_read	Missing tenant check permits another tenant with same local user ID
insufficient-funds	debit	Overdraw returns Some(0) rather than None
unicode-preview	preview	Byte slicing can panic or count bytes instead of Unicode scalar values
expiry-boundary	token_usable	Token accepted exactly at its expiry; dirty-tree change
fee-rounding	fee	Division before multiplication drops fractional base; doctest fails
invalid-limit	parse_limit	Untracked module panics for invalid or out-of-range input
ORACLE
cat > "$root/oracle/regressions.rs" <<'RUST'
use ledger_preview::*;
#[test]
fn tenant_isolation() {
    assert!(!can_read(Identity { tenant_id: 1, user_id: 7 }, Identity { tenant_id: 2, user_id: 7 }));
}
#[test]
fn insufficient_funds() { assert_eq!(debit(10, 11), None); }
#[test]
fn unicode_preview() { assert_eq!(preview("żółw", 1), "ż"); }
#[test]
fn expiry_boundary() { assert!(!token_usable(100, 100)); }
#[test]
fn fee_rounding() { assert_eq!(fee(1_999, 250), 49); }
#[test]
fn invalid_limit() { assert_eq!(parse_limit("bogus"), None); }
RUST
printf '%s\n' "$root"
