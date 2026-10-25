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
