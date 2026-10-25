#![cfg(feature="model")]
use runtime_bridge::publication::Published;
#[test]
fn publication_model(){let mut b=loom::model::Builder::new();b.max_threads=3;b.max_branches=1000;b.max_permutations=None;b.max_duration=None;b.preemption_bound=None;b.check(||{let p=loom::sync::Arc::new(Published::default());let writer=p.clone();let t=loom::thread::spawn(move||writer.publish(42));if let Some(x)=p.snapshot(){assert_eq!(x,42);}t.join().unwrap();assert_eq!(p.snapshot(),Some(42));});}
