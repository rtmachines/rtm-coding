use runtime_bridge::service::{Service,approved_pop,stop_worker};
use std::{collections::VecDeque,future::Future,task::{Context,Poll,Waker},sync::{Arc,atomic::{AtomicBool,Ordering}},time::Duration};
use tokio::sync::{Mutex,oneshot};
#[tokio::test] async fn progress_and_later_snapshot() {let s=Service::default(); tokio::time::timeout(Duration::from_secs(1),async {assert_eq!(s.increment_and_snapshot().await,1); assert_eq!(s.snapshot().await,1); let (a,b)=tokio::join!(s.increment_and_snapshot(),s.increment_and_snapshot()); assert!((2..=3).contains(&a));assert!((2..=3).contains(&b));assert_eq!(s.snapshot().await,3);}).await.unwrap();}
#[tokio::test] async fn cancellation_waiting_for_queue_and_closed_approval() {let q=Mutex::new(VecDeque::from([7]));let guard=q.lock().await;let(tx,rx)=oneshot::channel();tx.send(()).unwrap();let mut f=Box::pin(approved_pop(&q,rx));assert!(matches!(f.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));drop(f);assert_eq!(guard.front(),Some(&7));drop(guard);let(tx,rx)=oneshot::channel();drop(tx);assert_eq!(approved_pop(&q,rx).await,None);assert_eq!(*q.lock().await,VecDeque::from([7]));}
struct Mark(Arc<AtomicBool>);impl Drop for Mark {fn drop(&mut self){self.0.store(true,Ordering::SeqCst);}}
#[tokio::test] async fn shutdown_waits_for_destructor() {let flag=Arc::new(AtomicBool::new(false));let f=flag.clone();let(tx,rx)=oneshot::channel();let worker=tokio::spawn(async move{let _mark=Mark(f);tx.send(()).unwrap();std::future::pending::<()>().await;});rx.await.unwrap();tokio::time::timeout(Duration::from_secs(1),stop_worker(worker)).await.unwrap();assert!(flag.load(Ordering::SeqCst));}
#[tokio::test] async fn shutdown_waits_for_running_blocking_worker() {
 let (started_tx,started_rx)=oneshot::channel(); let (release_tx,release_rx)=std::sync::mpsc::channel(); let effect=Arc::new(AtomicBool::new(false));let e=effect.clone();
 let worker=tokio::task::spawn_blocking(move||{started_tx.send(()).unwrap();release_rx.recv().unwrap();e.store(true,Ordering::SeqCst);});started_rx.await.unwrap();
 let mut stop=Box::pin(stop_worker(worker)); assert!(matches!(stop.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));assert!(!effect.load(Ordering::SeqCst));release_tx.send(()).unwrap();tokio::time::timeout(Duration::from_secs(1),stop).await.unwrap();assert!(effect.load(Ordering::SeqCst));
}
