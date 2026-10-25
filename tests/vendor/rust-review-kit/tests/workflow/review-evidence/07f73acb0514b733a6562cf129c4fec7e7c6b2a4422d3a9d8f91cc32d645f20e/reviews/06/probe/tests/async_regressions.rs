use runtime_bridge::service::{Service, approved_pop, stop_worker};
use std::{
    collections::VecDeque,
    future::Future,
    task::{Context, Poll, Waker},
    time::Duration,
};
use tokio::sync::{Mutex, oneshot};

#[tokio::test]
async fn nested_lock_completes() {
    let service = Service::default();
    let value =
        tokio::time::timeout(Duration::from_millis(100), service.increment_and_snapshot()).await;
    assert_eq!(value.expect("nested lock did not complete"), 1);
}

#[tokio::test]
async fn cancel_before_approval_preserves_item() {
    let queue = Mutex::new(VecDeque::from([7]));
    let (_approval, rx) = oneshot::channel();
    let mut operation = Box::pin(approved_pop(&queue, rx));
    let mut cx = Context::from_waker(Waker::noop());
    assert!(matches!(operation.as_mut().poll(&mut cx), Poll::Pending));
    drop(operation);
    assert_eq!(queue.lock().await.front(), Some(&7));
}

#[tokio::test]
async fn stopped_worker_cannot_receive_more_work() {
    let (started_tx, started_rx) = oneshot::channel();
    let (release_tx, release_rx) = oneshot::channel();
    let (effect_tx, effect_rx) = oneshot::channel();
    let worker = tokio::spawn(async move {
        let _ = started_tx.send(());
        if release_rx.await.is_ok() {
            let _ = effect_tx.send(());
        }
    });
    started_rx.await.unwrap();
    stop_worker(worker).await;
    let received_more_work = release_tx.send(()).is_ok();
    if received_more_work {
        tokio::time::timeout(Duration::from_millis(100), effect_rx)
            .await
            .unwrap()
            .unwrap();
    }
    assert!(
        !received_more_work,
        "side effect observed after stop returned"
    );
}
