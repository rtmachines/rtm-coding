#[cfg(feature="model")]
#[test] fn one_shot_publication(){let mut b=loom::model::Builder::new();b.max_branches=1000;b.preemption_bound=Some(3);b.check(||{let p=loom::sync::Arc::new(runtime_bridge::publication::Published::default());let w=p.clone();let t=loom::thread::spawn(move||w.publish(42));if let Some(v)=p.snapshot(){assert_eq!(v,42);}t.join().unwrap();assert_eq!(p.snapshot(),Some(42));});}
