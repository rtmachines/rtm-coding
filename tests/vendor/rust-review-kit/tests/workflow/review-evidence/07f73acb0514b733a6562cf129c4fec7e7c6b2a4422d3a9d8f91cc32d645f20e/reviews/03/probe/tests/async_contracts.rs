use runtime_bridge::service::*;
use std::{collections::VecDeque,future::Future,task::{Context,Poll,Waker},time::Duration};
use tokio::sync::{Mutex,oneshot};
#[tokio::test] async fn increment_progress(){assert_eq!(tokio::time::timeout(Duration::from_millis(100),Service::default().increment_and_snapshot()).await.unwrap(),1);}
#[tokio::test] async fn cancellation_keeps_item(){let q=Mutex::new(VecDeque::from([7]));let (_tx,rx)=oneshot::channel();let mut f=Box::pin(approved_pop(&q,rx));assert!(matches!(f.as_mut().poll(&mut Context::from_waker(Waker::noop())),Poll::Pending));drop(f);assert_eq!(*q.lock().await,VecDeque::from([7]));}
#[tokio::test] async fn stop_prevents_effect(){let (go,wait)=oneshot::channel();let (effect,done)=oneshot::channel();let worker=tokio::spawn(async move {if wait.await.is_ok(){let _=effect.send(42);}});stop_worker(worker).await;let _=go.send(());let result=tokio::time::timeout(Duration::from_millis(100),done).await.unwrap();assert!(result.is_err(),"worker performed effect after stop: {result:?}");}
