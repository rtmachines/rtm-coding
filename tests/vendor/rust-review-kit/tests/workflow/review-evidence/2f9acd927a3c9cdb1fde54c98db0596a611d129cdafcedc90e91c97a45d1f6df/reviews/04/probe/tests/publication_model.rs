#![cfg(feature="model")]
use runtime_bridge::publication::Published;
#[test]fn publication_model(){let mut b=loom::model::Builder::new();b.max_threads=3;b.max_branches=1000;b.max_permutations=None;b.max_duration=None;b.preemption_bound=None;b.check(||{let d=loom::sync::Arc::new(Published::default());let w=d.clone();let t=loom::thread::spawn(move||w.publish(42));if let Some(v)=d.snapshot(){assert_eq!(v,42);}t.join().unwrap();assert_eq!(d.snapshot(),Some(42));});}
