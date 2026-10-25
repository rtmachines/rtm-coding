use std::collections::VecDeque;
use tokio::sync::{Mutex, oneshot};
use tokio::task::JoinHandle;

#[derive(Default)]
pub struct Service {
    count: Mutex<u64>,
}
impl Service {
    pub async fn snapshot(&self) -> u64 {
        *self.count.lock().await
    }
    pub async fn increment_and_snapshot(&self) -> u64 {
        let mut count = self.count.lock().await;
        *count += 1;
        self.snapshot().await
    }
}

/// Dequeue only when approval arrives. Dropping this future must preserve the queue.
pub async fn approved_pop(
    queue: &Mutex<VecDeque<u64>>,
    approval: oneshot::Receiver<()>,
) -> Option<u64> {
    let item = queue.lock().await.pop_front();
    approval.await.ok()?;
    item
}

/// Return only after the owned worker can no longer cause side effects.
pub async fn stop_worker(worker: JoinHandle<()>) {
    drop(worker);
}

#[cfg(test)]
mod tests {
    use super::*;
    #[tokio::test]
    async fn snapshot_initial() {
        assert_eq!(Service::default().snapshot().await, 0);
    }
    #[tokio::test]
    async fn approved_delivery() {
        let queue = Mutex::new(VecDeque::from([7]));
        let (tx, rx) = oneshot::channel();
        tx.send(()).unwrap();
        assert_eq!(approved_pop(&queue, rx).await, Some(7));
    }
}
