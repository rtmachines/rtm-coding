use runtime_bridge::service::*;
use std::{collections::VecDeque,future::Future,task::{Context,Poll,Waker},time::Duration};
use tokio::sync::{Mutex,oneshot};
#[tokio::test]
async fn increment_progress() {
 let s=Service::default();
 assert_eq!(tokio::time::timeout(Duration::from_millis(50),s.increment_and_snapshot()).await.unwrap(),1);
 assert_eq!(s.snapshot().await,1);
}
#[tokio::test]
async fn cancel_before_approval() {
 let q=Mutex::new(VecDeque::from([7])); let (_tx,rx)=oneshot::channel();
 let mut f=Box::pin(approved_pop(&q,rx)); let mut cx=Context::from_waker(Waker::noop());
 assert!(matches!(f.as_mut().poll(&mut cx),Poll::Pending)); drop(f);
 assert_eq!(*q.lock().await,VecDeque::from([7]));
}
#[tokio::test]
async fn stop_prevents_later_effect() {
 let (go,rx)=oneshot::channel(); let (done,observed)=oneshot::channel();
 let (started,ready)=oneshot::channel();
 let h=tokio::spawn(async {let _=started.send(());let _=rx.await;let _=done.send(1);});
 ready.await.unwrap();
 stop_worker(h).await;let _=go.send(());
 assert!(tokio::time::timeout(Duration::from_millis(50),observed).await.unwrap().is_err());
}
