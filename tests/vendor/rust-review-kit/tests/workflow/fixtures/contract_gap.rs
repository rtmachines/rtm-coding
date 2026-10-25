use runtime_bridge::{Delivery, Outcome, Transport, deliver};
use std::{sync::atomic::{AtomicUsize, Ordering}, time::Duration};
struct Adapter { commit_before_receipt: bool, remote_effects: AtomicUsize }
impl Transport for Adapter {
    fn send(&self, _: u64) -> Delivery<'_> {
        Box::pin(async move {
            if self.commit_before_receipt { self.remote_effects.fetch_add(1, Ordering::SeqCst); }
            std::future::pending().await
        })
    }
}
#[tokio::test]
async fn same_local_outcome_does_not_determine_remote_commit() {
    for commit in [false, true] {
        let vendor = Adapter { commit_before_receipt: commit, remote_effects: AtomicUsize::new(0) };
        assert_eq!(deliver(&vendor, 7, Duration::ZERO).await, Outcome::Retry(7));
        assert_eq!(vendor.remote_effects.load(Ordering::SeqCst), usize::from(commit));
        println!("Retry(7), committed remote effects={}", usize::from(commit));
    }
}
