use runtime_bridge::service::{Service,approved_pop,stop_worker};
use std::{collections::VecDeque, future::Future, pin::Pin, task::{Context,Poll,Waker},sync::{Arc,atomic::{AtomicUsize,Ordering}}};
use tokio::sync::{Mutex,oneshot};
use tokio::time::{timeout,Duration};
fn poll_once<F:Future>(f:Pin<&mut F>)->Poll<F::Output>{f.poll(&mut Context::from_waker(Waker::noop()))}
#[tokio::test]
async fn increment_progress(){
 let s=Service::default();
 let mut f=Box::pin(s.increment_and_snapshot());
 if poll_once(f.as_mut()).is_ready() {
  assert_eq!(s.snapshot().await,1);
  return;
 }
 eprintln!("increment polled: first lock acquired and increment performed; nested snapshot waits for same guard");
 let mut later=Box::pin(s.snapshot());assert!(poll_once(later.as_mut()).is_pending());
 let result=timeout(Duration::from_millis(100),f.as_mut()).await;
 drop(later);drop(f);
 assert_eq!(s.snapshot().await,1);
 eprintln!("later snapshot blocked while increment alive; after dropping increment snapshot returns 1");
 assert!(result.is_ok(),"increment cannot finish while retaining its own lock");
}
#[tokio::test]
async fn cancel_before_approval_preserves_queue(){
 let q=Mutex::new(VecDeque::from([7,8]));let (_tx,rx)=oneshot::channel();
 let mut f=Box::pin(approved_pop(&q,rx));assert!(poll_once(f.as_mut()).is_pending());drop(f);
 assert_eq!(*q.lock().await,VecDeque::from([7,8]));
}
#[tokio::test]
async fn closed_approval_preserves_queue(){
 let q=Mutex::new(VecDeque::from([7]));let (tx,rx)=oneshot::channel();drop(tx);
 assert_eq!(approved_pop(&q,rx).await,None);assert_eq!(*q.lock().await,VecDeque::from([7]));
}
#[tokio::test]
async fn stop_prevents_later_effect(){
 let effects=Arc::new(AtomicUsize::new(0));let e=effects.clone();
 let (ready_tx,ready_rx)=oneshot::channel();let (release_tx,release_rx)=oneshot::channel();let(done_tx,done_rx)=oneshot::channel();
 let worker=tokio::spawn(async move {ready_tx.send(()).unwrap();let _=release_rx.await;e.fetch_add(1,Ordering::SeqCst);let _=done_tx.send(());});
 ready_rx.await.unwrap();stop_worker(worker).await;
 let _=release_tx.send(());let _=timeout(Duration::from_secs(1),done_rx).await;
 assert_eq!(effects.load(Ordering::SeqCst),0,"effect after stop returned");
}
