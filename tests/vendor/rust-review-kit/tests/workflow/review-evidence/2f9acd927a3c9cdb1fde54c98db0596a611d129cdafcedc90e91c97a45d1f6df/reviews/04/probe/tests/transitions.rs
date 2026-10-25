use runtime_bridge::service::*;
use std::{collections::VecDeque,future::Future,sync::{Arc,atomic::{AtomicBool,Ordering}},task::{Context,Poll,Waker},time::Duration};
use tokio::sync::{Mutex,oneshot};
#[tokio::test] async fn progress(){let s=Service::default();tokio::time::timeout(Duration::from_secs(1),async {assert_eq!(s.increment_and_snapshot().await,1);assert_eq!(s.snapshot().await,1);}).await.unwrap();}
#[tokio::test] async fn cancel_before_approval_and_at_lock(){
 let q=Mutex::new(VecDeque::from([7]));let(tx,rx)=oneshot::channel();let mut f=Box::pin(approved_pop(&q,rx));assert!(matches!(f.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));drop(f);drop(tx);assert_eq!(*q.lock().await,VecDeque::from([7]));
 let guard=q.lock().await;let(tx,rx)=oneshot::channel();tx.send(()).unwrap();let mut f=Box::pin(approved_pop(&q,rx));assert!(matches!(f.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));drop(f);drop(guard);assert_eq!(*q.lock().await,VecDeque::from([7]));
 let(tx,rx)=oneshot::channel();drop(tx);assert_eq!(approved_pop(&q,rx).await,None);assert_eq!(*q.lock().await,VecDeque::from([7]));
}
struct Mark(Arc<AtomicBool>);impl Drop for Mark{fn drop(&mut self){self.0.store(true,Ordering::SeqCst);}}
#[tokio::test] async fn stop_observes_destructor_and_prevents_effect(){
 let done=Arc::new(AtomicBool::new(false));let effect=Arc::new(AtomicBool::new(false));let (start_tx,start_rx)=oneshot::channel();let (go_tx,go_rx)=oneshot::channel::<()>();let d=done.clone();let e=effect.clone();let task=tokio::spawn(async move{let _mark=Mark(d);start_tx.send(()).unwrap();let _=go_rx.await;e.store(true,Ordering::SeqCst);});start_rx.await.unwrap();tokio::time::timeout(Duration::from_secs(1),stop_worker(task)).await.unwrap();assert!(done.load(Ordering::SeqCst));let _=go_tx.send(());tokio::task::yield_now().await;assert!(!effect.load(Ordering::SeqCst));
}
