from pathlib import Path
import shutil
root=Path('/tmp/rust-skills-review-20261025');p=root/'cases/03';o=root/'reviews/03/probe';o.mkdir(exist_ok=True)
shutil.copytree(p/'src',o/'src',dirs_exist_ok=True)
for f in ['Cargo.toml','Cargo.lock']:shutil.copy2(p/f,o/f)
(o/'tests').mkdir(exist_ok=True)
(o/'tests/async.rs').write_text('''use runtime_bridge::service::*;
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
 let h=tokio::spawn(async {let _=rx.await;let _=done.send(1);});
 stop_worker(h).await;let _=go.send(());
 assert!(tokio::time::timeout(Duration::from_millis(50),observed).await.unwrap().is_err());
}
''')
(o/'tests/model.rs').write_text('''#![cfg(feature="model")]
use runtime_bridge::publication::Published;
#[test] fn one_shot_publication(){loom::model(||{
 let p=loom::sync::Arc::new(Published::default());let w=p.clone();
 let h=loom::thread::spawn(move||w.publish(7));
 if let Some(v)=p.snapshot(){assert_eq!(v,7);}
 h.join().unwrap();assert_eq!(p.snapshot(),Some(7));
});}
''')
m=root/'reviews/03/memory';(m/'src').mkdir(parents=True,exist_ok=True)
for f in ['bytes.rs','registration.rs']:shutil.copy2(p/'src'/f,m/'src'/f)
(m/'Cargo.toml').write_text('[package]\nname="memory-probe"\nversion="0.1.0"\nedition="2024"\n')
(m/'src/lib.rs').write_text('''mod bytes;mod registration;
#[cfg(test)]mod probes {
 use super::*;
 #[test] fn short_word(){let b=Box::new([1u8]);assert_eq!(bytes::read_word(&*b),None);}
 #[test] fn unaligned_word(){#[repr(align(4))]struct A([u8;8]);let b=A([1;8]);assert_eq!(bytes::read_word(&b.0[1..5]),Some(u32::from_ne_bytes([1;4])));}
 static mut RETAINED:*const u8=std::ptr::null();
 unsafe extern "C" fn register(p:*const u8,_:usize){unsafe{RETAINED=p;}}
 unsafe extern "C" fn unregister(){unsafe{assert_eq!(*RETAINED,7);RETAINED=std::ptr::null();}}
 #[test] fn retained_buffer(){let r=unsafe{registration::Registration::new(vec![7u8].into_boxed_slice(),register,unregister)};let moved=Box::new(r);unsafe{assert_eq!(*RETAINED,7);}drop(moved);}
}
''')
p2=root/'cases/02';o2=root/'reviews/02/probe';(o2/'tests').mkdir(parents=True,exist_ok=True);shutil.copytree(p2/'src',o2/'src',dirs_exist_ok=True)
for f in ['Cargo.toml','Cargo.lock']:shutil.copy2(p2/f,o2/f)
(o2/'tests/contracts.rs').write_text('''use ledger_preview::*;
#[test]fn contracts(){
 let a=Identity{tenant_id:1,user_id:2};assert!(can_read(a,a));assert!(!can_read(a,Identity{tenant_id:2,user_id:2}));assert!(!can_read(a,Identity{tenant_id:1,user_id:3}));
 assert_eq!(debit(0,1),None);assert_eq!(debit(1,1),Some(0));
 assert_eq!(preview("é🦀x",2),"é🦀");assert_eq!(preview("x",0),"");
 assert!(!token_usable(5,5));assert_eq!(fee(u32::MAX,u32::MAX),((u32::MAX as u128)*(u32::MAX as u128)/10000)as u64);
 for (s,v) in [("0",Some(0)),("65535",Some(65535)),("65536",None),("-1",None),("",None),("x",None),("1.2",None)]{assert_eq!(parse_limit(s),v);}
}
''')
