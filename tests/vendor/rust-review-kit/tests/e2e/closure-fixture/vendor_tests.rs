#![cfg(not(feature = "model"))]
use runtime_bridge::{acme::{AcmeTransport, Reply, Server}, deliver, Outcome};
use std::{future::Future, sync::Arc, task::{Context, Poll, Waker}, time::Duration};

#[tokio::test]
async fn timeout_after_commit_then_retry_deduplicates() {
    let server = Arc::new(Server::default());
    let lost = AcmeTransport::new(server.clone(), Reply::LoseAfterCommit);
    assert_eq!(deliver(&lost, 7, Duration::ZERO).await, Outcome::Retry(7));
    assert_eq!(server.effect_count(), 1);
    let retry = AcmeTransport::new(server.clone(), Reply::Normal);
    for _ in 0..3 {
        assert_eq!(deliver(&retry, 7, Duration::from_secs(1)).await, Outcome::Delivered(7));
    }
    assert_eq!(server.effect_count(), 1);
}
#[tokio::test]
async fn cancel_at_both_boundaries_then_retry() {
    for (reply, committed) in [(Reply::StallBeforeCommit, 0), (Reply::LoseAfterCommit, 1)] {
        let server = Arc::new(Server::default());
        let client = AcmeTransport::new(server.clone(), reply);
        let mut operation = Box::pin(deliver(&client, 9, Duration::from_secs(30)));
        assert!(matches!(operation.as_mut().poll(&mut Context::from_waker(Waker::noop())), Poll::Pending));
        assert_eq!(server.effect_count(), committed);
        drop(operation);
        let retry = AcmeTransport::new(server.clone(), Reply::Normal);
        assert_eq!(deliver(&retry, 9, Duration::from_secs(1)).await, Outcome::Delivered(9));
        assert_eq!(server.effect_count(), 1);
    }
}
#[tokio::test]
async fn reconnect_and_quiescent_restart_preserve_keys() {
    let server = Arc::new(Server::default());
    let client = AcmeTransport::new(server.clone(), Reply::LoseAfterCommit);
    assert_eq!(deliver(&client, 11, Duration::ZERO).await, Outcome::Retry(11));
    drop(client);
    let state = server.snapshot();
    drop(server);
    let restored = Arc::new(Server::restore(state));
    let client = AcmeTransport::new(restored.clone(), Reply::Normal);
    assert_eq!(deliver(&client, 11, Duration::from_secs(1)).await, Outcome::Delivered(11));
    assert_eq!(restored.effect_count(), 1);
    assert_eq!(deliver(&client, 12, Duration::from_secs(1)).await, Outcome::Delivered(12));
    assert_eq!(restored.effect_count(), 2);
}
