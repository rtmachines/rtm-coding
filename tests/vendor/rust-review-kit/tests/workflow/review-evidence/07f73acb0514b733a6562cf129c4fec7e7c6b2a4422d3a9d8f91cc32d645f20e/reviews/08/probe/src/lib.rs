use std::{future::Future, pin::Pin, time::Duration};
pub type Receipt = u64;
pub type Delivery<'a> = Pin<Box<dyn Future<Output = Receipt> + Send + 'a>>;
pub trait Transport {
    fn send(&self, request: u64) -> Delivery<'_>;
}
#[derive(Debug, PartialEq, Eq)]
pub enum Outcome {
    Delivered(Receipt),
    Retry(u64),
}
/// Submit a request, returning it to the caller on expiry for later retry.
pub async fn deliver(transport: &impl Transport, request: u64, deadline: Duration) -> Outcome {
    match tokio::time::timeout(deadline, transport.send(request)).await {
        Ok(receipt) => Outcome::Delivered(receipt),
        Err(_) => Outcome::Retry(request),
    }
}
