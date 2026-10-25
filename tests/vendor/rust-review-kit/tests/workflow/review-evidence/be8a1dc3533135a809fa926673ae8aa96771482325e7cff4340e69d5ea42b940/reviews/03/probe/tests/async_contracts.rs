
use runtime_bridge::service::*;
use std::{collections::VecDeque, future::Future, pin::pin, sync::{Arc, atomic::{AtomicBool,Ordering}}, task::{Context,Poll,Waker},time::Duration};
use tokio::sync::{Mutex,oneshot};
#[tokio::test] async fn increment_progress() {
 let service=Service::default();
 assert_eq!(tokio::time::timeout(Duration::from_millis(50),service.increment_and_snapshot()).await,Ok(1),"increment holds count lock while snapshot waits for it");
 assert_eq!(service.snapshot().await,1);
}
#[tokio::test] async fn cancel_before_approval() {
 let q=Mutex::new(VecDeque::from([7]));
 let (_tx,rx)=oneshot::channel();
 { let mut f=pin!(approved_pop(&q,rx));
 assert!(matches!(f.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending)); }
 assert_eq!(*q.lock().await,VecDeque::from([7]));
}
#[tokio::test] async fn worker_stopped_before_return() {
 let effect=Arc::new(AtomicBool::new(false));let e=effect.clone();
 let (release,rx)=oneshot::channel();
 let (started,s)=oneshot::channel();
 let worker=tokio::spawn(async move {started.send(()).unwrap();let _=rx.await;e.store(true,Ordering::SeqCst);});
 s.await.unwrap();
 stop_worker(worker).await;
 let _=release.send(());
 for _ in 0..3 {tokio::task::yield_now().await;}
 assert!(!effect.load(Ordering::SeqCst),"worker performed effect after stop returned");
}
