use runtime_bridge::*;
use std::{sync::{Arc,atomic::{AtomicBool,Ordering}},future::Future,pin::Pin,task::{Context,Poll,Waker},time::Duration};
struct PendingDelivery(Arc<AtomicBool>);
impl Future for PendingDelivery{type Output=u64;fn poll(self:Pin<&mut Self>,_:&mut Context<'_>)->Poll<u64>{Poll::Pending}}
impl Drop for PendingDelivery{fn drop(&mut self){self.0.store(true,Ordering::SeqCst);}}
struct Local(Arc<AtomicBool>);
impl Transport for Local{fn send(&self,_:u64)->Delivery<'_>{Box::pin(PendingDelivery(self.0.clone()))}}
#[tokio::test]async fn deadline_drops_local_future(){let flag=Arc::new(AtomicBool::new(false));assert_eq!(deliver(&Local(flag.clone()),7,Duration::ZERO).await,Outcome::Retry(7));assert!(flag.load(Ordering::SeqCst));}
#[tokio::test]async fn caller_cancel_drops_local_future(){let flag=Arc::new(AtomicBool::new(false));let local=Local(flag.clone());let mut f=Box::pin(deliver(&local,7,Duration::from_secs(30)));assert!(matches!(f.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));drop(f);assert!(flag.load(Ordering::SeqCst));}
