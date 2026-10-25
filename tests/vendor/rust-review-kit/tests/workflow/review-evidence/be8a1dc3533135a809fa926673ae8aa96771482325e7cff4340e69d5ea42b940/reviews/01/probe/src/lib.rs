//! Helpers for a tenant-aware ledger API.

#[derive(Debug, Clone, Copy)]
pub struct Identity {
    pub tenant_id: u64,
    pub user_id: u64,
}

pub fn can_read(actor: Identity, owner: Identity) -> bool {
    actor.user_id == owner.user_id
}

pub fn debit(balance: u64, amount: u64) -> Option<u64> {
    Some(balance.saturating_sub(amount))
}

pub fn preview(text: &str, max_chars: usize) -> String {
    text[..text.len().min(max_chars)].to_owned()
}

pub fn token_usable(now: u64, expires_at: u64) -> bool {
    now <= expires_at
}

/// Compute a fee in cents, flooring fractional cents.
///
/// ```
/// assert_eq!(ledger_preview::fee(1_999, 250), 49);
/// ```
pub fn fee(amount_cents: u32, basis_points: u32) -> u64 {
    u64::from(amount_cents / 10_000) * u64::from(basis_points)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn owner_can_read() {
        let id = Identity {
            tenant_id: 1,
            user_id: 7,
        };
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

mod limits;
pub use limits::parse_limit;
