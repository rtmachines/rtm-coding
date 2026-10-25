use runtime_bridge::{service::*, bytes::read_word};
use std::{collections::VecDeque, future::Future, sync::{Arc,atomic::{AtomicUsize,Ordering}}, task::{Context,Poll,Waker},time::Duration};
use tokio::sync::{Mutex,oneshot};
#[test]
fn alignment_and_short_input() { let b=[1u8,2,3,4,5]; assert_eq!(read_word(&b[1..]),Some(u32::from_ne_bytes([2,3,4,5]))); for n in 0..4 {assert_eq!(read_word(&b[..n]),None);} }
#[tokio::test]
async fn progress_and_later_snapshot() {
 let service=Arc::new(Service::default()); let other=service.clone();
 let task=tokio::spawn(async move { other.increment_and_snapshot().await });
 tokio::time::timeout(Duration::from_secs(1),service.increment_and_snapshot()).await.unwrap();
 tokio::time::timeout(Duration::from_secs(1),task).await.unwrap().unwrap();
 assert_eq!(tokio::time::timeout(Duration::from_secs(1),service.snapshot()).await.unwrap(),2);
}
#[tokio::test]
async fn cancellation_and_channel_closure_preserve_queue() {
 let queue=Mutex::new(VecDeque::from([7]));let (tx,rx)=oneshot::channel();
 let mut op=Box::pin(approved_pop(&queue,rx));
 assert!(matches!(op.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));
 drop(op);assert_eq!(*queue.lock().await,VecDeque::from([7]));drop(tx);
 let (tx,rx)=oneshot::channel();drop(tx);assert_eq!(approved_pop(&queue,rx).await,None);assert_eq!(*queue.lock().await,VecDeque::from([7]));
 let (tx,rx)=oneshot::channel();tx.send(()).unwrap();let guard=queue.lock().await;
 let mut op=Box::pin(approved_pop(&queue,rx));assert!(matches!(op.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));drop(op);drop(guard);assert_eq!(*queue.lock().await,VecDeque::from([7]));
}
struct Mark(Arc<AtomicUsize>); impl Drop for Mark {fn drop(&mut self){self.0.fetch_add(1,Ordering::SeqCst);}}
#[tokio::test]
async fn stop_observes_destructor_and_prevents_effects() {
 let effects=Arc::new(AtomicUsize::new(0));let dropped=Arc::new(AtomicUsize::new(0));let e=effects.clone();let d=dropped.clone();
 let (ready_tx,ready_rx)=oneshot::channel();let (go_tx,go_rx)=oneshot::channel();
 let task=tokio::spawn(async move {let _mark=Mark(d);ready_tx.send(()).unwrap();let _=go_rx.await;e.fetch_add(1,Ordering::SeqCst);});
 ready_rx.await.unwrap();tokio::time::timeout(Duration::from_secs(1),stop_worker(task)).await.unwrap();
 assert_eq!(dropped.load(Ordering::SeqCst),1);assert!(go_tx.send(()).is_err());tokio::task::yield_now().await;assert_eq!(effects.load(Ordering::SeqCst),0);
}
