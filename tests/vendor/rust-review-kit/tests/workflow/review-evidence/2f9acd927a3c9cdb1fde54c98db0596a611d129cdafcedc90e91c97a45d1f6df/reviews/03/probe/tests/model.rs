#![cfg(feature="model")]
use runtime_bridge::publication::Published;
#[test] fn one_shot_publication(){loom::model(||{
 let p=loom::sync::Arc::new(Published::default());let w=p.clone();
 let h=loom::thread::spawn(move||w.publish(7));
 if let Some(v)=p.snapshot(){assert_eq!(v,7);}
 h.join().unwrap();assert_eq!(p.snapshot(),Some(7));
});}
