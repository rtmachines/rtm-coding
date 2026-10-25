use memory_probe::service::{approved_pop,stop_worker,Service};
use std::{collections::VecDeque,future::Future,task::{Context,Poll,Waker},sync::{Arc,atomic::{AtomicBool,Ordering}},time::Duration};
use tokio::sync::{Mutex,oneshot};
#[tokio::test] async fn cancellation_after_approval_while_lock_waiting() {
 let q=Mutex::new(VecDeque::from([7]));let guard=q.lock().await;
 let (tx,rx)=oneshot::channel();tx.send(()).unwrap();
 let mut f=Box::pin(approved_pop(&q,rx));
 assert!(matches!(f.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));
 drop(f);assert_eq!(guard.front(),Some(&7));
}
#[tokio::test] async fn closed_approval_preserves_queue() {
 let q=Mutex::new(VecDeque::from([7]));let (tx,rx)=oneshot::channel();drop(tx);
 assert_eq!(approved_pop(&q,rx).await,None);assert_eq!(q.lock().await.front(),Some(&7));
}
#[tokio::test] async fn successive_increment_and_snapshot_progress() {
 let s=Service::default();for n in 1..=3 {assert_eq!(tokio::time::timeout(Duration::from_secs(1),s.increment_and_snapshot()).await.unwrap(),n);assert_eq!(tokio::time::timeout(Duration::from_secs(1),s.snapshot()).await.unwrap(),n);}
}
struct Marker(Arc<AtomicBool>);impl Drop for Marker {fn drop(&mut self){self.0.store(true,Ordering::SeqCst);}}
#[tokio::test] async fn async_worker_destructor_completed_before_return() {
 let destroyed=Arc::new(AtomicBool::new(false));let flag=destroyed.clone();let (tx,rx)=oneshot::channel();
 let worker=tokio::spawn(async move {let _marker=Marker(flag);tx.send(()).unwrap();std::future::pending::<()>().await;});
 rx.await.unwrap();tokio::time::timeout(Duration::from_secs(1),stop_worker(worker)).await.unwrap();assert!(destroyed.load(Ordering::SeqCst));
}
#[tokio::test] async fn started_blocking_worker_is_joined() {
 let destroyed=Arc::new(AtomicBool::new(false));let flag=destroyed.clone();let (tx,rx)=oneshot::channel();let (release,wait)=std::sync::mpsc::channel();
 let worker=tokio::task::spawn_blocking(move || {let _marker=Marker(flag);tx.send(()).unwrap();wait.recv_timeout(Duration::from_secs(5)).unwrap();});
 rx.await.unwrap();let mut stopping=Box::pin(stop_worker(worker));assert!(matches!(stopping.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));assert!(!destroyed.load(Ordering::SeqCst));
 release.send(()).unwrap();tokio::time::timeout(Duration::from_secs(2),stopping).await.unwrap();assert!(destroyed.load(Ordering::SeqCst));
}
#[tokio::test] async fn already_finished_worker_can_be_stopped() {
 let destroyed=Arc::new(AtomicBool::new(false));let flag=destroyed.clone();let (tx,rx)=oneshot::channel();let worker=tokio::spawn(async move {let _marker=Marker(flag);tx.send(()).unwrap();});rx.await.unwrap();stop_worker(worker).await;assert!(destroyed.load(Ordering::SeqCst));
}
