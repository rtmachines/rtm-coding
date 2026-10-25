use runtime_bridge::{Delivery, Outcome, Transport, deliver};
use std::time::Duration;
struct Ready;
impl Transport for Ready {
    fn send(&self, request: u64) -> Delivery<'_> { Box::pin(async move { request }) }
}
struct Pending;
impl Transport for Pending {
    fn send(&self, _: u64) -> Delivery<'_> { Box::pin(std::future::pending()) }
}
#[tokio::test]
async fn delivers() { assert_eq!(deliver(&Ready, 7, Duration::from_secs(1)).await, Outcome::Delivered(7)); }
#[tokio::test]
async fn returns_for_retry() { assert_eq!(deliver(&Pending, 7, Duration::ZERO).await, Outcome::Retry(7)); }
