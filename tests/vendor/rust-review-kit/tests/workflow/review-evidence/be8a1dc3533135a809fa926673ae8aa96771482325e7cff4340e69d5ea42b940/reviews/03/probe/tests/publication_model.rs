
#![cfg(feature="model")]
use runtime_bridge::publication::Published;
#[test] fn published_value() {
 loom::model(|| {
 let p=loom::sync::Arc::new(Published::default());let q=p.clone();
 let writer=loom::thread::spawn(move|| q.publish(42));
 if let Some(v)=p.snapshot(){assert_eq!(v,42);}
 writer.join().unwrap();assert_eq!(p.snapshot(),Some(42));
 });
}
