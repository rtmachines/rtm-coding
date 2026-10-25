use runtime_bridge::service::{Service,approved_pop,stop_worker};
use std::{collections::VecDeque,future::Future,task::{Context,Poll,Waker},sync::{Arc,atomic::{AtomicBool,Ordering}},time::Duration};
use tokio::sync::{Mutex,oneshot};
#[tokio::test]
async fn later_snapshot_progress(){let s=Service::default();tokio::time::timeout(Duration::from_secs(1),async{assert_eq!(s.increment_and_snapshot().await,1);assert_eq!(s.snapshot().await,1);assert_eq!(s.increment_and_snapshot().await,2);}).await.unwrap();}
#[tokio::test]
async fn closed_approval_preserves_queue(){let q=Mutex::new(VecDeque::from([7]));let(tx,rx)=oneshot::channel();drop(tx);assert_eq!(approved_pop(&q,rx).await,None);assert_eq!(q.lock().await.front(),Some(&7));}
#[tokio::test]
async fn cancel_waiting_on_queue_preserves_queue(){let q=Mutex::new(VecDeque::from([7]));let guard=q.lock().await;let(tx,rx)=oneshot::channel();tx.send(()).unwrap();let mut fut=Box::pin(approved_pop(&q,rx));assert!(matches!(fut.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));drop(fut);assert_eq!(guard.front(),Some(&7));}
struct Mark(Arc<AtomicBool>);impl Drop for Mark{fn drop(&mut self){self.0.store(true,Ordering::SeqCst);}}
#[tokio::test]
async fn stop_waits_for_destructor(){let done=Arc::new(AtomicBool::new(false));let d=done.clone();let(tx,rx)=oneshot::channel();let worker=tokio::spawn(async move{let _mark=Mark(d);tx.send(()).unwrap();std::future::pending::<()>().await;});rx.await.unwrap();tokio::time::timeout(Duration::from_secs(1),stop_worker(worker)).await.unwrap();assert!(done.load(Ordering::SeqCst));}
