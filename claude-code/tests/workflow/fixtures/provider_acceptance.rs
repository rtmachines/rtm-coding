use runtime_bridge::{acme::{AcmeTransport, Reply, Server}, deliver, Outcome};
use std::{sync::Arc, time::Duration, future::Future, task::{Context, Poll, Waker}};

#[tokio::test(flavor = "current_thread")]
async fn timeout_before_commit_reconnect_and_retry() {
    let server = Arc::new(Server::default());
    let stalled = AcmeTransport::new(server.clone(), Reply::StallBeforeCommit);
    assert_eq!(deliver(&stalled, 42, Duration::ZERO).await, Outcome::Retry(42));
    assert_eq!(server.effect_count(), 0);
    drop(stalled);
    tokio::task::yield_now().await;
    assert_eq!(Arc::strong_count(&server), 1);
    assert_eq!(server.effect_count(), 0);
    let retry = AcmeTransport::new(server.clone(), Reply::Normal);
    assert_eq!(deliver(&retry, 42, Duration::from_secs(1)).await, Outcome::Delivered(42));
    assert_eq!(server.effect_count(), 1);
    drop(retry);
    let reconnect = AcmeTransport::new(server.clone(), Reply::Normal);
    assert_eq!(deliver(&reconnect, 42, Duration::from_secs(1)).await, Outcome::Delivered(42));
    assert_eq!(server.effect_count(), 1);
}

#[tokio::test(flavor = "current_thread")]
async fn drop_at_known_boundaries_releases_operation_without_later_effects() {
    for (fault, expected) in [(Reply::StallBeforeCommit,0), (Reply::LoseAfterCommit,1)] {
        let server = Arc::new(Server::default());
        let transport = AcmeTransport::new(server.clone(), fault);
        let mut operation = Box::pin(deliver(&transport, 51, Duration::from_secs(30)));
        assert_eq!(operation.as_mut().poll(&mut Context::from_waker(Waker::noop())), Poll::Pending);
        assert_eq!(server.effect_count(), expected);
        drop(operation);
        drop(transport);
        assert_eq!(Arc::strong_count(&server), 1);
        for _ in 0..3 { tokio::task::yield_now().await; }
        assert_eq!(server.effect_count(), expected);
        let retry = AcmeTransport::new(server.clone(), Reply::Normal);
        assert_eq!(deliver(&retry, 51, Duration::from_secs(1)).await, Outcome::Delivered(51));
        assert_eq!(server.effect_count(),1);
    }
}
